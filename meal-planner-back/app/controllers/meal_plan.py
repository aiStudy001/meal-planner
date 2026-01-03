"""
식단 계획 API 컨트롤러

SSE 스트리밍 엔드포인트 + Health Check
"""

import asyncio
from hashlib import sha256
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.models.requests import MealPlanRequest
from app.models.responses import HealthCheckResponse
from app.services.stream_service import stream_meal_plan
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["meal-plan"])

# EC-029: Request deduplication state
active_requests = {}  # request_key -> asyncio.Task
request_locks = {}  # request_key -> asyncio.Lock


def get_request_key(request: MealPlanRequest) -> str:
    """요청 고유 키 생성 (프로필 필드 기반 해시)
    
    동일한 프로필로 중복 요청을 방지하기 위한 고유 키 생성
    """
    # 프로필 주요 필드로 해시 생성
    key_data = f"{request.goal}|{request.weight}|{request.height}|{request.age}|{request.gender}|{request.activity_level}|{request.budget}|{request.budget_type}|{request.meals_per_day}|{request.days}"
    key_hash = sha256(key_data.encode()).hexdigest()[:16]
    return key_hash


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    헬스 체크 엔드포인트

    서버가 정상 작동 중인지 확인
    """
    logger.info("health_check_requested")
    return HealthCheckResponse(status="ok", version="1.0.0")


@router.post("/generate")
async def generate_meal_plan(request: MealPlanRequest):
    """
    7일 식단 생성 (SSE 스트리밍)

    Args:
        request: 식단 계획 요청

    Returns:
        SSE 스트림 (text/event-stream)

    SSE 이벤트 타입:
        - progress: 노드 진행 상태
        - validation: 검증 결과
        - retry: 재시도
        - meal_complete: 끼니 완료
        - complete: 전체 완료 (7일 식단)
        - error: 에러 발생
    """
    logger.info("generate_request_received", request=request.model_dump())

    # EC-029: Request deduplication check
    request_key = get_request_key(request)

    # 이미 진행 중인 동일 요청 확인
    if request_key in active_requests:
        logger.warning(
            "duplicate_request_rejected",
            request_key=request_key,
            profile_summary=f"{request.goal}|{request.weight}kg|{request.age}세"
        )
        return JSONResponse(
            status_code=409,
            content={
                "error": "동일한 프로필로 이미 식단 생성이 진행 중입니다. 잠시 후 다시 시도해주세요.",
                "request_key": request_key
            }
        )

    # Lock 초기화 (없으면 생성)
    if request_key not in request_locks:
        request_locks[request_key] = asyncio.Lock()

    async with request_locks[request_key]:
        try:
            # 요청 시작 마킹
            current_task = asyncio.current_task()
            active_requests[request_key] = current_task

            logger.info("request_started", request_key=request_key)

            # SSE 스트림 반환
            async def wrapped_stream():
                """스트림 종료 시 자동으로 active_requests 정리"""
                try:
                    async for chunk in stream_meal_plan(request):
                        yield chunk
                finally:
                    # 완료 시 active_requests에서 제거
                    if request_key in active_requests:
                        del active_requests[request_key]
                    logger.info("request_completed", request_key=request_key)

            return StreamingResponse(
                wrapped_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Nginx 버퍼링 방지
                },
            )

        except Exception as e:
            # 에러 발생 시에도 active_requests 정리
            if request_key in active_requests:
                del active_requests[request_key]

            logger.error("generate_request_failed", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
