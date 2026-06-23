import os
import shutil
import tkinter as tk

from tkinter import filedialog
from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_session
from backend.models import Notebook, Source
from backend.chroma import chunk_and_save
from pathlib import Path
from sqlmodel import Session, select

router = APIRouter(prefix="/sources")
NOTEBOOKS_PATH = Path(__file__).parent.parent.parent / "data" / "notebooks"
ALLOWED_FILETYPES = [
    ("Documents", "*.pdf *.txt *.md"),
    ("All files", "*.*"),
]


@router.get("/")
async def sources(notebook: str, session: Session = Depends(get_session)):
    notebook_id = session.exec(
        select(Notebook.id).where(Notebook.name == notebook)
    ).first()
    sources = session.exec(
        select(Source.filename).where(Source.notebook_id == notebook_id)
    ).all()

    return {"sources": sources}


@router.post("/add/")
async def from_explorer(notebook_name: str, session: Session = Depends(get_session)):
    path = get_source_from_explorer()
    if path is None:
        raise HTTPException(status_code=204, detail="No file selected")

    return await add(notebook_name=notebook_name, path=path, session=session)


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


def get_source_from_explorer() -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    path = filedialog.askopenfilename(filetypes=ALLOWED_FILETYPES)
    root.destroy()
    return path or None
