import os
import shutil
import chromadb
from ollama import chat
from ollama import ChatResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_chroma import Chroma
from contextlib import asynccontextmanager
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata

TEST_FILES = [
    "../data/Alice's_Adventures_in_Wonderland.txt",
    "../data/Nietzsche_The_Greek_State.txt",
]
CHROMA_PATH = "chroma"

embeddings = OllamaEmbeddings(model="nomic-embed-text")
model = "llama3.2:latest"

persistence = chromadb.PersistentClient(CHROMA_PATH)
vectore_store: Chroma | None = None

origins = ["http://localhost", "http://localhost:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(await notebooks())
    notebook = "Alice"  # Or Nietzsche
    await open(notebook)
    await chunk_data(0)  # 0 for Alice; 1 for Nietzsche

    yield

    # Clean up
    print("Bye bye (⌐■_■)")


app = FastAPI(title="Rabbithole RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/open")
async def open(name: str):
    global vectore_store
    vectore_store = await get_vector_store(name=name)
    return {"result": "success"}


@app.get("/notebooks")
async def notebooks():
    collections = persistence.list_collections()
    names = [n.name for n in collections]
    return {"names": names}


@app.get("/ask")
async def ask(question: str):
    if vectore_store is None:
        raise RuntimeError("Vectorstore not initialized")

    results = vectore_store.similarity_search_with_relevance_scores(question, k=3)

    for i in range(len(results)):
        print(f"Similarity for chunk {i}:\t{results[i][1]}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    # hard coded for now
    response: ChatResponse = chat(
        model=model,
        messages=[{"role": "user", "content": f"{question}\n\n\n{context_text}"}],
    )

    return {"answer": response.message.content}


async def get_vector_store(name: str):
    return Chroma(
        client=persistence,
        collection_name=name,
        embedding_function=embeddings,
    )


async def chunk_data(file: int):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=500, length_function=len, add_start_index=True
    )

    documents = DoclingLoader(file_path=TEST_FILES[file]).load()
    chunks = text_splitter.split_documents(documents)

    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    await save_to_chroma(chunks)


async def save_to_chroma(chunks: list[Document]):
    if vectore_store is None:
        raise RuntimeError("Vectorstore not initialized")

    filtered_chunks = filter_complex_metadata(chunks)

    vectore_store.reset_collection()
    vectore_store.add_documents(filtered_chunks)

    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
