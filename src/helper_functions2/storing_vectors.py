from uuid import uuid4
from langchain_chroma import Chroma
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss

def add_documents_in_db(vector_db,all_chunks):
    uuids = [str(uuid4()) for _ in range(len(all_chunks))]                  #INDEXING CHUNKS IN VECTOR DATABASES

    vector_db.add_documents(documents=all_chunks, ids=uuids)

    return vector_db


def faiss_vectordb(embedding_function):
    index = faiss.IndexFlatL2(len(embedding_function.embed_query("hello world")))

    vector_faiss = FAISS(
        embedding_function=embedding_function,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    return vector_faiss


def chroma_vectordb(embedding_function):
    vector_store_chroma = Chroma(
    collection_name="example_collection2",
    embedding_function=embedding_function
    # persist_directory="./chroma_langchain_db",  # Uncommnet it if you wanna save embeddings locally
)
    return vector_store_chroma