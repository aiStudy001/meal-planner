"""LangGraph State 스키마 정의"""
from typing import Literal, TypedDict, Annotated, Optional
from operator import add
from pydantic import BaseModel, Field


# ============================================================================
# Custom Reducers (메모리 관리)
# ============================================================================

def limit_validation_results(
    existing: list["ValidationResult"],
    new: list["ValidationResult"]
) -> list["ValidationResult"]:
    """Validation results reducer with max size limit

    최근 검증 결과만 유지하여 메모리 누수 방지
    """
    MAX_VALIDATION_HISTORY = 10
    combined = existing + new
    if len(combined) > MAX_VALIDATION_HISTORY:
        return combined[-MAX_VALIDATION_HISTORY:]
    return combined


def limit_events(
    existing: list[dict],
    new: list[dict]
) -> list[dict]:
    """Events reducer with max size limit

    SSE 스트리밍 후 이벤트 정리
    """
    MAX_EVENT_HISTORY = 20
    combined = existing + new
    if len(combined) > MAX_EVENT_HISTORY:
        return combined[-MAX_EVENT_HISTORY:]
    return combined


# ============================================================================
# Pydantic 모델 (데이터 검증용)
# ============================================================================

class UserProfile(BaseModel):
    """사용자 프로필"""
    goal: Literal["다이어트", "벌크업", "유지", "질병관리"]
    weight: float = Field(gt=0, description="체중 (kg)")
    height: float = Field(gt=0, description="키 (cm)")
    age: int = Field(gt=0, description="나이")
    gender: Literal["male", "female"]
    activity_level: Literal["low", "moderate", "high", "very_high"]
    restrictions: list[str] = Field(default_factory=list, description="알레르기 + 식이선호")
    health_conditions: list[str] = Field(default_factory=list, description="당뇨, 고혈압, 고지혈증")
    calorie_adjustment: int | None = Field(default=None, description="사용자 지정 조정값")
    budget: int = Field(gt=0, description="예산 (원)")
    budget_type: Literal["weekly", "daily", "per_meal"]
    budget_distribution: Literal["equal", "weighted"] = Field(default="equal", description="예산 배분 방식")
    cooking_time: Literal["15분 이내", "30분 이내", "제한 없음"]
    skill_level: Literal["초급", "중급", "고급"]
    meals_per_day: int = Field(ge=1, le=4, description="하루 끼니 수")
    days: int = Field(ge=1, le=7, description="식단 기간")


class MacroTargets(BaseModel):
    """매크로 영양소 목표"""
    calories: float
    carb_g: float
    protein_g: float
    fat_g: float
    carb_ratio: int  # 50
    protein_ratio: int  # 30
    fat_ratio: int  # 20


class MealRecommendation(BaseModel):
    """전문가 추천 메뉴"""
    menu_name: str
    ingredients: list[dict]  # [{"name": "닭가슴살", "amount": "150g"}]
    estimated_calories: float
    estimated_cost: int
    cooking_time_minutes: int
    reasoning: str
    ingredient_prices: list[dict] | None = Field(default=None, description="Tavily 가격 검색 결과")
    recipe_url: Optional[str] = None


class Menu(BaseModel):
    """최종 결정된 메뉴"""
    meal_type: Literal["아침", "점심", "저녁", "간식"]
    menu_name: str
    ingredients: list[dict]
    calories: float
    carb_g: float
    protein_g: float
    fat_g: float
    sodium_mg: float
    sugar_g: float
    cooking_time_minutes: int
    estimated_cost: int
    recipe_steps: list[str]
    recipe_url: Optional[str] = None
    validation_warnings: list[str] = Field(default_factory=list, description="검증 실패 경고 메시지")


class ValidationResult(BaseModel):
    """검증 결과"""
    validator: str  # "nutrition_checker", "allergy_checker", "time_checker"
    passed: bool
    issues: list[str] = Field(default_factory=list, description="검증 실패 상세 내용")
    reason: str | None = None
    details: dict | None = None


class DailyPlan(BaseModel):
    """하루 식단 계획 (상세 필드)"""
    day: int
    meals: list[Menu]
    total_calories: float
    total_carb_g: float
    total_protein_g: float
    total_fat_g: float
    total_cost: int


class DayMealPlan(BaseModel):
    """하루 식단 계획 (간소화 버전)"""
    day: int
    meals: list[Menu]
    daily_totals: dict


# ============================================================================
# LangGraph State (TypedDict)
# ============================================================================

class MealPlanState(TypedDict):
    """LangGraph State 스키마"""

    # 입력
    profile: UserProfile

    # 계산된 목표
    daily_targets: MacroTargets
    per_meal_targets: MacroTargets  # 끼니당 목표
    per_meal_budget: int  # 끼니당 예산 (균등 배분 시 사용)
    per_meal_budgets: dict[str, int] | None  # 끼니별 예산 (차등 배분 시 사용)

    # 현재 진행
    current_day: int
    current_meal_type: Literal["아침", "점심", "저녁", "간식"]
    current_meal_index: int  # 0부터 시작

    # 전문가 추천 (병렬 실행 결과)
    nutritionist_recommendation: MealRecommendation | None
    chef_recommendation: MealRecommendation | None
    budget_recommendation: MealRecommendation | None

    # 통합된 현재 메뉴
    current_menu: Menu | None

    # 검증 결과 (병렬 실행 결과) - 최대 10개만 유지
    validation_results: Annotated[list[ValidationResult], limit_validation_results]

    # 누적 결과
    completed_meals: list[Menu]
    weekly_plan: list[DailyPlan]  # DayMealPlan → DailyPlan

    # 제어
    retry_count: int
    max_retries: int  # 5
    error_message: str | None

    # 스트리밍용 이벤트 (SSE 통합용) - 최대 20개만 유지
    events: Annotated[list[dict], limit_events]

    # Validation feedback for retry
    previous_validation_failures: Annotated[list[dict], add]  # [{"validator": str, "issues": list, "retry_count": int, "menu_name": str}]
