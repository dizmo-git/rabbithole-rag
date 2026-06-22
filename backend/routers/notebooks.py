import shutil

from pathlib import Path
from fastapi import APIRouter, Depends
from backend.routers.sources import NOTEBOOKS_PATH
from backend.database import get_session, engine
from backend.models import Notebook
from chroma import client
from sqlmodel import SQLModel, Session, select

router = APIRouter(prefix="/notebooks")


@router.get("/")
async def notebooks(session: Session = Depends(get_session)):
    names = session.exec(select(Notebook.name)).all()
    return {"names": names}


@router.post("/new")
async def new(name: str, session: Session = Depends(get_session)):
    notebook = Notebook(name=name)
    session.add(notebook)
    session.commit()
    session.refresh(notebook)
    print(f"Created new notebook: {name}")
    return notebook


@router.post("/nuke")
async def nuke():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("All tables are deleted")

    path = Path(NOTEBOOKS_PATH).absolute()
    shutil.rmtree(path)
    path.mkdir()
    print("All notebook files are deleted")

    client.reset()
    print("All collections are deleted")
