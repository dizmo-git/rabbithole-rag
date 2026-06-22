from fastapi import APIRouter
from backend.chroma import get_vector_store
from backend.chroma import model
from ollama import ChatResponse
from ollama import chat

router = APIRouter(prefix="/query")


@router.get("/")
async def ask(question: str, notebook: str):
    collection = await get_vector_store(notebook)
    results = collection.similarity_search_with_relevance_scores(question, k=3)

    for i in range(len(results)):
        print(f"Similarity for chunk {i}:\t{results[i][1]}")

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    # hard coded for now
    response: ChatResponse = chat(
        model=model,
        messages=[{"role": "user", "content": f"{question}\n\n\n{context_text}"}],
    )

    return {"answer": response.message.content}
