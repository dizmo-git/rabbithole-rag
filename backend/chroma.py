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
from backend.models import Source

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


async def chunk_and_save(file: str, collection: str, source_id: str):
    loop = asyncio.get_event_loop()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=50, length_function=len, add_start_index=True
    )

    documents = await loop.run_in_executor(
        None, lambda: DoclingLoader(file_path=file).load()
    )
    chunks = text_splitter.split_documents(documents)

    await save_to_chroma(chunks, collection)

    with Session(database.engine) as session:
        source = session.get(Source, source_id)
        if source is None:
            raise RuntimeError("Source not found")
        source.status = "processed"
        session.add(source)
        session.commit()


async def save_to_chroma(chunks: list[Document], collection: str):
    loop = asyncio.get_event_loop()
    vector_store = await get_vector_store(collection)
    filtered_chunks = filter_complex_metadata(chunks)

    for i in range(0, len(filtered_chunks), BATCH_SIZE):
        batch = filtered_chunks[i : i + BATCH_SIZE]
        await loop.run_in_executor(None, lambda b=batch: vector_store.add_documents(b))
        print(f"Saved {len(batch)} chunks to {CHROMA_PATH}.")
