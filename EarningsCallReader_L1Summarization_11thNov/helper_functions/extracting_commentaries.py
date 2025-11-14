from openai import AsyncOpenAI
import yaml
import pandas as pd
import asyncio
import os
import re
from helper_functions.indexing import *
from helper_functions.creating_chunks import *
import streamlit as st
import nest_asyncio
nest_asyncio.apply()
from pathlib import Path


prompts=reading_yaml("prompts.yaml")

def apply_theme():
    """Inject custom CSS theme."""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Theme file not found at {css_file}")

apply_theme()


def extract_company_name(pdf_path):
    # Get the filename from the full path
    filename = os.path.basename(pdf_path)
    
    # Remove the extension
    filename_no_ext = os.path.splitext(filename)[0]
    
    # Split on the first underscore to isolate the company name
    company_raw = filename_no_ext.split('_')[0]
    
    # Optional: Clean up common legal suffixes if desired
    
    return company_raw

def print_chunk_page_info(chunk):
    """
    Pretty-print the page numbers and text content from a LangChain Document chunk.
    
    Handles both single and multiple page numbers gracefully.
    
    Args:
        chunk (Document): LangChain Document with metadata containing 'page_number'
                          (can be int or list of ints) and 'page_content' string.
                          
    Example:
        >>> print_chunk_page_info(chunk)
        this content is of page number, chunk.page_number = 15 & 16:
        Thank you. This does conclude the program...
    """
    # Extract page numbers safely
    page_numbers = chunk.metadata.get("page_number", [])

    # Normalize to list
    if isinstance(page_numbers, int):
        page_numbers = [page_numbers]
    elif not isinstance(page_numbers, list):
        page_numbers = list(page_numbers) if page_numbers else []

    # Handle page number string formatting
    if not page_numbers:
        page_str = "unknown"
    elif len(page_numbers) == 1:
        page_str = f"{page_numbers[0]}"
    elif len(page_numbers) == 2:
        page_str = f"{page_numbers[0]} & {page_numbers[1]}"
    else:
        page_str = ", ".join(map(str, page_numbers[:-1])) + f" & {page_numbers[-1]}"

    # Print formatted output
    return f"## This chunk is/are of page numbers:{page_str}:\n\n {chunk.page_content}"


def get_chunks_from_pdf(pdf_extracted_output,pdf_path):
    all_chunks_agg=[]
    markdown_chunks=markdown_text_split(text=pdf_extracted_output, headers_to_split_on=[("#", 1), ("##", 2), ("###", 3), ("####", 4), ("#####", 5)])
    page_nums=extract_page_numbers_from_chunks(markdown_chunks)
    for chunkno, chunk in enumerate(markdown_chunks):
        markdown_chunks[chunkno].metadata['page_number'] = page_nums[chunkno]
        markdown_chunks[chunkno].metadata['PDF path'] = pdf_path
        all_chunks_agg.append(markdown_chunks[chunkno])   
    
    return all_chunks_agg

# -----------------------------------------------------
# 🔹 Shared progress tracker setup
# -----------------------------------------------------
progress_placeholder = st.empty()
progress_bar = st.progress(0.0)

progress_state = {
    "completed": 0,
    "total": 1,  # set later
}

def update_progress():
    pct = progress_state["completed"] / progress_state["total"]
    progress_bar.progress(pct)
    progress_placeholder.text(
        f"({pct*100:.1f}%)"
    )

# -----------------------------------------------------
# 🔹 Extract commentary for one theme (patched)
# -----------------------------------------------------
async def extract_theme_from_chunk(client, chunk, theme, definition):
    pdf_name = extract_company_name(chunk.metadata["PDF path"])
    prompt = prompts['extracting_commentary_prompt_new'].format(theme=theme, definition=definition)

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": print_chunk_page_info(chunk)},
                {"role": "system", "content": prompt},
            ],
            temperature=0.4,
        )
        extracted = resp.choices[0].message.content.strip() or "N/A"

        # ✅ increment progress counter after successful call
        progress_state["completed"] += 1
        update_progress()

        return {
            "Company": pdf_name,
            "Theme": theme,
            "Definition": definition,
            "Extracted Commentary": extracted,
        }

    except Exception as e:
        progress_state["completed"] += 1
        update_progress()

        return {
            "Company": pdf_name,
            "Theme": theme,
            "Definition": definition,
            "Extracted Commentary": f"Error: {str(e)}",
        }

