from contextlib import asynccontextmanager
from typing import AsyncIterator
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_tarot_reader_backend.api.routes.cards import router as cards_router
from ai_tarot_reader_backend.api.routes.sessions import router as sessions_router
from ai_tarot_reader_backend.api.routes.streaming import router as streaming_router
from ai_tarot_reader_backend.api.routes.user import router as user_router
from ai_tarot_reader_backend.core.errors import ErrorResponse, BaseAppError
from ai_tarot_reader_backend.core.database import DatabaseConnection, init_db_connection
from ai_tarot_reader_backend.configs import set_config, get_config, PathSettings, Config

SERVICE_NAME = "OAPI_TARO_BACKEND/001.00"


async def __init_db_connection(config: Config) -> DatabaseConnection:
    db_connection = init_db_connection(config.postgres)
    await db_connection.check_connection()
    await db_connection.init_schema()
    return db_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config: Config = get_config()
    db_connection: DatabaseConnection = await __init_db_connection(config)
    app.state.db_connection = db_connection

    yield

    await app.state.db_connection.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Tarot Reader API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions_router)
    app.include_router(streaming_router)
    app.include_router(cards_router)
    app.include_router(user_router)

    @app.exception_handler(BaseAppError)
    async def app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                service_name=SERVICE_NAME,
                error_code=exc.error_code,
                user_message=exc.user_message,
                developer_message=exc.developer_message,
            ).model_dump(by_alias=True),
        )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()

if __name__ == "__main__":
    app_dir = Path(__file__).parent.parent

    path_settings = PathSettings(
        yaml_path=str(app_dir / "config.yml"),
        env_path=str(app_dir / ".env.local"),
    )
    set_config(path_settings)
    uvicorn.run(app, host="0.0.0.0", port=8000)