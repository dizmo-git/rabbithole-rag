from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.db_seed import seed
from backend.routers import notebooks, query, sources

origins = ["http://localhost", "http://localhost:5173"]
doSeed = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Rabbithole - Startup")

    # Seeding
    if doSeed:
        await seed()

    yield

    print("Rabbithole - Cleanup")


app = FastAPI(title="Rabbithole RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=notebooks.router)
app.include_router(router=query.router)
app.include_router(router=sources.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
