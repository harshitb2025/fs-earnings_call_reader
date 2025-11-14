from regex import F
import streamlit as st
import pandas as pd
import re
import textwrap
from helper_functions.testing import *
from helper_functions.indexing import *
from markupsafe import Markup
import streamlit.components.v1 as components
from pathlib import Path
import asyncio
import time

# -------- GLOBAL FONT & THEME SETUP -------- #
st.title("Earnings Call Transcript")

def apply_theme():
    # 1) get the pages folder (<project_root>/app/pages)
    this_page = Path(__file__).resolve().parent
    # 2) go up one level to <project_root>/app
    project_root = this_page.parent
    # 3) read the theme.css that lives in <project_root>/app/theme.css
    css_file = project_root / "theme.css"
    if css_file.exists():
        st.markdown(f"""<style>
{css_file.read_text()}</style>""", unsafe_allow_html=True)
    else:
        st.warning(f"Theme file not found at {css_file}")

# …and then just call
apply_theme()

st.markdown("""
<style>
/* ------------------------------------------------------ */
/* 🔹 GLOBAL FONT & BASE STYLES */
/* ------------------------------------------------------ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], div {
    font-family: 'Inter', sans-serif !important;
    font-weight: 400;
    color: #111827;
    letter-spacing: 0.01em;
}

/* ------------------------------------------------------ */
/* 🔹 CARD STYLING (consistent across all sections) */
/* ------------------------------------------------------ */
.card-base {
    background: linear-gradient(145deg, #ffffff, #f8f9fa);
    border-radius: 18px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.06),
                0 2px 6px rgba(0,0,0,0.04);
    padding: 1.5rem;
    margin: 1rem auto;
    width: 100%;
    max-width: 1000px;
    transition: all 0.25s ease;
    border: 1px solid rgba(230,230,230,0.7);
    overflow: hidden;
    word-wrap: break-word;
}

.card-base:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    background: linear-gradient(145deg, #ffffff, #fefefe);
}

.card-title {
    font-weight: 700;
    font-size: 1.1rem;
    margin-bottom: 0.6rem;
    color: #1f2937;
}

.card-text {
    font-size: 0.96rem;
    line-height: 1.6;
    color: #374151;
    text-align: justify;
    white-space: normal;
}

/* Bullet formatting */
.card-text ul {
    margin: 0.4rem 0 0 1.4rem;
    padding-left: 1rem;
}
.card-text li {
    margin-bottom: 0.35rem;
    list-style-type: disc;
}
            
/* --- Confidence Bar Styling (shared between summaries & commentaries) --- */
.confidence-row {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    margin-top: 1rem;
}

.confidence-label {
    font-weight: 600;
    color: #1f2937;
    font-size: 0.95rem;
}

.confidence-bar {
    background: #e5e7eb;
    height: 8px;
    width: 120px;
    border-radius: 999px;
    overflow: hidden;
    position: relative;
}

.confidence-bar-fill {
    background: #4f46e5;
    height: 100%;
    border-radius: 999px;
    position: absolute;
    left: 0;
    top: 0;
    transition: width 0.4s ease;
}

.confidence-score {
    font-weight: 700;
    color: #111827;
    min-width: 40px;
}


/* ------------------------------------------------------ */
/* 🔹 SCROLL WRAPPERS (shared across sections) */
/* ------------------------------------------------------ */
.scroll-wrapper,
.right-scroll-wrapper {
    height: 900px;
    overflow-y: auto;
    background: #f9fafb;
    border-radius: 20px;
    padding: 2rem 0;
    margin-top: 1rem;
    scroll-behavior: smooth;
}

.scroll-wrapper::-webkit-scrollbar,
.right-scroll-wrapper::-webkit-scrollbar {
    width: 10px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.scroll-wrapper:hover::-webkit-scrollbar,
.right-scroll-wrapper:hover::-webkit-scrollbar {
    opacity: 1;
}

.scroll-wrapper::-webkit-scrollbar-thumb,
.right-scroll-wrapper::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.25);
    border-radius: 10px;
}


/* ------------------------------------------------------ */
/* 🔹 RATIONALE DROPDOWN */
/* ------------------------------------------------------ */
.xf-rationale {
    background: #f9fafb;
    margin-top: 10px;
    border-top: 1px solid #e5e7eb;
    border-radius: 0 0 16px 16px;
    padding: 10px 12px;
    font-size: 0.95rem;
    color: #374151;
    transition: all 0.3s ease;
}
.xf-rationale summary {
    cursor: pointer;
    font-weight: 600;
    color: #111827;
    list-style: none;
    position: relative;
}
.xf-rationale summary::-webkit-details-marker {display:none;}
.xf-rationale summary::after {
    content: "▾";
    position: absolute;
    right: 0;
    font-size: 1rem;
    transition: transform 0.3s ease;
    color: #6b7280;
}
.xf-rationale[open] summary::after {
    transform: rotate(180deg);
}
</style>
""", unsafe_allow_html=True)



