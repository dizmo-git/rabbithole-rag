from typing import Any, Mapping, Sequence

from fastapi import APIRouter
from backend.chroma import get_vector_store
from backend.chroma import model
from ollama import ChatResponse
from ollama import chat

from backend.models import Message

router = APIRouter(prefix="/query")


@router.post("/")
async def ask(conversation: list[Message], notebook: str):
    question = conversation[-1].content
    collection = await get_vector_store(notebook)
    results = collection.similarity_search_with_relevance_scores(question, k=3)

    for i in range(len(results)):
        print(f"Similarity for chunk {i}:\t{results[i][1]}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    response: ChatResponse = chat(
        model=model,
        messages=map_messages(conversation=conversation, context=context_text),
    )

    return {"answer": response.message.content}


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
