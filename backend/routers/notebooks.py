from fastapi import APIRouter
from chroma import client
from chroma import get_vector_store

router = APIRouter(prefix="/notebooks")


@router.get("/")
async def notebooks():
    collections = client.list_collections()
    names = [n.name for n in collections]
    return {"names": names}