# if "old_summarized_df" not in st.session_state:
#     st.session_state["old_summarized_df"]=None


# -------- Session state -------- #
if "comp_choice" not in st.session_state:
    st.session_state["comp_choice"] = None
if "theme_choice" not in st.session_state:
    st.session_state["theme_choice"] = None
if "uber_summary" not in st.session_state:
    st.session_state["uber_summary"] = None


if st.session_state["summarized_df"] is None:
    st.warning("No summarized data found. Please get the summarized results first! Redirecting to sumarization page...")
    time.sleep(1)
    st.switch_page(r"pages\4_Summarization.py")
    st.stop()

summarized_df = st.session_state["summarized_df"]
# old_summarized_df=st.session_state["old_summarized_df"]
extracted_df = st.session_state["commentaries_df_with_conf"]

# -------- Filter function -------- #
def filter_dataframe_theme_and_firm_wise(df, theme_name, comp_name):
    return df[(df['Theme'] == theme_name) & (df['Company'] == comp_name)]

# -------- Helper: Convert markdown bullets to HTML -------- #
def convert_to_html_bullets(text: str) -> str:
    text = text.replace("\\n", "\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [re.sub(r"^[-•]\s*", "", line) for line in lines if line.startswith(("-", "•"))]
    if bullet_lines:
        return "<ul>" + "".join(f"<li>{line}</li>" for line in bullet_lines) + "</ul>"
    return f"<p>{text}</p>"

# -------- Summaries display -------- #
def display_summaries_all(summarized_df, theme_choice, comp_choice, uber_summary=False):
    if uber_summary:
        if summarized_df is not None and not summarized_df.empty:
            company_df = summarized_df[summarized_df["Company"] == comp_choice]
            if not company_df.empty:
                html_cards = ""
                for _, row in company_df.iterrows():
                    theme = str(row["Theme"])
                    summary = convert_to_html_bullets(str(row["Summary"]))
                    # html_cards += f"""
                    # <div class="card-base">
                    #     <div class="card-title">{theme}</div>
                    #     <div class="card-text">{summary}</div>
                    # </div>
                    # """
                    html_cards += textwrap.dedent(f"""
                <div class="card-base">
                    <div class="card-title"><b>{theme}</b></div>
                    <div class="card-text">{summary}</div>
                </div>
                """)
                repeated_cards=html_cards 
                carousel_html = f"""    

                <div class="scroll-wrapper">
                    {repeated_cards}
                </div>
                """

                st.markdown(carousel_html, unsafe_allow_html=True)
            else:
                st.warning("No data found for the selected company.")
        else:
            st.warning("No data available to display.")
    else:
        filtered_df = filter_dataframe_theme_and_firm_wise(summarized_df, theme_choice, comp_choice)
        if not filtered_df.empty:
            st.markdown('<div class="summary-container">', unsafe_allow_html=True)
            for _, row in filtered_df.iterrows():
                summary_html = Markup(convert_to_html_bullets(str(row["Summary"])))
                st.markdown(f"""
                <div class="card-base">
                    <div class="card-title"><b>Summary</b></div>
                    <div class="card-text">{summary_html}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No data found for the selected company and theme.")
        


# -------- Commentary cards -------- #
def render_extraction_cards(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("No commentaries to display.")
        return

    def format_pages(val):
        if val is None:
            return "N/A"
        nums = re.findall(r'\d+', str(val))
        if not nums:
            return "N/A"
        if len(nums) == 1:
            return f"page {nums[0]}"
        elif len(nums) == 2:
            return f"pages {nums[0]} & {nums[1]}"
        return "pages " + ", ".join(nums[:-1]) + f" & {nums[-1]}"

    html_cards = ""
    for _, row in df.iterrows():
        commentary = str(row.get("Extracted Commentary", "N/A"))
        rationale = str(row.get("Rationale", "No rationale available")).strip()
        page_nums = format_pages(row.get("Page nums"))
        conf_val = int(row.get("confidence_score", 0)) if not pd.isna(row.get("confidence_score")) else 0
        conf_pct = min(max(conf_val * 10, 0), 100)
        conf_label = f"{conf_val}/10"
        html_cards += textwrap.dedent(f"""
        <div class="card-base">
            <div class="card-title"><b>Extracted Commentary<b></div>
            <div class="card-text"><i>{commentary[:-4]}</i></div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.8rem;">
                <div><span style="font-weight:600;">Pages:</span> {page_nums}</div>
                <div><span style="font-weight:600;">Confidence:</span> {conf_label}</div>
            </div>
            <details class="xf-rationale">
                <summary><b>Show Rationale</b></summary>
                <p>{rationale}</p>
            </details>
        </div>
        """)

    st.markdown(f'<div class="scroll-wrapper">{html_cards}</div>', unsafe_allow_html=True)

# -------- UI Layout -------- #
col1, col2 = st.columns([3, 2], gap="small")

with col1:
    col11, col12 = st.columns(2)
    with col11:
        comp_choice = st.selectbox("Select Company:", list(summarized_df['Company'].unique()))
        st.session_state["comp_choice"] = comp_choice
    with col12:
        theme_choice = st.selectbox("Select Theme:", ["All"] + list(summarized_df['Theme'].unique()))
        st.session_state["theme_choice"] = theme_choice

    if st.session_state["theme_choice"] != "All":
        display_summaries_all(summarized_df, st.session_state["theme_choice"], st.session_state["comp_choice"])
    else:
        if st.session_state.get("uber_summary") is None: #or old_summarized_df is None or old_summarized_df.loc[1]!=summarized_df.loc[1]: 
            with st.spinner("Generating uber summary...", show_time=True):
                uber_summary = asyncio.run(uber_theme_summary_wise(summarized_df))
                st.session_state["uber_summary"] = uber_summary
                # st.session_state["old_summarized_df"]=st.session_state["summarized_df"]

        selected_company = st.session_state.get("comp_choice")
        if selected_company and selected_company in st.session_state["uber_summary"]:
            summary_html = Markup(convert_to_html_bullets(str(st.session_state["uber_summary"][selected_company])))
            st.markdown(f"""
            <div class="card-base">
                <div class="card-title"><b>Summary</b></div>
                <div class="card-text">{summary_html}</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("Regenerate Summary", icon="🔀"):
            st.session_state["uber_summary"] = None

with col2:
    if st.session_state["theme_choice"] != "All":
        comm_df = filter_dataframe_theme_and_firm_wise(
            extracted_df,
            st.session_state["theme_choice"],
            st.session_state["comp_choice"]
        )
        comm_df = comm_df[comm_df['confidence_score'] > 6].sort_values(by="confidence_score", ascending=False)
        render_extraction_cards(comm_df)
    else: 
        display_summaries_all(
            summarized_df,
            None,
            st.session_state["comp_choice"],
            uber_summary=True
        )
    st.write("\n\n\n")
    cols=st.columns([5,10])
    with cols[1]:
        st.page_link("pages/4_Summarization.py", label="🔀 Summarize again with different prompts?")
