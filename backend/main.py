import os
import shutil
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

FILE_PATH = "../data/Alice's_Adventures_in_Wonderland.txt"
CHROMA_PATH = "chroma"

origins = ["http://localhost", "http://localhost:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Test chunking
    await chunk_data()

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


@app.get("/")
async def root():
    return {"message": "Rabbithole RAG API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/ask")
async def ask(question: str):
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=OllamaEmbeddings(model="nomic-embed-text"),
    )

    results = db.similarity_search_with_relevance_scores(question, k=3)

    for i in range(len(results)):
        print(f"Similarity for chunk {i}:\t{results[i][1]}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    # hard coded for now
    response: ChatResponse = chat(
        model="llama3.2:latest",
        messages=[{"role": "user", "content": f"{question}\n\n\n{context_text}"}],
    )

    return {"answer": response.message.content}


async def get_docs():
    loader = DoclingLoader(file_path=FILE_PATH)
    return loader.load()


async def chunk_data():
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=500, length_function=len, add_start_index=True
    )

    documents = await get_docs()
    chunks = text_splitter.split_documents(documents)

    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    await save_to_chroma(chunks)


async def save_to_chroma(chunks: list[Document]):
    filtered_chunks = filter_complex_metadata(chunks)

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    db = Chroma.from_documents(
        filtered_chunks,
        embedding=OllamaEmbeddings(model="nomic-embed-text"),
        persist_directory=CHROMA_PATH,
    )

    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
