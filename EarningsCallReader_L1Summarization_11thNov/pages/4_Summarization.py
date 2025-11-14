from pathlib import Path
import streamlit as st
from helper_functions.summarizing_commentaries import *
import os
import pandas as pd
import time 

api_key=os.environ.get("OPENAI_API_KEY")

def apply_theme():
    """Inject custom CSS theme from ../theme.css (one level above pages/)."""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Theme file not found at {css_file}")

apply_theme()




def ss_init():
    st.session_state.setdefault("commentaries_df_with_conf", None)
    st.session_state.setdefault("summarized_df", None)
    st.session_state.setdefault("prompts", {})
    st.session_state.setdefault("summary_type", "Brief")
    st.session_state.setdefault("prompt_draft", "")
    st.session_state.setdefault("saved_prompt", None)

ss_init()

if st.session_state["commentaries_df_with_conf"] is None:
    st.warning("Validated excel not found. Either upload validated excel or run whole pipleine on previous page. Redirecting to commentary extraction page...")
    time.sleep(1)
    st.switch_page(r"pages\3_Commentary_Extraction.py")

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

DEFAULT_BRIEF = """
You are an expert financial summarization model.

Your task: Generate a **strictly bulleted summary** of the extracted commentary.

Formatting Rules (must follow exactly):
- Output must **only** consist of bullet points (each line starting with “- ”).
- Do **not** use paragraphs, numbering, or any other formatting symbols.
- Each bullet point must represent a distinct idea or insight.
- There must be **at least 3 bullet points** in the output (unless no relevant commentary is found).
- Each bullet should be **concise, factual, and grammatically correct**.

Guidelines:
- Extract insights strictly from the transcript; do **not** add or infer any outside information.
- Focus on both **quantitative and qualitative** details (e.g., revenue, growth %, margins, segments, geographies, guidance).
- Ensure the summary **broadly covers** the commentary — not just isolated figures.
- Use **passive voice** throughout.
- Do **not** include theme names, headings, or labels.
- Do **not** use LaTeX, Markdown formatting, or indentation beyond the bullet symbol.
- If there are no relevant commentaries, return exactly: 
  `No extracted commentaries for summary`
- Keep the total summary between **150–200 words**.

Structure:
- Begin with the main actions, announcements, or results.
- Follow with key figures, metrics, or qualitative drivers.
- Conclude with implications, partnerships, or strategic priorities if mentioned.

Output Format Example (follow this style exactly):
- Reported revenue increased 8% year-over-year, driven by strong growth in North America and digital services.
- Operating margins improved by 120 basis points due to cost optimization initiatives.
- Announced plans to expand renewable energy investments in Europe.
- Guidance for FY25 was reaffirmed, with expected mid-single-digit growth in EPS.
"""

DEFAULT_STORY = """
Guidelines:
- Extract insights strictly from the transcript (do not add outside information).
- Present the details in a narrative style that connects actions, drivers, and outcomes into a coherent storyline.
- Highlight clear, quantitative, and qualitative details such as revenue, growth %, margins, segments, geographies, or guidance.
- Ensure the summary flows logically, linking events and implications rather than listing facts.
- Use passive voice consistently.
- Do not mention the theme name, headings, or labels in the output.
- Do not use bullet points, lists, or extra formatting.

Structure:
- Begin with the central event, action, or announcement.
- Describe the supporting details and figures in a way that shows cause-and-effect or progression.
- Conclude with implications, strategic direction, or partnerships to give the summary a natural ending.
"""

if not st.session_state["prompts"]:
    st.session_state["prompts"] = {
        "Brief": DEFAULT_BRIEF.strip(),
        "Descriptive(Storyline)": DEFAULT_STORY.strip(),
    }

if not st.session_state["prompt_draft"]:
    st.session_state["prompt_draft"] = st.session_state["prompts"][st.session_state["summary_type"]]

st.subheader("Selection of Summary setup")

def on_type_change():
    t = st.session_state["summary_type"]
    st.session_state["prompt_draft"] = st.session_state["prompts"][t]

summary_type = st.selectbox(
    "Select the type of summary you want:",
    options=["Brief", "Descriptive(Storyline)"],
    index=0 if st.session_state["summary_type"] == "Brief" else 1,
    key="summary_type",
    on_change=on_type_change,
)

with st.expander("Expand to edit the Default Prompt", expanded=False):
    st.text_area(
        "Edit your summarization prompt:",
        key="prompt_draft",
        height=220,
        placeholder=st.session_state["prompts"][summary_type],
    )

if st.button("💾 Save prompt"):
    st.session_state["saved_prompt"] = (st.session_state["prompt_draft"] or st.session_state["prompts"][summary_type]).strip()
    st.session_state["saved_summary_type"] = summary_type
    st.success("Prompt saved.")
    with st.expander("See Final Prompt", expanded=False):
        st.code(st.session_state["saved_prompt"])
st.divider()

if st.button("🚀 Summarize validated commentaries"):
        user_prompt = st.session_state.get("saved_prompt", st.session_state["prompts"][summary_type])
        if st.session_state.get("commentaries_df_with_conf") is not None:
            with st.spinner("⌛ Summarizing validated commentaries…", show_time=True):
                t0 = time.time()
                summarized = asyncio.run(
                    summarizing_commentaries(
                        st.session_state["commentaries_df_with_conf"],
                        user_prompt=user_prompt,
                        openai_api_key=api_key,
                        theme_cross_firm_wise=True,
                    )
                )
                st.session_state["summarized_df"] = pd.DataFrame(summarized)
                st.success(f"✅ Summarization complete in {time.time() - t0:.2f}s!")
        else:
            st.warning("⚠️ No validated data found.")


# ==============================
# OUTPUTS
# ==============================
if st.session_state.get("summarized_df") is not None:
    st.write("### Summarized Commentaries")
    summarized_df = st.session_state["summarized_df"]
    st.dataframe(summarized_df)

    data, fname = export_excel(summarized_df, "summarized_commentaries", "Summarized")
    st.download_button(
        label="⬇️ Download Summarized Commentaries (Excel)",
        data=data,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    cols=st.columns([10,10,8], gap="large")
    with cols[2]:
        st.page_link(r"pages/5_Final_View.py", label="➡️  Click here to see final view of summaries!")
