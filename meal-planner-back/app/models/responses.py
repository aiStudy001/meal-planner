"""
API 응답 모델

SSE 이벤트 타입은 meal-planner-info.md 섹션 7.3의 명세를 따름
"""

from pydantic import BaseModel
from typing import Literal, Optional, Any, List


class SSEEvent(BaseModel):
    """SSE 이벤트 기본 구조"""

    type: Literal["progress", "validation", "retry", "meal_complete", "complete", "error"]
    data: dict


class ProgressEvent(BaseModel):
    """진행 상태 이벤트"""

    type: Literal["progress"] = "progress"
    data: dict  # {"node": str, "status": str, "message": Any}


class ValidationEvent(BaseModel):
    """검증 결과 이벤트"""

    type: Literal["validation"] = "validation"
    data: dict  # {"validator": str, "passed": bool, "reason": Optional[str]}


class RetryEvent(BaseModel):
    """재시도 이벤트"""

    type: Literal["retry"] = "retry"
    data: dict  # {"attempt": int, "reason": str}


class MealCompleteEvent(BaseModel):
    """끼니 완료 이벤트"""

    type: Literal["meal_complete"] = "meal_complete"
    data: dict  # {"day": int, "meal": str, "menu": dict}


class CompleteEvent(BaseModel):
    """전체 완료 이벤트"""

    type: Literal["complete"] = "complete"
    data: dict  # {"result": List[dict]}


class ErrorEvent(BaseModel):
    """에러 이벤트"""

    type: Literal["error"] = "error"
    data: dict  # {"message": str, "code": str}


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""

    status: str = "ok"
    version: str = "1.0.0"
