import asyncio
from click import prompt
from openai import AsyncOpenAI, OpenAI
import json 
import pandas as pd
from helper_functions.indexing import reading_yaml
from concurrent.futures import ThreadPoolExecutor, as_completed 
import streamlit as st
from pathlib import Path

def apply_theme():
    """Inject custom CSS theme."""
    css_file = Path(__file__).resolve().parent.parent / "theme.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Theme file not found at {css_file}")

apply_theme()



prompts=reading_yaml("prompts.yaml")

  # Tune this: start with 5–15


# ---------------------------------------------
# 🔹 Validate a single row
# ---------------------------------------------
def validate_row(item, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    index, row = item
    try:
        prompt = prompts["confidence_and_rationale_prompt"].format(
            theme_name=row["Theme"],
            definition=row["Definition"],
        )
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": row["Extracted Commentary"]},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        resp = completion.choices[0].message.content.strip()
        data = json.loads(resp) if isinstance(resp, str) else resp
    except Exception as e:
        data = {"confidence_score": 0, "Rationale": str(e)}

    return {
        "Company": row["Company"],
        "Theme": row["Theme"],
        "Definition": row["Definition"],
        "Extracted Commentary": row["Extracted Commentary"],
        "Page nums": row.get("Page Numbers", ""),
        **data,
    }


# ---------------------------------------------
# 🔹 Validate all rows (with live updating)
# ---------------------------------------------
def validate_all_rows(df, openai_api_key, max_workers=5):
    total = len(df)
    completed = 0
    results = []

    # --- Streamlit UI placeholders
    progress_bar = st.progress(0.0)
    progress_text = st.empty()
    live_table = st.empty()  # 👈 this will dynamically render results

    # --- Start threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(validate_row, item, openai_api_key): item[0]
            for item in df.iterrows()
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            # --- Update progress UI
            pct = completed / total
            progress_bar.progress(pct)
            progress_text.text(f"Validated {completed}/{total} rows ({pct*100:.1f}%)")

            # --- Update live table (convert results to DataFrame)
            current_df = pd.DataFrame(results)
            live_table.dataframe(current_df, use_container_width=True)

    # --- Final completion state
    progress_bar.progress(1.0)
    progress_text.text(f"✅ Validation complete ({total}/{total})")

    return pd.DataFrame(results)

async def avalidate_row(item, openai_api_key):

    client = AsyncOpenAI(api_key=openai_api_key)
    index, row = item

    try:
        prompt = prompts['confidence_and_rationale_prompt'].format(
            theme_name=row['Theme'],
            definition=row['Definition']
        )

        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": row['Extracted Commentary']}
            ],
            temperature=0.4,
            response_format={"type": "json_object"} 
        )
        resp = completion.choices[0].message.content.strip()
        data = json.loads(resp) if isinstance(resp, str) else resp

    except Exception as e:
        data = {'confidence_score': 0, 'Rationale': str(e)}

    return {
        'Company': row['Company'],
        'Theme': row['Theme'],
        'Definition': row['Definition'],
        'Extracted Commentary': row['Extracted Commentary'],
        "Page nums": row["Page Numbers"],
        **data
    }


async def process_batch(batch, openai_api_key):

    tasks = [avalidate_row(item, openai_api_key) for item in batch]
    return await asyncio.gather(*tasks)

async def avalidate_all_without_saving(df, openai_api_key,batch_size=100):
    results = []

    rows = list(df.iterrows())

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        batch_results = await process_batch(batch, openai_api_key)
        results.extend(batch_results)

    return pd.DataFrame(results)