# -----------------------------------------------------
# 🔹 Process all themes for a single chunk
# -----------------------------------------------------
async def extract_for_themes(chunk, themes_data, client: AsyncOpenAI, sem_theme: asyncio.Semaphore):
    async def one_theme(theme, definition):
        async with sem_theme:
            return await extract_theme_from_chunk(client, chunk, theme, definition)

    theme_tasks = [one_theme(row["Theme"], row["Definition"]) for _, row in themes_data.iterrows()]
    theme_results = await asyncio.gather(*theme_tasks)
    return pd.DataFrame(theme_results)

# -----------------------------------------------------
# 🔹 Process all chunks for a single PDF
# -----------------------------------------------------
async def process_chunk(pdf_path, pdf_text, themes_data, client: AsyncOpenAI, sem_chunk: asyncio.Semaphore, sem_theme: asyncio.Semaphore):
    all_chunks = get_chunks_from_pdf(pdf_extracted_output=pdf_text, pdf_path=pdf_path)

    async def run_chunk(chunk):
        async with sem_chunk:
            return await extract_for_themes(chunk, themes_data, client, sem_theme)

    chunk_tasks = [run_chunk(c) for c in all_chunks]
    chunk_results = await asyncio.gather(*chunk_tasks)
    return pd.concat(chunk_results, ignore_index=True)

# -----------------------------------------------------
# 🔹 Process all PDFs concurrently
# -----------------------------------------------------
async def process_all_pdfs_and_chunks(results, themes_data, api_key):
    pdf_paths = list(results.keys())
    client = AsyncOpenAI(api_key=api_key)

    # concurrency caps
    sem_pdf   = asyncio.Semaphore(8)
    sem_chunk = asyncio.Semaphore(20)
    sem_theme = asyncio.Semaphore(10)

    # ✅ compute total API calls (for percentage)
    total_themes = len(themes_data)
    total_chunks = sum(len(get_chunks_from_pdf(results[p], p)) for p in pdf_paths)
    progress_state["total"] = total_chunks * total_themes
    progress_state["completed"] = 0
    update_progress()

    async def run_pdf(pdf_path):
        async with sem_pdf:
            return await process_chunk(pdf_path, results[pdf_path], themes_data, client, sem_chunk, sem_theme)

    try:
        tasks = [run_pdf(p) for p in pdf_paths]
        all_results = await asyncio.gather(*tasks)
        return pd.concat(all_results, ignore_index=True)
    finally:
        await client.close()

# # --------------------------------------------------------------
# # 🔹 Extract commentary for a single theme from one chunk
# # --------------------------------------------------------------
# async def extract_theme_from_chunk(client, chunk, theme, definition):
#     pdf_name = extract_company_name(chunk.metadata["PDF path"])
#     prompt = prompts['extracting_commentary_prompt_new'].format(theme=theme, definition=definition)

#     try:
#         resp = await client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "user", "content": print_chunk_page_info(chunk)},
#                 {"role": "system", "content": prompt},
#             ],
#             temperature=0.4,
#         )
#         extracted = resp.choices[0].message.content.strip() or "N/A"

#         print(f"✅ Done for theme: {theme} | PDF: {pdf_name}")
#         return {
#             "Company": pdf_name,
#             "Theme": theme,
#             "Definition": definition,
#             "Extracted Commentary": extracted,
#         }

#     except Exception as e:
#         print(f"⚠️ Error for theme: {theme} | PDF: {pdf_name} — {e}")
#         return {
#             "Company": pdf_name,
#             "Theme": theme,
#             "Definition": definition,
#             "Extracted Commentary": f"Error: {str(e)}",
#         }


# # --------------------------------------------------------------
# # 🔹 Process all themes for a single chunk
# # --------------------------------------------------------------
# async def extract_for_themes(chunk, themes_data, openai_api_key: str, client: AsyncOpenAI, sem_theme: asyncio.Semaphore):
#     pdf_name = extract_company_name(chunk.metadata["PDF path"])

#     async def one_theme(theme, definition):
#         async with sem_theme:
#             return await extract_theme_from_chunk(
#                 client=client, chunk=chunk, theme=theme, definition=definition
#             )

#     theme_tasks = [one_theme(row["Theme"], row["Definition"]) for _, row in themes_data.iterrows()]
#     theme_results = await asyncio.gather(*theme_tasks)

#     print(f"🎯 Finished all themes for one chunk in {pdf_name}")
#     return pd.DataFrame(theme_results)


