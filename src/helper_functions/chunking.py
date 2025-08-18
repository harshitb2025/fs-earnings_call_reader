import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from typing import List, Literal, Optional, Dict


def markdown_chunking(markdown_text: str, headers=[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]) -> List[str]:
    headers = headers 
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
    chunks = splitter.split_text(markdown_text)
    return [chunk.page_content for chunk in chunks]


def recursive_chunking(texts, chunk_size = 100000, chunk_overlap = 10000):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = splitter.create_documents(texts)
    chunks = splitter.split_documents(docs)
    return [chunk.page_content for chunk in chunks]


def semantic_chunking(text: str, openai_api_key: str) -> List[str]:
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    splitter = SemanticChunker(embeddings)
    docs = splitter.create_documents([text])
    return [doc.page_content for doc in docs]


def chunk_text(
    text,
    method = "markdown",
    config = None
):
    config = config or {}

    if method == "markdown":
        return markdown_chunking(text, headers=config.get("headers"))

    elif method == "recursive":
        return recursive_chunking(
            texts=[text],
            chunk_size=config.get("chunk_size", 100000),
            chunk_overlap=config.get("chunk_overlap", 10000),
        )

    elif method == "markdown+recursive":
        markdown_chunks = markdown_chunking(text, headers=config.get("headers"))
        return recursive_chunking(
            texts=markdown_chunks,
            chunk_size=config.get("chunk_size", 100000),
            chunk_overlap=config.get("chunk_overlap", 10000),
        )

    elif method == "semantic":
        return semantic_chunking(
            text=text,
            openai_api_key=config["openai_api_key"]
        )

    else:
        raise ValueError(f"Unsupported chunking method: {method}")


