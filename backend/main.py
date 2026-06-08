from fastapi import FastAPI

app = FastAPI(title="Rabbithole RAG API")


@app.get("/")
async def root():
    return {"message": "Rabbithole RAG API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)