from langchain_core.documents import Document
import re
from langchain_text_splitters import MarkdownHeaderTextSplitter



def text_to_docs(chunk_list, pageno_list):
    doc_list = []
    for chunkno, chunk in enumerate(chunk_list):
        if isinstance(chunk, Document):
            # Add "pageno" to existing metadata
            chunk.metadata["pageno"] = pageno_list[chunkno]
            doc = chunk
        else:
            # Create a new Document
            doc = Document(metadata={"pageno": pageno_list[chunkno]}, page_content=chunk)
        doc_list.append(doc)
    return doc_list



def markdown_text_split(text:str, headers_to_split_on:list):
    markdown_chunk_splitter=MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    markdown_chunks=markdown_chunk_splitter.split_text(text=text)
    return markdown_chunks



def markdown_chunk_split(documents:str, headers_to_split_on=[("#", 1), ("##", 2), ("###", 3), ("####", 4), ("#####", 5)]):
    markdown_chunk_splitter=MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    markdown_chunks=markdown_chunk_splitter.split_text(text=documents)
    return markdown_chunks



def extract_page_numbers_from_chunks(chunks):
    page_assignments = []
    current_page = 1

    for chunk in chunks:
        # Handle both raw string chunks and document objects
        text = chunk.page_content if hasattr(chunk, 'page_content') else chunk

        matches = list(re.finditer(r"<start_of_page_(\d+)>", text))
        pages = set()

        if matches:
            starts_with = text.strip().startswith(matches[0].group(0))
            ends_with = text.strip().endswith(matches[-1].group(0))

            for i, match in enumerate(matches):
                marker_page = int(match.group(1))

                if i == 0 and starts_with:
                    pages.add(marker_page)
                elif i == len(matches) - 1 and ends_with:
                    pages.add(marker_page - 1)
                else:
                    pages.add(current_page)
                    pages.add(marker_page)

                current_page = marker_page

        else:
            pages.add(current_page)

        page_assignments.append(sorted(pages))

    return page_assignments

