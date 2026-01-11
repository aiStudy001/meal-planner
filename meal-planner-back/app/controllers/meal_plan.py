"""
식단 계획 API 컨트롤러

SSE 스트리밍 엔드포인트 + Health Check
"""

import asyncio
from hashlib import sha256
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.models.requests import MealPlanRequest, RegenerateMealRequest
from app.models.responses import HealthCheckResponse
from app.services.stream_service import stream_meal_plan, stream_meal_regeneration
from app.services.regeneration_service import build_regeneration_state
from app.services.recipe_search_service import get_alternative_recipe_service
from app.services.csv_recipe_search_service import get_csv_recipe_service
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


@router.post("/regenerate-meal")
async def regenerate_meal(request: RegenerateMealRequest):
    """
    특정 끼니 재생성 (SSE 스트리밍)

    Args:
        request: 끼니 재생성 요청

    Returns:
        SSE 스트림 (text/event-stream)

    SSE 이벤트 타입:
        - meal_regenerate_progress: 재생성 진행 상태
        - validation: 검증 결과
        - retry: 재시도
        - meal_regenerate_complete: 재생성 완료
        - error: 에러 발생
    """
    logger.info(
        "regenerate_request_received",
        target_day=request.target_day,
        target_meal_type=request.target_meal_type
    )

    try:
        # 1. 재생성용 초기 상태 생성
        initial_state = build_regeneration_state(request)

        # 2. SSE 스트림 반환
        return StreamingResponse(
            stream_meal_regeneration(initial_state),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("regenerate_request_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alternative-recipes")
async def get_alternative_recipes(
    current_menu: str,
    target_calories: int,
    target_cost: int,
    calorie_tolerance: int = 50,
    cost_tolerance: int = 1000,
    restrictions: str = "",
    exclude_recipes: str = "",
    target_carb_g: float = None,
    target_protein_g: float = None,
    target_fat_g: float = None
):
    """
    대체 레시피 검색

    Args:
        current_menu: 현재 메뉴 이름
        target_calories: 목표 칼로리
        target_cost: 목표 비용
        calorie_tolerance: 칼로리 허용 범위 (default: ±50kcal)
        cost_tolerance: 비용 허용 범위 (default: ±1000원)
        restrictions: 제외 재료 (쉼표 구분, 예: "견과류,우유")
        exclude_recipes: 제외 레시피 (쉼표 구분, 예: "연어구이,돼지고기볶음")
        target_carb_g: 목표 탄수화물(g) - 선택사항
        target_protein_g: 목표 단백질(g) - 선택사항
        target_fat_g: 목표 지방(g) - 선택사항

    Returns:
        JSON: {"alternatives": [Recipe, Recipe, Recipe]}
    """
    logger.info(
        "alternative_recipes_request",
        current_menu=current_menu,
        target_calories=target_calories,
        target_cost=target_cost
    )

    try:
        # 쉼표로 구분된 문자열 → 리스트 변환
        restrictions_list = [r.strip() for r in restrictions.split(",") if r.strip()]
        exclude_list = [e.strip() for e in exclude_recipes.split(",") if e.strip()]

        # 대체 레시피 검색 서비스 가져오기 (CSV 기반)
        search_service = get_csv_recipe_service()

        # 대체 레시피 검색 (상위 3개)
        alternatives = await search_service.search_alternative_recipes(
            current_menu_name=current_menu,
            target_calories=target_calories,
            target_cost=target_cost,
            calorie_tolerance=calorie_tolerance,
            cost_tolerance=cost_tolerance,
            restrictions=restrictions_list,
            exclude_recipes=exclude_list,
            target_carb_g=target_carb_g,
            target_protein_g=target_protein_g,
            target_fat_g=target_fat_g
        )

        logger.info(
            "alternative_recipes_found",
            current_menu=current_menu,
            alternatives_count=len(alternatives)
        )

        return JSONResponse(
            content={"alternatives": alternatives}
        )

    except Exception as e:
        logger.error("alternative_recipes_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
