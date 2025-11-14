from openai import AsyncOpenAI
from helper_functions.indexing import reading_yaml
import asyncio
import streamlit as st

prompts=reading_yaml("prompts.yaml")


async def summarize_commentary(comp_name,theme_name,openai_api_key,user_prompt, df_filtered_conf,cross_firm_wise=True):
    client = AsyncOpenAI(api_key=openai_api_key)
    resp=None
    
    if cross_firm_wise:
        df_filtered_matrix=df_filtered_conf[(df_filtered_conf['Company']==comp_name) & (df_filtered_conf['Theme']==theme_name)]
        concatenated_comments = " ".join(df_filtered_matrix['Extracted Commentary'].tolist())
        input_prompt="Inputs:\n"+prompts['summarizing_prompt_theme_cross_firm_l1_level']['Inputs'].format(theme_name=theme_name, extracted_commentary=concatenated_comments)
        user_prompt="User Prompt:\n"+user_prompt
        output_prompt="Outputs:\n"+prompts['summarizing_prompt_theme_cross_firm_l1_level']['Output']
        summarizing_prompt=input_prompt +"\n" +user_prompt + "\n" +output_prompt
    else: 
        df_filtered_matrix=df_filtered_conf[df_filtered_conf['Theme']==theme_name]
        summarizing_prompt=user_prompt
        
    try:
       summarizing_prompt = summarizing_prompt
       completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": summarizing_prompt},
            ],
            temperature=0.4,
        )
       print("Done with theme:", theme_name, "Done for Company:", comp_name,"No of comments:",len(df_filtered_matrix['Extracted Commentary'].tolist()))
       resp = completion.choices[0].message.content.strip()
       
    except Exception as e:
        print("Getting error:", theme_name)
        return e

    return {'Company': comp_name, 'Theme': theme_name, 'Summary': resp}

async def summarizing_commentaries(df,user_prompt, openai_api_key,theme_cross_firm_wise=True):
    comp_list=sorted(df['Company'].unique())
    themes_list=sorted(df['Theme'].unique())
    comp_cross_theme=[(comp, theme) for comp in comp_list for theme in themes_list]
    
    df_filtered_conf=df[df['confidence_score']>6]

    if theme_cross_firm_wise:
        tasks = [summarize_commentary(comp_name, theme_name,openai_api_key,user_prompt=user_prompt, df_filtered_conf=df_filtered_conf, cross_firm_wise=theme_cross_firm_wise) for comp_name, theme_name in comp_cross_theme]
        return await asyncio.gather(*tasks)
    else:
        tasks = [summarize_commentary(theme_name=theme_name,openai_api_key=openai_api_key, user_prompt=user_prompt, df_filtered_conf=df_filtered_conf, cross_firm_wise=theme_cross_firm_wise, comp_name=None) for theme_name in themes_list]
        return await asyncio.gather(*tasks)