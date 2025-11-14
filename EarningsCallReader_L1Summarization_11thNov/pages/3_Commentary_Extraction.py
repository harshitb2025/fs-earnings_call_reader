# app/pages/summarize.py  (example filename)
import os
import io
import re
import time
import asyncio
import pandas as pd
from pathlib import Path
import streamlit as st

# ---- your helpers (as you already had) ----
from helper_functions.indexing import *
from helper_functions.creating_chunks import *
from helper_functions.extracting_commentaries import *
from helper_functions.validating_commentaries import validate_all_rows, validate_row
from helper_functions.summarizing_commentaries import *

# ==============================
# CONSTANTS / TITLES
# ==============================
APP_TITLE = "📝 Extract & Validate Commentary"
MARKDOWN_STORE = "markdown_store"
CONFIDENCE_MIN = 6

# ==============================
# THEME
# ==============================
def apply_theme():
    """Inject custom CSS theme from ../theme.css (one level above pages/)."""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Theme file not found at {css_file}")
        
with st.spinner("Applying theme..."):
    apply_theme()

# ==============================
# PAGE HEADER
# ==============================
st.markdown(
    f"""
    <div style='text-align:center; margin: 1rem 0;'>
      <h1 style='color:#D40000; font-size:2.75rem; font-weight:900;'>{APP_TITLE}</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================
# SESSION STATE INIT
# ==============================
def ss_init():
    st.session_state.setdefault("validated_df", None)
    st.session_state.setdefault("results", None)
    st.session_state.setdefault("commentaries_df_without_conf", None)
    st.session_state.setdefault("commentaries_df_with_conf", None)

ss_init()

# ==============================
# UTILITIES
# ==============================
def export_excel(df: pd.DataFrame, base_name: str, sheet_prefix: str) -> tuple[bytes, str]:
    """Return (bytes, filename) for a DataFrame Excel export."""
    from io import BytesIO
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"{base_name}_{ts}.xlsx"
    sheet_name = f"{sheet_prefix}_{time.strftime('%H-%M-%S')}"
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.read(), file_name

def get_session_selection():
    """Validate selection pulled from previous pages."""
    folder = st.session_state.get("selected_folder_path")
    pdfs = st.session_state.get("selected_pdf")
    themes_df = st.session_state.get("theme_definitions_df")  # keep naming consistent
    if not folder or not pdfs:
        st.error("Missing selection: please choose a folder and PDF(s) on the previous page.")
        st.stop()
    return folder, pdfs, themes_df

def load_results_from_markdown(pdf_paths, md_root=MARKDOWN_STORE):
    """Load extracted markdown for PDFs if available; otherwise extract and cache."""
    results, all_md_exist = {}, True
    for pdf_path in pdf_paths:
        md_path = os.path.join(md_root, os.path.normpath(pdf_path).replace(".pdf", ".md"))
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                results[pdf_path] = f.read()
        else:
            all_md_exist = False

    if all_md_exist and results:
        return results

    extracted = asyncio.run(
        process_multiple_pdfs(
            pdf_paths=pdf_paths,
            api_key="alHrreAH1Ru3a0KteMGyFcKj8Yi9oY5X",
            replace_images=False,
        )
    )

    for pdf_path, content in extracted.items():
        md_path = os.path.join(md_root, os.path.normpath(pdf_path).replace(".pdf", ".md"))
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

    return extracted

def get_chunks_from_pdf(pdf_extracted_output, pdf_path):
    """Split extracted markdown into chunks & attach metadata."""
    chunks = []
    agg_markdown = pdf_extracted_output[pdf_path]
    markdown_chunks = markdown_text_split(
        text=agg_markdown,
        headers_to_split_on=[("#", 1), ("##", 2), ("###", 3), ("####", 4), ("#####", 5)],
    )
    page_nums = extract_page_numbers_from_chunks(markdown_chunks)
    for i, _ in enumerate(markdown_chunks):
        markdown_chunks[i].metadata["page_number"] = page_nums[i]
        markdown_chunks[i].metadata["PDF path"] = pdf_path
        chunks.append(markdown_chunks[i])
    return chunks

# ==============================
# PIPELINE RUN
# ==============================
st.header("Run pipeline or Upload validated excel")

progress_bar = st.progress(0)
progress_text = st.empty()

choice = st.selectbox(
    "Would you like to upload an existing validated Excel file to skip re-validation?",
    options=["No, run full pipeline", "Yes, upload validated Excel file"],
    index=0,
)

folder, pdfs, theme_definitions_df = get_session_selection()
pdf_paths = [os.path.join(folder, pdf) for pdf in pdfs]
api_key = os.getenv("OPENAI_API_KEY")  # passed to helper functions


def validate_dataframe_columns(df: pd.DataFrame, expected_columns: list[str]) -> tuple[bool, dict]:
    """
    Validate whether a DataFrame has the expected columns (case-sensitive).
    Returns incorrect→expected mapping if mismatches are found.

    Args:
        df (pd.DataFrame): DataFrame to validate.
        expected_columns (list[str]): List of required column names (case-sensitive).

    Returns:
        tuple:
            - bool: True if all expected columns are present and no unexpected ones exist.
            - dict: {"incorrect_name": "expected_name"} for mismatched or unexpected columns.
    """
    actual_columns = list(df.columns)
    incorrect_map = {}

    # Check for unexpected or incorrect columns
    for col in actual_columns:
        if col not in expected_columns:
            incorrect_map[col] = "Expected one of: " + ", ".join(expected_columns)


    is_valid = len(incorrect_map) == 0
    return is_valid, incorrect_map

# ----- 1) Use existing validated file (optional) -----
if choice.startswith("Yes"):

    uploaded_file = st.file_uploader(
        "📤 Upload an existing validated Excel file:",
        type=["xlsx"],
        help="If you already have a validated Excel, upload it to skip re-validation.",
    )
    if uploaded_file is not None:

        try:
            st.session_state["commentaries_df_with_conf"] = pd.read_excel(uploaded_file)
            validated_df=st.session_state["commentaries_df_with_conf"]
            flag, mis_cols = validate_dataframe_columns(validated_df,['Company','Theme','Definition','Extracted Commentary','Page nums','confidence_score','Rationale'])

            if not flag:
                formatted = ", ".join([f"{wrong} → {right}\n" for wrong, right in mis_cols.items()])
                st.error(f"❌ Incorrect spell/name of required column(s), with same case(s)\n: {formatted}")
                st.stop()
            else:
                st.success(f"✅ Loaded validated Excel file: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ Failed to read Excel file: {e}")
    else:
        st.info("Please upload a validated excel to proceed")
        st.stop()

# ----- 2) Run full pipeline -----
else:
    st.info("⚙️ Running pipeline: PDF Extraction → Commentary Extraction → Validation")

    if st.button("🚀 Run Full Pipeline"):
        start = time.time()
        total_steps = 4
        step = 0

        # Step 1: PDF Extraction
        t0 = time.time()
        progress_text.text("📄 Step 1: Extracting information from PDFs…")
        if st.session_state.get("results") is None:
            st.session_state["results"] = load_results_from_markdown(pdf_paths)
            st.success(f"✅ Extraction completed in {time.time() - t0:.2f}s.")
        else:
            st.info("PDF extraction already available. Skipping re-extraction.")
        step += 1.33
        progress_bar.progress(int(step / total_steps * 100))

        # Step 2: Commentary Extraction
        t0 = time.time()
        progress_text.text("🧠 Step 2: Commentary extraction in progress…")
        if st.session_state.get("commentaries_df_without_conf") is None:
            rows = asyncio.run(
                process_all_pdfs_and_chunks(
                    results=st.session_state["results"],
                    themes_data=theme_definitions_df,
                    api_key=api_key,
                )
            )
            st.session_state["commentaries_df_without_conf"] = finalizing_dataframe(rows)
            st.success(f"✅ Commentary extraction completed in {time.time() - t0:.2f}s.")
        else:
            st.info("Commentaries already extracted. Proceeding to validation...")
        step += 1.33
        progress_bar.progress(int(step / total_steps * 100))

        # Step 3: Validation
        t0 = time.time()
        progress_text.text("🛡️ Step 3: Validating extracted commentaries…")
        if st.session_state.get("commentaries_df_with_conf") is None:
            validated_df = validate_all_rows(
                st.session_state["commentaries_df_without_conf"],
                openai_api_key=api_key,
                max_workers=None,
            )
            st.session_state["commentaries_df_with_conf"] = validated_df
            st.success(f"✅ Validation completed in {time.time() - t0:.2f}s.")
        else:
            st.info("Validation already completed. Proceeding to summarization...")
        step += 1.33
        progress_bar.progress(int(step / total_steps * 100))
        progress_bar.progress(100)
        progress_text.text(f"🎉 All steps completed successfully in {time.time() - start:.2f}s.")


if st.session_state.get("commentaries_df_with_conf") is not None:
    st.divider()
    st.write("### Extracted Commentaries (After Validation)")
    validated_df = st.session_state["commentaries_df_with_conf"].map(
        lambda x: re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", x) if isinstance(x, str) else x
    )
    validated_df = validated_df[validated_df["confidence_score"] > CONFIDENCE_MIN]
    st.dataframe(validated_df)

    data, fname = export_excel(validated_df, "validated_commentaries", "Validated")
    st.download_button(
        label="⬇️ Download Validated Commentaries (Excel)",
        data=data,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.write(f"Total Extracted Commentaries: {len(validated_df)}")
    cols=st.columns([10,10,5], gap="large")
    with cols[2]:
        st.page_link(r"pages/4_Summarization.py",label="➡️ Summarize Commentaries")


