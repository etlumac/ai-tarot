from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_tarot_reader_backend.api.routes.cards import router as cards_router
from ai_tarot_reader_backend.api.routes.sessions import router as sessions_router
from ai_tarot_reader_backend.api.routes.streaming import router as streaming_router
from ai_tarot_reader_backend.api.routes.user import router as user_router
from ai_tarot_reader_backend.core.errors import ErrorResponse, BaseAppError, ValidationError
from ai_tarot_reader_backend.core.database import DatabaseConnection, init_db_connection
from ai_tarot_reader_backend.configs import set_config, get_config, PathSettings, Config
from ai_tarot_reader_backend.db import load_models

SERVICE_NAME = "OAPI_TARO_BACKEND/001.00"

_app_dir = Path(__file__).parent.parent
set_config(PathSettings(
    yaml_path=str(_app_dir / "config.yml"),
    env_path=str(_app_dir / ".env.local"),
))


async def __init_db_connection(config: Config) -> DatabaseConnection:
    db_connection = init_db_connection(config.postgres)
    await db_connection.check_connection()
    load_models()
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

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        dev_msg = "; ".join(
            f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        custom_exc = ValidationError(
            user_message="Invalid request format",
            developer_message=dev_msg,
        )
        return await app_error_handler(request, custom_exc)

    @app.exception_handler(Exception)
    async def unknown_error_handler(request: Request, exc: Exception) -> JSONResponse:
        custom_exc = BaseAppError(
            user_message="Unknown error",
            developer_message=str(exc),
        )
        return await app_error_handler(request, custom_exc)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)