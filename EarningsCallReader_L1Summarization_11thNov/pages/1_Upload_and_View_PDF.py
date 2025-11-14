import os
import shutil
from pathlib import Path
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import auth

# ==============================
# PAGE CONFIGURATION
# ==============================
st.set_page_config(layout="wide")

# ==============================
# THEME APPLICATION
# ==============================
def apply_theme():
    """Inject custom CSS theme."""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Theme file not found at {css_file}")

apply_theme()

# ==============================
# AUTHENTICATION
# ==============================
# auth.authenticate()

# ==============================
# DIRECTORIES
# ==============================
ROOT_DIR = "earnings_calls"
os.makedirs(ROOT_DIR, exist_ok=True)

# ==============================
# UTILITY FUNCTIONS
# ==============================
def get_folders_files(base_path: str) -> dict:
    """Return folder-to-files mapping for PDFs."""
    structure = {}
    for folder in sorted(os.listdir(base_path)):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            files = [f for f in sorted(os.listdir(folder_path)) if f.lower().endswith(".pdf")]
            structure[folder] = files
    return structure

# ==============================
# PAGE HEADER
# ==============================
st.markdown("""
<div style='text-align: center; margin-top: 1rem; margin-bottom: 1rem;'>
    <h1 style='color: #D40000; font-size: 2.75rem; font-weight: 900;'>📁 Upload, Browse & Manage PDFs</h1>
</div>
""", unsafe_allow_html=True)

# ======================================================
# 1️⃣  FOLDER CREATION
# ======================================================


st.divider()

st.subheader("📂 Create new folder")

with st.expander("➕ Create New Folder", expanded=False):
    new_folder = st.text_input("Folder Name (e.g., Q2 2025)", key="new_folder")
    if st.button("Create Folder", key="create_folder_btn"):
        if not new_folder:
            st.error("❗ Please enter a folder name.")
        else:
            folder_path = os.path.join(ROOT_DIR, new_folder)
            if os.path.exists(folder_path):
                st.warning("⚠️ Folder already exists.")
            else:
                os.makedirs(folder_path)
                st.success(f"✅ '{new_folder}' created.")

# ======================================================
# 2️⃣  FILE UPLOAD SECTION
# ======================================================
folders = sorted([d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))])

st.divider()
st.subheader("📤 Upload PDFs")

if folders:
    upload_to = st.selectbox("Choose folder:", folders, key="upload_folder")
    uploaded_files = st.file_uploader("Select PDFs to upload", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            dest_path = os.path.join(ROOT_DIR, upload_to, file.name)
            with open(dest_path, "wb") as f:
                f.write(file.read())
        st.success(f"✅ Uploaded {len(uploaded_files)} file(s) to '{upload_to}'.")
else:
    st.info("📂 No folders yet. Create one above to start uploading.")
    st.stop()

# ======================================================
# 3️⃣  BROWSE & EXTRACTION SETTINGS
# ======================================================
st.divider()
st.subheader("📄 Browse & Manage")

mode = st.radio("Extraction Mode:", ["Full Extraction", "Single Extraction"], horizontal=True)

structure = get_folders_files(ROOT_DIR)
if not structure:
    st.warning("⚠️ No folders available. Create one above and upload PDFs.")
    st.stop()

if mode == "Full Extraction":
    selected_folder = st.selectbox("Choose folder for full extraction:", list(structure.keys()))
    files = structure[selected_folder]
    st.info(f"✅ {len(files)} files ready for extraction in '{selected_folder}'.")

    if not files:
        st.info("📂 No PDFs in selected folder.")
        st.stop()

    preview_file = st.selectbox("View files in the PDF:", files)

    with st.expander("Preview PDF", expanded=False):
        pdf_path = os.path.join(ROOT_DIR, selected_folder, preview_file)
        pdf_viewer(pdf_path, width="90%", height=1000)


    st.session_state["selected_pdf"] = files

else:
    selected_folder = st.selectbox("Select folder:", list(structure.keys()))
    files = structure[selected_folder]
    if not files:
        st.info("📂 No PDFs in selected folder.")
        st.stop()

    preview_file = st.selectbox("Choose a PDF to extract:", files)
    st.session_state["selected_pdf"] = [preview_file]

    with st.expander("Preview PDF", expanded=False):
        pdf_path = os.path.join(ROOT_DIR, selected_folder, preview_file)
        pdf_viewer(pdf_path, width="90%", height=1000)

# ======================================================
# 4️⃣  MANAGEMENT ACTIONS
# ======================================================
st.divider()
st.subheader("🧰 File & Folder Management")

if st.checkbox("Enable management actions"):
    if mode == "Full Extraction":
        if st.button("🗑️ Delete selected folder"):
            shutil.rmtree(os.path.join(ROOT_DIR, selected_folder))
            st.success(f"✅ Folder '{selected_folder}' deleted.")
            st.rerun()
    else:
        if st.button("🗑️ Delete selected file"):
            os.remove(os.path.join(ROOT_DIR, selected_folder, preview_file))
            st.success(f"✅ File '{preview_file}' deleted.")
            st.rerun()

st.session_state["selected_folder_path"] = os.path.join(ROOT_DIR, selected_folder)
st.caption(f"🧭 Last viewed: `{st.session_state['selected_folder_path']}`")

# ======================================================
# 5️⃣  NAVIGATION BUTTON
# ======================================================
cols = st.columns([10, 10, 3], gap="small")
with cols[2]:
    st.page_link("pages/2_Theme.py", label="➡️Select taxonomy")