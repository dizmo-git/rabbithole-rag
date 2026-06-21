import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from database import get_session
from models import Notebook, Source
from chroma import chunk_and_save, get_vector_store
from pathlib import Path
from sqlmodel import Session, select

router = APIRouter(prefix="/sources")
NOTEBOOKS_PATH = Path(__file__).parent.parent.parent / "data" / "notebooks"


# TODO: Query from sqlite
@router.get("/")
async def sources(notebook: str):
    collection = await get_vector_store(notebook)
    metadatas = collection.get(include=["metadatas"])["metadatas"]
    unique_sources = {Path(meta["source"]).name for meta in metadatas}
    return {"sources": unique_sources}


@router.post("/add")
async def add(notebook_name: str, path: str, session: Session = Depends(get_session)):
    notebook = session.exec(
        select(Notebook).where(Notebook.name == notebook_name)
    ).first()

    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook does not exist")

    src = Path(path).absolute()
    dst = Path(
        os.path.join(Path(NOTEBOOKS_PATH).absolute(), f"{notebook.id}/{src.name}")
    )

    if not src.exists():
        raise HTTPException(status_code=404, detail="File does not exist")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src=src, dst=dst)

    source = Source(notebook_id=notebook.id, file_path=str(dst), filename=dst.name)
    session.add(source)
    session.commit()
    session.refresh(source)

    await chunk_and_save(path, notebook.name)
    print(f"Added new source {dst} to {notebook_name}")
    return path
