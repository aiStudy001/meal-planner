"""
API 요청 모델

MealPlanRequest는 meal-planner-info.md 섹션 7.2의 명세를 따름
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, List, Optional
from app.utils.prompt_safety import sanitize_string_list
from app.models.state import UserProfile


class MealPlanRequest(BaseModel):
    """식단 생성 요청 모델"""

    # 기본 정보
    goal: Literal["다이어트", "벌크업", "유지", "질병관리"]
    weight: float = Field(gt=0, le=300, description="체중 (kg)")
    height: float = Field(gt=50, le=250, description="키 (cm)")
    age: int = Field(gt=0, le=150, description="나이")
    gender: Literal["male", "female"]

    # 활동 수준
    activity_level: Literal["low", "moderate", "high", "very_high"]

    # 제약 사항
    restrictions: List[str] = Field(default_factory=list, description="알레르기 + 식이선호")
    health_conditions: List[str] = Field(
        default_factory=list, description="건강 상태 (당뇨, 고혈압, 고지혈증)"
    )

    # 칼로리/매크로
    calorie_adjustment: Optional[int] = Field(
        default=None, description="칼로리 조정값 (선택사항)"
    )
    macro_ratio: Optional[dict] = Field(
        default=None, description="매크로 비율 (선택사항)"
    )

    # 예산
    budget: int = Field(ge=10_000, le=1_000_000, description="예산 (원)")
    budget_type: Literal["weekly", "daily", "per_meal"] = Field(
        default="weekly", description="예산 타입"
    )
    budget_distribution: Literal["equal", "weighted"] = Field(
        default="equal", description="예산 배분 방식"
    )

    # 조리
    cooking_time: Literal["15분 이내", "30분 이내", "제한 없음"]
    skill_level: Literal["초급", "중급", "고급"]

    # 식단 설정
    meals_per_day: int = Field(ge=1, le=4, description="하루 끼니 수")
    days: int = Field(ge=1, le=7, description="계획 일수")

    @model_validator(mode='after')
    def validate_realistic_budget(self):
        """예산이 현실적인지 검증 (끼니당 최소 2,000원)"""
        # 모든 필드가 검증된 후 실행되므로 직접 접근 가능
        budget = self.budget
        budget_type = self.budget_type
        meals_per_day = self.meals_per_day
        days = self.days

        # 끼니당 예산 계산
        if budget_type == "weekly":
            total_meals = meals_per_day * days
            per_meal_budget = budget / total_meals
        elif budget_type == "daily":
            per_meal_budget = budget / meals_per_day
        elif budget_type == "per_meal":
            per_meal_budget = budget
        else:
            per_meal_budget = budget / (meals_per_day * days)  # fallback

        # 끼니당 최소 2,000원 검증
        MIN_PER_MEAL_BUDGET = 2_000
        if per_meal_budget < MIN_PER_MEAL_BUDGET:
            raise ValueError(
                f"끼니당 예산이 너무 낮습니다. "
                f"현재: {per_meal_budget:,.0f}원/끼니, "
                f"최소 요구: {MIN_PER_MEAL_BUDGET:,}원/끼니 "
                f"(예산 타입: {budget_type}, 하루 {meals_per_day}끼, {days}일)"
            )

        return self

    @field_validator("restrictions")
    @classmethod
    def sanitize_restrictions(cls, v):
        """알레르기/식이선호 입력 sanitization (prompt injection 방지)"""
        if not v:
            return v
        return sanitize_string_list(v, "알레르기/식이선호")

    @field_validator("health_conditions")
    @classmethod
    def sanitize_health_conditions(cls, v):
        """건강 상태 입력 sanitization (prompt injection 방지)"""
        if not v:
            return v
        return sanitize_string_list(v, "건강 상태")

    class Config:
        json_schema_extra = {
            "example": {
                "goal": "다이어트",
                "weight": 70,
                "height": 175,
                "age": 30,
                "gender": "male",
                "activity_level": "moderate",
                "restrictions": ["우유", "땅콩"],
                "health_conditions": [],
                "calorie_adjustment": -500,
                "budget": 100000,
                "budget_type": "weekly",
                "budget_distribution": "equal",
                "cooking_time": "30분 이내",
                "skill_level": "중급",
                "meals_per_day": 3,
                "days": 7,
            }
        }


class RegenerateMealRequest(BaseModel):
    """특정 끼니 재생성 요청 모델"""

    # 사용자 프로필 (전체 컨텍스트)
    profile: UserProfile

    # 재생성 대상
    target_day: int = Field(ge=1, le=7, description="재생성할 일자 (1-7)")
    target_meal_type: Literal["아침", "점심", "저녁", "간식"] = Field(
        description="재생성할 끼니 타입"
    )

    # 영양 및 예산 목표
    daily_nutrition_targets: dict = Field(
        description="일일 영양 목표 (calories, carb_g, protein_g, fat_g)"
    )
    per_meal_budget: int = Field(
        gt=0, description="이 끼니에 할당된 예산 (원)"
    )

    # 기존 식단 컨텍스트 (다른 끼니들)
    completed_meals_context: List[dict] = Field(
        default_factory=list,
        description="이미 생성된 다른 끼니 정보 (영양 균형 유지용)"
    )

    # 중복 방지 및 다양성
    recently_used_recipes: List[str] = Field(
        default_factory=list,
        description="최근 사용된 레시피 이름 목록 (중복 방지)"
    )
    used_ingredients: List[str] = Field(
        default_factory=list,
        description="최근 사용된 주재료 목록 (다양성 확보)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "goal": "다이어트",
                    "weight": 70,
                    "height": 175,
                    "age": 30,
                    "gender": "male",
                    "activity_level": "moderate",
                    "restrictions": [],
                    "health_conditions": [],
                    "budget": 100000,
                    "budget_type": "weekly",
                    "budget_distribution": "equal",
                    "cooking_time": "30분 이내",
                    "skill_level": "중급",
                    "meals_per_day": 3,
                    "days": 3
                },
                "target_day": 2,
                "target_meal_type": "아침",
                "daily_nutrition_targets": {
                    "calories": 1800,
                    "carb_g": 225,
                    "protein_g": 135,
                    "fat_g": 40
                },
                "per_meal_budget": 7000,
                "completed_meals_context": [
                    {
                        "day": 1,
                        "meal_type": "아침",
                        "menu_name": "닭가슴살 샐러드",
                        "calories": 500
                    }
                ],
                "recently_used_recipes": [
                    "닭가슴살 샐러드",
                    "연어 구이"
                ],
                "used_ingredients": [
                    "닭가슴살",
                    "연어",
                    "토마토"
                ]
            }
        }
