import os
import pandas as pd
import streamlit as st
from io import BytesIO
from pathlib import Path

# ==============================
# PAGE CONFIGURATION
# ==============================
st.set_page_config(page_title="Theme Manager", layout="wide")

# ==============================
# THEME APPLICATION
# ==============================
def apply_theme():
    """Inject global CSS from theme.css"""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Theme file not found at {css_file}")

apply_theme()

# ==============================
# DIRECTORIES & DEFAULT FILES
# ==============================
MARKDOWN_DIR = Path(os.getcwd()) / "markdown"
EXCEL_DIR = Path(os.getcwd()) / "excel_sheets"
MARKDOWN_DIR.mkdir(exist_ok=True)

default_excel = "default_themes_def.xlsx"
initial_df = pd.read_excel(default_excel)

# ==============================
# SESSION STATE INIT
# ==============================
st.session_state.setdefault("theme_definitions_df", initial_df.copy())
st.session_state.setdefault("selected_themes", [])
st.session_state.setdefault("theme_definitions", {})

# ==============================
# PAGE HEADER
# ==============================
st.markdown("""
<div style='text-align:center; margin: 1rem 0;'>
  <h1 style='color:#D40000; font-size:2.75rem; font-weight:900;'>Theme Manager</h1>
</div>
""", unsafe_allow_html=True)

# ==============================
# VALIDATE SELECTION CONTEXT
# ==============================
pdf_folder = st.session_state.get("selected_folder_path")
pdf_sel = st.session_state.get("selected_pdf")

if not pdf_folder or not pdf_sel:
    st.error("No PDFs selected. Please upload and choose PDFs on the Upload page.")
    st.stop()

pdf_list = pdf_sel if isinstance(pdf_sel, list) else [pdf_sel]
st.session_state["selected_pdf"] = pdf_list
st.info(f"✅ {len(pdf_list)} PDF(s) selected for processing.")

# ==============================
# UTILITIES
# ==============================
def to_excel(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to Excel bytes for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Taxonomy")
    return output.getvalue()

# ==============================
# MAIN UI — THEME DEFINITIONS
# ==============================
st.subheader("Theme Selection & Definitions", divider="blue")

use_default = st.selectbox(
    "Do you want to use default themes and definitions?",
    options=["Yes", "No"],
    index=0
)

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

    # # Check for missing columns as well (optional but useful)
    # missing = [col for col in expected_columns if col not in actual_columns]
    # for col in missing:
    #     incorrect_map[f"Missing: {col}"] = f"Expected '{col}' column not found"

    is_valid = len(incorrect_map) == 0
    return is_valid, incorrect_map

# ==============================
# DEFAULT THEMES MODE
# ==============================
if use_default == "Yes":
    edited_df = st.session_state["theme_definitions_df"]

    # --- Add New Theme ---
    with st.expander("➕ Add a New Theme", expanded=False):
        new_theme = st.text_input("Theme Name", key="new_theme_input")
        new_def = st.text_area("Definition", key="new_def_input")

        if st.button("Add Theme", key="add_theme_btn"):
            if not new_theme.strip():
                st.warning("Please enter a theme name.")
            elif new_theme in edited_df["Theme"].values:
                st.warning(f"Theme '{new_theme}' already exists.")
            else:
                new_row = pd.DataFrame([{"Theme": new_theme, "Definition": new_def}])
                edited_df = pd.concat([edited_df, new_row], ignore_index=True)
                st.session_state["theme_definitions_df"] = edited_df
                st.success(f"✅ Added theme '{new_theme}'.")

    # --- Delete Themes ---
    with st.expander("🗑️ Delete Existing Themes", expanded=False):
        to_delete = st.multiselect(
            "Select themes to delete:",
            options=edited_df["Theme"].tolist(),
            key="delete_themes_sel"
        )
        if st.button("Delete Selected Themes", key="delete_themes_btn"):
            if to_delete:
                edited_df = edited_df[~edited_df["Theme"].isin(to_delete)].reset_index(drop=True)
                st.session_state["theme_definitions_df"] = edited_df
                st.success(f"✅ Deleted themes: {', '.join(to_delete)}.")
            else:
                st.info("No themes selected for deletion.")

    # --- Editable Data Table ---
    edited_df = st.data_editor(
        edited_df,
        num_rows="fixed",
        use_container_width=True,
        key="editable_themes"
    )

    # --- Download Button ---
    st.download_button(
        label="⬇️ Download Themes (Excel)",
        data=to_excel(edited_df),
        file_name="Taxonomy.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==============================
# UPLOAD CUSTOM THEMES MODE
# ==============================
else:
    st.subheader("Upload and Preview Excel File", divider="blue")
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])


    if uploaded_file:
        try:
            uploaded_df = pd.read_excel(uploaded_file)

            flag, mis_cols = validate_dataframe_columns(uploaded_df, ["Theme", "Definition"])

            if not flag:
                formatted = ", ".join([f"{wrong} → {right}" for wrong, right in mis_cols.items()])
                st.error(f"❌ Incorrect spell/name of required column(s), with same case(s): {formatted}")
                st.stop()

            st.session_state["theme_definitions_df"] = uploaded_df
            st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")

            st.subheader("Preview of Uploaded Excel Data", divider="blue")

            # Coerce columns to string to avoid type issues
            for col in ["Theme", "Definition", "L3 Themes"]:
                if col in uploaded_df.columns:
                    uploaded_df[col] = uploaded_df[col].astype(str)

            edited_df = st.data_editor(
                uploaded_df,
                num_rows="fixed",
                use_container_width=True,
                key="editable_themes_upload"
            )
        except Exception as e:
            st.error(f"❌ Failed to read Excel file: {e}")
    else:
        st.info("Please upload an Excel file containing themes and definitions.", icon="📂")

# ==============================
# SAVE & DISPLAY CURRENT THEMES
# ==============================
if st.button("💾 Save Themes & Definitions", key="save_defs_btn"):
    edited_df = edited_df.drop_duplicates(subset=["Theme"]).reset_index(drop=True)
    st.session_state["theme_definitions_df"] = edited_df
    st.session_state["selected_themes"] = edited_df["Theme"].tolist()
    st.session_state["theme_definitions"] = dict(zip(edited_df["Theme"], edited_df["Definition"]))
    st.success("✅ Themes and definitions saved! Now you can proceed with extracting commentaries!")

if st.session_state["selected_themes"]:
    cols=st.columns([10,10,5], gap="small")
    with cols[2]:
        st.page_link("pages/3_Commentary_Extraction.py", label="➡️Start commentary extraction")

st.subheader("📋 Current Themes & Definitions", divider="blue")
if st.session_state["selected_themes"]:
    for theme in st.session_state["selected_themes"]:
        definition = st.session_state["theme_definitions"].get(theme, "")
        st.markdown(f"**{theme}** — {definition}")
else:
    st.info("No themes selected to display.")
