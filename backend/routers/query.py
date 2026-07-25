from typing import Any, AsyncIterable, Mapping, Sequence

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.chroma import get_vector_store
from backend.chroma import model
from ollama import AsyncClient, ChatResponse
from ollama import chat
import re

from backend.models import Message

router = APIRouter(prefix="/query")


@router.post("/", response_class=StreamingResponse)
async def ask(conversation: list[Message], notebook: str) -> StreamingResponse:
    question = conversation[-1].content
    collection = await get_vector_store(notebook)

    queries = await enhance_query(question)
    print(queries)

    seen_ids = set()
    combined_results = []
    for q in queries:
        results = collection.similarity_search_with_relevance_scores(q, k=10)
        for doc, score in results:
            doc_id = doc.metadata.get("id", doc.page_content)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined_results.append((doc, score))

    combined_results.sort(key=lambda x: x[1], reverse=True)
    top_results = combined_results[:10]

    for i, (doc, score) in enumerate(top_results):
        print(f"Similarity for chunk {i}:\t{score}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in top_results])
    print(context_text)

    async def generate() -> AsyncIterable[str]:
        client = AsyncClient()
        async for chunk in await client.chat(
            model=model,
            messages=map_messages(conversation=conversation, context=context_text),
            stream=True,
            options={"temperature": 0.3},
        ):
            if chunk.message.content:
                yield chunk.message.content

    return StreamingResponse(generate(), media_type="text/plain")


async def enhance_query(question: str) -> list[str]:
    client = AsyncClient()
    response: ChatResponse = await client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a search query generator for a semantic search system "
                    "indexing a knowledge base of documents.\n\n"
                    "Given a user's question, generate 3 alternative search queries "
                    "that would help retrieve relevant passages from this index.\n\n"
                    "Rules:\n"
                    "- Vary vocabulary, phrasing, and specificity so the queries surface "
                    "content that discusses the same topic using different words than "
                    "the original question.\n"
                    "- Each query should be short: a phrase or a single sentence, not a "
                    "paragraph.\n"
                    "- Do not answer the user's question.\n"
                    "- Do not include explanations, numbering, labels, or any other text.\n"
                    "- Output exactly 3 queries, one per line, and nothing else."
                ),
            },
            {"role": "user", "content": question},
        ],
        options={"temperature": 0.6},
    )

    raw_lines = response.message.content.splitlines()  # type: ignore
    rewrites = [_clean_query_line(line) for line in raw_lines]
    rewrites = [line for line in rewrites if line]

    return [question] + rewrites


def _clean_query_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^\d+[\.\)]\s*", "", line)  # strip "1. " / "1) "
    line = re.sub(r"^[-*•]\s*", "", line)  # strip "- " / "* " / "• "
    return line.strip()


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
