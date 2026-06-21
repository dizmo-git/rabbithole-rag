from sqlmodel import SQLModel, create_engine, Session
import models  # noqa

engine = create_engine("sqlite:///app.db", echo=False)


def create_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
