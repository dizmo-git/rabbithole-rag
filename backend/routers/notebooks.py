import shutil

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from backend.routers.settings import list_installed_models
from backend.routers.sources import NOTEBOOKS_PATH
from backend.database import get_session, engine
from backend.models import Notebook
from backend.settings import get_settings
from chroma import client
from sqlmodel import SQLModel, Session, select

router = APIRouter(prefix="/notebooks")


@router.get("/")
async def notebooks(session: Session = Depends(get_session)):
    names = session.exec(select(Notebook.name)).all()
    return {"names": names}


@router.post("/new")
async def new(
    name: str,
    embedding_model: str | None = None,
    session: Session = Depends(get_session),
):
    if embedding_model is None:
        # db_seed calls this directly without a model and gets the default
        embedding_model = get_settings().embedding_model
    elif embedding_model not in {m.name for m in await list_installed_models()}:
        raise HTTPException(
            status_code=400, detail=f"Model not installed: {embedding_model}"
        )

    notebook = Notebook(name=name, embedding_model=embedding_model)
    session.add(notebook)
    session.commit()
    session.refresh(notebook)
    print(f"Created new notebook: {name} (embeddings: {embedding_model})")
    return notebook


@router.post("/nuke")
async def nuke():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("All tables are deleted")

    path = Path(NOTEBOOKS_PATH).absolute()
    shutil.rmtree(path)
    path.mkdir()
    (path / ".gitkeep").touch()
    print("All notebook files are deleted")

    client.reset()
    print("All collections are deleted")
