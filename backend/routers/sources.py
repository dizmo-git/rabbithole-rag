import os
import shutil
import tkinter as tk

from ingestors import get_ingestor
from tkinter import filedialog
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from backend.database import get_session
from backend.models import Notebook, Source, SourceType
from backend.chroma import chunk_and_save, delete_embeddings, save_chunks
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
        select(Source).where(Source.notebook_id == notebook_id)
    ).all()

    return sources


@router.post("/addfile/")
async def upload_file(
    notebook_name: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    path = get_source_from_explorer()
    if path is None:
        raise HTTPException(status_code=204, detail="No file selected")

    return await ingest_source(
        notebook_name=notebook_name,
        path=path,
        background_tasks=background_tasks,
        session=session,
    )


@router.post("/addlink/")
async def upload_link(
    link: str,
    notebook_name: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    notebook = session.exec(
        select(Notebook).where(Notebook.name == notebook_name)
    ).first()

    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook does not exist")

    source = Source(notebook_id=notebook.id, source_type=SourceType.POST, url=link)
    session.add(source)
    session.commit()
    session.refresh(source)

    background_tasks.add_task(ingest_link, link, notebook.name, source.id)
    return source


async def ingest_link(link: str, collection: str, source_id: str) -> None:
    ingestor = get_ingestor(link)
    chunks = await ingestor.ingest(link, source_id)
    await save_chunks(chunks, collection, source_id)


@router.delete("/del/")
async def delete_source(
    source_id: str, notebook_name: str, session: Session = Depends(get_session)
):
    source = session.exec(select(Source).where(Source.id == source_id)).first()

    if source is None:
        raise HTTPException(status_code=404, detail="Source does not exist")

    notebook = session.exec(
        select(Notebook).where(Notebook.name == notebook_name)
    ).first()

    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook does not exist")

    if source.notebook_id != notebook.id:
        raise HTTPException(
            status_code=403,
            detail="Source does not belong to the specified notebook",
        )

    await delete_embeddings(source_id=source_id, collection=notebook_name)
    session.delete(source)
    session.commit()


async def ingest_source(
    notebook_name: str,
    path: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
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

    background_tasks.add_task(chunk_and_save, path, notebook.name, source.id)
    print(f"Added new pending source {dst} to {notebook_name}")
    return source


async def ingest_source_sync(
    notebook_name: str,
    path: str,
    session: Session = Depends(get_session),
):
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

    await chunk_and_save(path, notebook.name, source.id)
    print(f"Added new pending source {dst} to {notebook_name}")
    return path


def get_source_from_explorer() -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    path = filedialog.askopenfilename(filetypes=ALLOWED_FILETYPES)
    root.destroy()
    return path or None
