from typing import Any, AsyncIterable, Mapping, Sequence

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.chroma import get_vector_store
from backend.chroma import model
from ollama import AsyncClient, ChatResponse
from ollama import chat

from backend.models import Message

router = APIRouter(prefix="/query")


@router.post("/", response_class=StreamingResponse)
async def ask(conversation: list[Message], notebook: str) -> StreamingResponse:
    question = conversation[-1].content
    collection = await get_vector_store(notebook)
    results = collection.similarity_search_with_relevance_scores(question, k=3)

    for i in range(len(results)):
        print(f"Similarity for chunk {i}:\t{results[i][1]}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    print(context_text)

    async def generate() -> AsyncIterable[str]:
        client = AsyncClient()
        async for chunk in await client.chat(
            model=model,
            messages=map_messages(conversation=conversation, context=context_text),
            stream=True,
        ):
            if chunk.message.content:
                yield chunk.message.content

    return StreamingResponse(generate(), media_type="text/plain")


def map_messages(conversation: list[Message], context: str):
    result = []
    result.extend(construct_system_prompt(context=context))

    for m in conversation:
        result.append(
            {
                "role": m.role.value,
                "content": m.content,
            }
        )

    return result


def construct_system_prompt(context: str):
    return [
        {
            "role": "system",
            "content": (
                "You are a helpful research assistant. Answer the user's question "
                "using the context below when it's relevant. If the context doesn't "
                "help, ignore it and answer from your own knowledge, and say so.\n\n"
                f"Context:\n{context}"
            ),
        },
        {
            "role": "assistant",
            "content": "Understood. I will use the provided context when relevant, and rely on my own knowledge otherwise, letting you know which I'm doing.",
        },
    ]
