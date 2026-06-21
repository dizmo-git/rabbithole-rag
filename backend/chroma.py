import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata

CHROMA_PATH = "chroma"

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


# Only used for testing inside a main.py


async def chunk_and_save(file: str, collection: str):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=500, length_function=len, add_start_index=True
    )

    documents = DoclingLoader(file_path=file).load()
    chunks = text_splitter.split_documents(documents)

    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    await save_to_chroma(chunks, collection)


async def save_to_chroma(chunks: list[Document], collection: str):
    vector_store = await get_vector_store(collection)
    filtered_chunks = filter_complex_metadata(chunks)

    vector_store.reset_collection()
    vector_store.add_documents(filtered_chunks)

    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")
