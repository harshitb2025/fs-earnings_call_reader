
from langchain_openai import OpenAIEmbeddings


# FIRST INSTALL LLAMA3.2 MODEL FROM OLLMA, THEN UNCOMMENT THIS CODE
# from langchain_ollama import OllamaEmbeddings
# def ollama_embeddings(model_name="llama3.2"):
#     embedding_ollama = OllamaEmbeddings(
#         model=model_name,
#     )
#     return embedding_ollama



def openai_embeddings(model_name="text-embedding-ada-002", api_key=None):
    openai_embeds = OpenAIEmbeddings(
        model=model_name,
        api_key=api_key
    )
    return openai_embeds
