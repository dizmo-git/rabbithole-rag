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

ANCESTOR_K = 1
MIN_RELEVANCE_SCORE = 0.3
MAX_ROOT_WALK = 25


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
    combined_results = [r for r in combined_results if r[1] >= MIN_RELEVANCE_SCORE]
    top_results = combined_results[:10]

    for i, (doc, score) in enumerate(top_results):
        print(f"Similarity for chunk {i}:\t{score}")

    context_text = build_context(collection, top_results)
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


def _fetch_by_id(collection, chunk_id: str) -> dict | None:
    raw = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not raw["ids"]:
        return None
    return {
        "id": raw["ids"][0],
        "content": raw["documents"][0],
        "metadata": raw["metadatas"][0],
    }


def get_thread_ancestors(collection, start_meta: dict, k: int) -> list[dict]:
    full_chain: list[dict] = []
    current_meta = start_meta
    hops = 0

    while hops < MAX_ROOT_WALK:
        parent_id = current_meta.get("immediate_parent_id")
        if not parent_id:
            break
        parent = _fetch_by_id(collection, parent_id)
        if parent is None:
            break
        full_chain.append(parent)
        current_meta = parent["metadata"]
        hops += 1

    if not full_chain:
        return []

    full_chain.reverse()  # root first, nearest parent last
    nearest = full_chain[-k:]
    root = full_chain[0]
    nearest_ids = {a["id"] for a in nearest}
    return nearest if root["id"] in nearest_ids else [root] + nearest


def build_context(collection, top_results) -> str:
    blocks = []
    for doc, _score in top_results:
        meta = doc.metadata
        if meta.get("source_type") != "post":
            blocks.append(doc.page_content)
            continue

        ancestors = get_thread_ancestors(collection, meta, ANCESTOR_K)
        if not ancestors:
            blocks.append(doc.page_content)
            continue

        thread_parts = [a["content"] for a in ancestors] + [doc.page_content]
        blocks.append("[forum thread]\n" + "\n---\n".join(thread_parts))

    return "\n\n---\n\n".join(blocks)


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
                "Context blocks come from two kinds of sources: plain documents, and "
                "forum threads. Forum thread blocks are marked '[forum thread]' and "
                "contain a chain of messages from earliest ancestor down to the most "
                "relevant reply - read them as a conversation, not isolated facts.\n\n"
                f"Context:\n{context}"
            ),
        },
        {
            "role": "assistant",
            "content": "Understood. I will use the provided context when relevant, and rely on my own knowledge otherwise, letting you know which I'm doing.",
        },
    ]
