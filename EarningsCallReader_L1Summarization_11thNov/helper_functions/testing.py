from openai import AsyncOpenAI
import os
import asyncio
from helper_functions.indexing import *



prompts=reading_yaml("prompts.yaml")
def filter_dataframe_company_basis(df, comp_name):

    comp_name=comp_name.lower()

    return df[
        df['Company'].str.lower()==comp_name
    ]

def update_definition_tag(definition_template: str = None):
    """
    Uses OpenAI's GPT model to rewrite or generate a tagging definition
    based on the given prompt text and template.

    Args:
        prompt_text (str): The core instructions or keywords for tagging.
        definition_template (str, optional): Existing definition text to be rewritten. Defaults to None.

    Returns:
        str: Updated or newly generated definition.
    """

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt_text = """
Tag if discussion includes strategy, strategic priorities, ambition, focus, roadmap, trajectory, expectation, approach, management, portfolio, potential.
Also include words like scalability, expansion, diversification, entering new markets, market positioning, value proposition.
Additionally include reallocation, realignment, leadership, differentiator, proposition.
"""

    # Construct the system + user messages
    messages = [
        {"role": "system", "content": "You are a precise assistant that writes tag definitions for an internal tagging app."},
        {"role": "user", "content": f"Rewrite the following definition in a clear and standardized format:\n\n{prompt_text}"}
    ]

    if definition_template:
        messages.append({
            "role": "user",
            "content": f"Existing definition:\n{definition_template}\n\nPlease rewrite or expand it following the same structure."
        })

    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


async def generate_summary_for_all_summaries(summarized_df, comp_name):

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    summarized_df=filter_dataframe_company_basis(summarized_df, comp_name)
    prompt_text=""

    for rowno, row in summarized_df.iterrows():
        prompt_text+=f"Company name: {row['Company']}"
        prompt_text+=f"Theme name:{row['Theme']}\n"
        prompt_text+=str(row['Summary'])
        prompt_text+="\n\n"


    # Construct the system + user messages
    messages = [
        {"role": "system", "content": "You are a precise assistant in generating summary for the given corpus."},
        {"role": "user", "content": prompts['uber_summary_prompt'].format(prompt_text=prompt_text)}
    ]


    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=1
    )

    return response.choices[0].message.content.strip()
    
async def uber_theme_summary_wise(summarized_df):
    
    comp_names = summarized_df['Company'].unique().tolist()

    
    theme_summary_dict=[generate_summary_for_all_summaries(summarized_df=summarized_df, comp_name=comp_name) for comp_name in comp_names]

    summaries= await asyncio.gather(*theme_summary_dict)

    theme_summary_dict=dict(zip(comp_names, summaries))

    return theme_summary_dict
