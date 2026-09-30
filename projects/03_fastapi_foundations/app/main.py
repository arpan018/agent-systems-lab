# FastAPI app object. uvicorn loads app.main:app from this package.
# Routes live on the router so this file stays the composition root.

from fastapi import FastAPI

from app.routes import router


# Build the application and attach the health and echo routes.
def create_app() -> FastAPI:
    application = FastAPI(
        title="FastAPI Foundations",
        description="Stage 3 local JSON API. No OpenAI calls.",
    )
    application.include_router(router)
    return application


app = create_app()
