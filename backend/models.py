from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid


class Notebook(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Source(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    notebook_id: str = Field(foreign_key="notebook.id")
    filename: str
    file_path: str  # data/notebooks/<notebook_id>/<filename>
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")
