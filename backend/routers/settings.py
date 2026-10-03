import asyncio

from fastapi import APIRouter, HTTPException
from ollama import AsyncClient
from pydantic import BaseModel

from backend.settings import AppSettings, get_settings, save_settings

router = APIRouter(prefix="/settings")


class OllamaModel(BaseModel):
    name: str
    family: str | None
    parameter_size: str | None
    # from `ollama show`, e.g. ["completion", "tools"] or ["embedding"].
    # Empty on Ollama servers too old to report it.
    capabilities: list[str]


@router.get("/")
async def read_settings() -> AppSettings:
    return get_settings()


@router.put("/")
async def update_settings(settings: AppSettings) -> AppSettings:
    installed = {m.name for m in await list_installed_models()}
    for model in (settings.chat_model, settings.embedding_model):
        if model not in installed:
            raise HTTPException(status_code=400, detail=f"Model not installed: {model}")
    save_settings(settings)
    print(f"Settings updated: {settings}")
    return settings


@router.get("/models")
async def models() -> list[OllamaModel]:
    return await list_installed_models()


async def list_installed_models() -> list[OllamaModel]:
    client = AsyncClient()
    try:
        listed = [m for m in (await client.list()).models if m.model]
        # `list` doesn't say what a model can do, only `show` does, one call per model
        shown = await asyncio.gather(*(client.show(m.model) for m in listed))
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama is not reachable")

    return [
        OllamaModel(
            name=m.model,  # type: ignore[arg-type]  # filtered above
            family=m.details.family if m.details else None,
            parameter_size=m.details.parameter_size if m.details else None,
            capabilities=s.capabilities or [],
        )
        for m, s in zip(listed, shown)
    ]
