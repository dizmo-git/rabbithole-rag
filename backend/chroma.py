from typing import NoReturn

import chromadb
import asyncio
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata
from sqlmodel import Session

from backend import database
from backend.models import Chunk, Source

CHROMA_PATH = "chroma"
BATCH_SIZE = 50

embeddings = OllamaEmbeddings(model="nomic-embed-text")
model = "llama3.2:latest"

client = chromadb.PersistentClient(
    path=CHROMA_PATH, settings=Settings(allow_reset=True)
)


async def get_vector_store(name: str):
    return Chroma(
        client=client,
        collection_name=name,
        embedding_function=embeddings,
    )


async def chunk_and_save(file: str, collection: str, source_id: str) -> None:
    loop = asyncio.get_event_loop()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=50, length_function=len, add_start_index=True
    )

    documents = await loop.run_in_executor(
        None, lambda: DoclingLoader(file_path=file).load()
    )
    chunks = text_splitter.split_documents(documents)

    # Just testing for now
    for chunk in chunks:
        chunk.metadata["source_id"] = source_id

    await save_to_chroma(chunks, collection)

    with Session(database.engine) as session:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError("Source not found")
        source.status = "processed"
        session.add(source)
        session.commit()


async def save_to_chroma(
    documents: list[Document], collection: str, ids: list[str] | None = None
) -> None:
    loop = asyncio.get_event_loop()
    vector_store = await get_vector_store(collection)
    filtered_documents = filter_complex_metadata(documents)

    for i in range(0, len(filtered_documents), BATCH_SIZE):
        doc_batch = filtered_documents[i : i + BATCH_SIZE]
        id_batch = ids[i : i + BATCH_SIZE] if ids else None
        await loop.run_in_executor(
            None, lambda b=doc_batch, ib=id_batch: vector_store.add_documents(b, ids=ib)
        )
        print(f"Saved {len(doc_batch)} chunks to {CHROMA_PATH}.")


async def save_chunks(chunks: list[Chunk], collection: str, source_id: str) -> None:
    documents = chunks_to_documents(chunks)
    await save_to_chroma(documents, collection, ids=[c.id for c in chunks])

    with Session(database.engine) as session:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError("Source not found")
        source.status = "processed"
        session.add(source)
        session.commit()


async def delete_embeddings(source_id: str, collection: str):
    vector_store = await get_vector_store(collection)
    vector_store.delete(where={"source_id": source_id})


def chunks_to_documents(chunks: list[Chunk]) -> list[Document]:
    documents = []
    for c in chunks:
        metadata: dict = {
            "source_id": c.source_id,  # same key delete_embeddings already filters on
            "source_type": c.source_type.value,
            "chunk_index": c.chunk_index,
        }
        if c.origin:
            metadata["platform"] = c.origin.platform.value
            metadata["external_id"] = c.origin.external_id
            metadata["origin_date"] = c.origin.origin_date.isoformat()
            if c.origin.author:
                metadata["author"] = c.origin.author
            if c.origin.permalink:
                metadata["permalink"] = c.origin.permalink
            if c.origin.ancestor_ids:
                metadata["immediate_parent_id"] = c.origin.ancestor_ids[-1]
        documents.append(Document(page_content=c.content, metadata=metadata))
    return documents
