from langchain_community.retrievers import BM25Retriever,TFIDFRetriever
from langchain.retrievers import EnsembleRetriever


def context_from_pdf(query,vector_db,k):
    retrieved_docs = vector_db.similarity_search(query = query, k = 5)
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return docs_content



def combined_context_with_page_numbers(relevant_docs):
    """
    Combine the page numbers and the LAST header (if present) with the document content for better context.
    """
    combined_docs = []

    for doc in relevant_docs:
        page_numbers = doc.metadata.get("pageno", [])
        
        # Get all headers in sorted order and pick the last one
        header_keys = [k for k in doc.metadata.keys() if "header" in k.lower()]
        header_keys = sorted(header_keys)  # Sort to get 'Header 1', 'Header 2', etc. in order

        last_header = ""
        if header_keys:
            last_header = doc.metadata.get(header_keys[-1], "")  # Pick value of last header key

        pages_str = ", ".join(str(p) for p in page_numbers)

        # Build the content
        content_with_pages = f"### Chunk from page(s): {pages_str}\n"
        
        if last_header:
            content_with_pages += f"**Section: {last_header}**\n\n"

        content_with_pages += f"{doc.page_content}"
        combined_docs.append(content_with_pages)

    return "\n\n---\n\n".join(combined_docs)



## DENSE VECTOR SEARCH 

def dense_vector_retriver(vector_db):
    return vector_db.as_retriever(kwargs={"k":20})

def dense_vector_search(query, vector_db):
    dense_ret=dense_vector_retriver(vector_db=vector_db)
    return dense_ret.invoke(input=query)

## LEXICAL SEARCH
def lexical_retriever(chunks, search_type):
    if search_type=="bm25-retriever":
        return BM25Retriever.from_documents(documents=chunks)
    elif search_type=="tf-idf-retriever":
        return TFIDFRetriever.from_documents(documents=chunks)
    else: 
        raise NameError("Enter correct search type")
    
def lexical_search(query, chunks, search_type="bm25-retriever"):
    retriever=lexical_retriever(chunks=chunks, search_type=search_type)

    return retriever.invoke(input=query, kwargs={"k":20})

## HYBRID SEARCH(LEXICAL+DENSE)
def hybrid_retriever(chunks, vector_db, lexical_search_type,lexical_weight, dense_vector_weight):
    bm25_ret=lexical_retriever(chunks=chunks, search_type=lexical_search_type)
    vector_db_ret=dense_vector_retriver(vector_db=vector_db)
    ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_ret, vector_db_ret], weights=[lexical_weight, dense_vector_weight]
)
    return ensemble_retriever

def hybrid_search(query, chunks, vector_db, lexical_search_type="bm25-retriever", lexical_weight=0.5, dense_vector_weight=0.5):
    ensemble_retriever=hybrid_retriever(chunks=chunks, vector_db=vector_db, lexical_search_type=lexical_search_type, lexical_weight=lexical_weight, dense_vector_weight=dense_vector_weight)
    return ensemble_retriever.invoke(query, kwargs={'k':20})