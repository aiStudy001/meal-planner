"""
FastAPI 애플리케이션 팩토리

SSE를 통한 실시간 식단 계획 생성 API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.controllers import meal_plan
from app.utils.logging import setup_logging, get_logger

# 로깅 설정
setup_logging(settings.DEBUG and "DEBUG" or "INFO")
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    FastAPI 앱 생성 및 설정

    Returns:
        FastAPI 앱 인스턴스
    """
    app = FastAPI(
        title="AI Meal Planner API",
        description="AI 에이전트 기반 개인 맞춤형 7일 식단 계획 생성 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # 라우터 등록
    app.include_router(meal_plan.router)

    # Startup 이벤트
    @app.on_event("startup")
    async def startup_event():
        logger.info(
            "server_starting",
            host=settings.HOST,
            port=settings.PORT,
            debug=settings.DEBUG,
            mock_mode=settings.MOCK_MODE,
        )

    # Shutdown 이벤트
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("server_shutting_down")

    return app


# 앱 인스턴스
app = create_app()


# Root 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "AI Meal Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
