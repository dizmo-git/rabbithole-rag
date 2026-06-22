import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_session
from backend.models import Notebook, Source
from backend.chroma import chunk_and_save
from pathlib import Path
from sqlmodel import Session, select

router = APIRouter(prefix="/sources")
NOTEBOOKS_PATH = Path(__file__).parent.parent.parent / "data" / "notebooks"


@router.get("/")
async def sources(notebook: str, session: Session = Depends(get_session)):
    notebook_id = session.exec(
        select(Notebook.id).where(Notebook.name == notebook)
    ).first()
    sources = session.exec(
        select(Source.filename).where(Source.notebook_id == notebook_id)
    ).all()

    return {"sources": sources}


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
