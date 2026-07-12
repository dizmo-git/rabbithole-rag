from sqlmodel import SQLModel, Field
from datetime import datetime
from enum import Enum
import uuid
from pydantic import BaseModel


class SourceType(str, Enum):
    FILE = "file"
    POST = "post"


class Notebook(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Source(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    notebook_id: str = Field(foreign_key="notebook.id")
    source_type: SourceType = Field(default=SourceType.FILE)
    filename: str | None = None
    file_path: str | None = None
    url: str | None = None  # populated for POST sources instead of filename/file_path
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")


class Message(BaseModel):
    role: Role
    content: str


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Platform(str, Enum):
    HN = "hn"
    REDDIT = "reddit"
    LOCAL = "local"


class PostOrigin(BaseModel):
    platform: Platform
    external_id: str  # platform's native id
    author: str | None
    origin_date: datetime  # when the post/comment was actually made
    permalink: str | None
    ancestor_ids: list[str]  # root -> immediate parent, chunk ids. Empty for root posts
    # do not write straight into Chroma metadata, it rejects empty lists.


class Chunk(BaseModel):
    id: str  # same as in chroma
    source_id: str  # source.id in app.db: notebook_id/uploaded_at live there, not here
    source_type: SourceType
    chunk_index: int  # position within this one source-unit (doc, or single post/comment), not thread-wide
    content: str
    origin: PostOrigin | None  # None for FILE, required for POST
