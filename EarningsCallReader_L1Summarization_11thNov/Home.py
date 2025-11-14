import os
import streamlit as st
import streamlit.components.v1 as components

# ==============================
# PAGE CONFIGURATION
# ==============================
st.set_page_config(page_title="ECR - Earnings Call Reader", layout="wide")


st.markdown(
    """
    <style>
        /* Center text inside all page_link buttons */
        [data-testid="stPageLinkContainer"] a {
            justify-content: center !important;
            text-align: center !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================
# AUTHENTICATION / API KEY HANDLING
# ==============================
def sidebar_api_key_input():
    """Sidebar input for OpenAI and Mistral API keys."""
    api_key = st.sidebar.text_input(
        "🔑 OpenAI API Key",
        value=st.session_state.get("OPENAI_API_KEY", ""),
        type="password",
        help="Enter your OpenAI API key to enable GPT features.",
    )

    if api_key:
        cols=st.columns([10,10,5], gap="large")
        with cols[2]:
            st.page_link(
    "pages/1_Upload_and_View_PDF.py",
    label="🚀 Let’s Begin!",
    use_container_width=True
)

        st.session_state["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
        # Set your Mistral key securely here
        st.session_state["MISTRALAI_API_KEY"] = "alHrreAH1Ru3a0KteMGyFcKj8Yi9oY5X"
        st.sidebar.success("✅ OpenAI API key set successfully.")

    if not st.session_state.get("OPENAI_API_KEY"):
        st.sidebar.warning("⚠️ Please enter your OpenAI API key to use the GPT features.")

# Initialize early
sidebar_api_key_input()

# ==============================
# THEME APPLICATION
# ==============================
def apply_theme():
    """Apply Bain custom theme from theme.css"""
    # Include Font Awesome icons
    st.markdown(
        """<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">""",
        unsafe_allow_html=True,
    )

    theme_path = os.path.join(os.path.dirname(__file__), "theme.css")
    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ theme.css not found — default Streamlit style will be used.")

apply_theme()

# ==============================
# HEADER SECTION
# ==============================
st.logo(
    image="https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Bain_%26_Company_logo.svg/2560px-Bain_%26_Company_logo.svg.png"
)

st.markdown(
    """
    <div class="title" style="text-align:center; margin: 2rem 0;">
        <h1 style="color:#D40000; font-size:3.5rem; font-weight:800; margin:0;">
            ECR - Earnings Call Reader
        </h1>
        <h2 style="color:#D40000; font-size:1.8rem; font-weight:500; margin-top:0.5rem;">
            Developed by FS CoE & BCN Labs
        </h2>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================
# ANIMATED INTRO (Lottie)
# ==============================
components.html(
    """
    <div style="width:250px; margin:auto;">
      <lottie-player 
        src="https://assets1.lottiefiles.com/packages/lf20_4kx2q32n.json"
        background="transparent"
        speed="1"
        loop
        autoplay>
      </lottie-player>
    </div>
    <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
    """,
    height=270,
)

# ==============================
# INTRO SECTION
# ==============================
st.markdown(
    """
    <div class="section">
        <h3>What is the Earnings Call Reader (ECR)?</h3>
        <p>
            The <strong>Earnings Call Reader (ECR)</strong> is a transcript intelligence tool that helps extract 
            and analyze verbatim commentary from earnings calls.
            It empowers analysts, strategists, and data professionals to surface insights quickly — based on 
            custom themes.
        </p>
        <ul>
            <li>📥 <strong>Upload &amp; View PDFs:</strong> Upload earnings call PDFs and browse them within the app.</li>
            <li>✏️ <strong>Add &amp; Modify Themes:</strong> Define or edit themes and definitions for analysis.</li>
            <li>🔍 <strong>Extract Commentary:</strong> One-click extraction with confidence scoring.</li>
            <li>📊 <strong>Download Results:</strong> Export results in a clean, Excel-friendly format.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================
# LAST VIEWED FOLDER (Optional)
# ==============================
if "selected_folder_path" in st.session_state:
    st.markdown(
        f"""
        <div class="section">
            <p><strong>🧭 Last viewed folder:</strong> <code>{st.session_state['selected_folder_path']}</code></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================
# FOOTER
# ==============================
st.markdown(
    """
    <div class="section" style="text-align:center; padding:1rem 0; font-size:0.9rem; color:gray;">
        © 2025 <strong>ECR - Earnings Call Reader</strong> | Developed by FS CoE x BCN Labs
    </div>
    """,
    unsafe_allow_html=True,
)

