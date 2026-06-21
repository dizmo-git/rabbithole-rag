from fastapi import APIRouter
from chroma import get_vector_store
from pathlib import Path

router = APIRouter(prefix="/sources")


@router.get("/")
async def sources(notebook: str):
    collection = await get_vector_store(notebook)
    metadatas = collection.get(include=["metadatas"])["metadatas"]
    unique_sources = {Path(meta["source"]).name for meta in metadatas}
    return {"sources": unique_sources}