# # --------------------------------------------------------------
# # 🔹 Process all chunks for a single PDF
# # --------------------------------------------------------------
# async def process_chunk(pdf_path, pdf_text, themes_data, openai_api_key, client: AsyncOpenAI, sem_chunk: asyncio.Semaphore, sem_theme: asyncio.Semaphore):
#     pdf_name = extract_company_name(pdf_path)
#     all_chunks = get_chunks_from_pdf(pdf_extracted_output=pdf_text, pdf_path=pdf_path)

#     async def run_chunk(chunk):
#         async with sem_chunk:
#             return await extract_for_themes(
#                 chunk=chunk,
#                 themes_data=themes_data,
#                 openai_api_key=openai_api_key,
#                 client=client,
#                 sem_theme=sem_theme,
#             )

#     chunk_tasks = [run_chunk(c) for c in all_chunks]
#     chunk_results = await asyncio.gather(*chunk_tasks)

#     print(f"✅✅ Completed all chunks for PDF: {pdf_name}")
#     return pd.concat(chunk_results, ignore_index=True)

# # --------------------------------------------------------------
# # 🔹 Process all PDFs concurrently
# # --------------------------------------------------------------
# async def process_all_pdfs_and_chunks(results, themes_data, api_key):
#     pdf_paths = list(results.keys())

#     # ✅ One shared OpenAI client for the whole run
#     # If you want to cap sockets at the HTTP layer too, uncomment httpx setup.
#     # http_client = httpx.AsyncClient(limits=httpx.Limits(max_connections=20, max_keepalive_connections=20), timeout=60)
#     # client = AsyncOpenAI(api_key=api_key, http_client=http_client)
#     client = AsyncOpenAI(api_key=api_key)

#     # ✅ Concurrency caps (tune as needed)
#     sem_pdf   = asyncio.Semaphore(8)   # PDFs in parallel
#     sem_chunk = asyncio.Semaphore(20)   # chunks in parallel per run
#     sem_theme = asyncio.Semaphore(10)  # theme API calls in parallel per run

#     async def run_pdf(pdf_path):
#         async with sem_pdf:
#             return await process_chunk(
#                 pdf_path=pdf_path,
#                 pdf_text=results[pdf_path],
#                 themes_data=themes_data,
#                 openai_api_key=api_key,
#                 client=client,
#                 sem_chunk=sem_chunk,
#                 sem_theme=sem_theme,
#             )

#     try:
#         tasks = [run_pdf(p) for p in pdf_paths]
#         all_results = await asyncio.gather(*tasks)
#         print("🏁 All PDFs processed successfully.")
#         return pd.concat(all_results, ignore_index=True)
#     finally:
#         await client.close()

def split_extracted_comments(row):
    text = row.get("Extracted Commentary")
    if pd.isna(text) or not str(text).strip():
        return []

    # 1) Capture: serial, quoted comment, and the (...) with page(s)
    #    e.g. 2. "some text" (page 7)  OR  3. "foo" (pages 15, 16 & 17)
    pattern = re.compile(
        r'(\d+)\.\s+"(.*?)"\s*\((?:page|pages)\s*([^)]+)\)',
        flags=re.DOTALL | re.IGNORECASE
    )
    matches = pattern.findall(str(text))

    # 2) Normalize page numbers display: "5" | "15 & 16" | "15, 16 & 17"
    def pages_display(pages_raw: str) -> str | None:
        nums = re.findall(r'\d+', pages_raw)
        if not nums:
            return None
        if len(nums) == 1:
            return nums[0]
        if len(nums) == 2:
            return f"{nums[0]} & {nums[1]}"
        return ", ".join(nums[:-1]) + f" & {nums[-1]}"

    rows = []
    for serial, comment, pages_raw in matches:
        disp = pages_display(pages_raw)
        rows.append({
            "Company": row["Company"],
            "Theme": row["Theme"],
            "Definition": row["Definition"],
            # -> formatted exactly like: 1. comment1(page_num1)
            "Extracted Commentary": f"{serial}. {comment.strip()} ({disp})",
            # optional: keep numeric list too (useful downstream)
            "Page Numbers": [int(n) for n in re.findall(r'\d+', pages_raw)]
        })

    return pd.DataFrame(rows)


def finalizing_dataframe(raw_df):
    final_r=[]

    for rowno,row in raw_df.iterrows():
        if row['Extracted Commentary']!="N/A":
            split_df=split_extracted_comments(row)
            final_r.append(split_df)
    return pd.concat(final_r)