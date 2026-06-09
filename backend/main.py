from fastapi import FastAPI
from contextlib import asynccontextmanager
from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

FILE_PATH = "../data/Alice's_Adventures_in_Wonderland.txt"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Test chunking
    await chunk_data()

    yield

    # Clean up
    print("Bye bye (⌐■_■)")

app = FastAPI(title="Rabbithole RAG API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Rabbithole RAG API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def get_docs():
    loader = DoclingLoader(file_path=FILE_PATH)
    return loader.load()

async def chunk_data():
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 500,
        length_function = len,
        add_start_index = True
    )

    documents = await get_docs()
    chunks = text_splitter.split_documents(documents)

    print(f"Split {len(documents)} documents into {len(chunks)} chunks")
    document = chunks[10]
    print(document.page_content)
    print(document.metadata)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)