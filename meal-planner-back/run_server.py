"""
FastAPI 서버 실행기

uvicorn으로 서버 실행
"""

import uvicorn
from app.config import settings


def main():
    """서버 실행"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )


if __name__ == "__main__":
    main()
