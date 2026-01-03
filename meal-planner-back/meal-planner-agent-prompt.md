## Claude Code용 에이전트 개발 프롬프트



```markdown
# LangGraph 멀티 에이전트 식단 플래너 개발 요청

## 목표
개인 맞춤형 7일 식단을 생성하는 LangGraph 기반 멀티 에이전트 시스템을 개발해줘.
3명의 전문가 에이전트가 병렬로 협업하고, 검증 파이프라인을 거쳐 자동 재시도하는 구조야.

---

## 기술 스택

- Python 3.13+
- LangGraph (langgraph)
- LangChain (langchain-anthropic)
- Claude 3.5 Haiku (claude-3-5-haiku-latest)
- Pydantic v2
- FastAPI (SSE 스트리밍)

---

## 프로젝트 구조
```

# LangGraph 멀티 에이전트 식단 플래너 개발 요청

## 목표

개인 맞춤형 7일 식단을 생성하는 LangGraph 기반 멀티 에이전트 시스템을 개발해줘.
3명의 전문가 에이전트가 병렬로 협업하고, 검증 파이프라인을 거쳐 자동 재시도하는 구조야.

---

## 기술 스택

- Python 3.13+
- LangGraph (langgraph)
- LangChain (langchain-anthropic)
- Claude 3.5 Haiku (claude-3-5-haiku-latest)
- Pydantic v2
- FastAPI (SSE 스트리밍)

---

## 프로젝트 구조

```
meal-planner-backend/
├── app/
│ ├── **init**.py
│ ├── main.py # FastAPI 앱
│ ├── config.py # 환경 설정
│ ├── models/
│ │ ├── **init**.py
│ │ ├── state.py # LangGraph State 정의
│ │ ├── requests.py # API 요청 스키마
│ │ └── responses.py # API 응답 스키마
│ ├── agents/
│ │ ├── **init**.py
│ │ ├── graph.py # 메인 그래프 정의
│ │ └── nodes/
│ │ ├── **init**.py
│ │ ├── nutrition_calculator.py
│ │ ├── meal_planning/
│ │ │ ├── **init**.py
│ │ │ ├── supervisor.py
│ │ │ ├── nutritionist.py
│ │ │ ├── chef.py
│ │ │ ├── budget.py
│ │ │ └── conflict_resolver.py
│ │ ├── validation/
│ │ │ ├── **init**.py
│ │ │ ├── supervisor.py
│ │ │ ├── nutrition_checker.py
│ │ │ ├── allergy_checker.py
│ │ │ └── time_checker.py
│ │ └── decision_maker.py
│ ├── services/
│ │ ├── **init**.py
│ │ └── llm_service.py # Claude API 래퍼
│ └── utils/
│ ├── **init**.py
│ ├── constants.py # 상수 정의
│ └── nutrition.py # BMR/TDEE 계산
├── tests/
│ ├── test_graph.py
│ └── test_nodes.py
├── .env.example
├── requirements.txt
└── pyproject.toml
```

## 그래프 아키텍처

```
**start** │
▼
nutrition_calculator
│
▼
meal_planning_subgraph ─────────────────────────────┐
│ │
├──► nutritionist ──┐ │
├──► chef ──────────┼──► conflict_resolver │ (병렬 실행)
└──► budget ────────┘ │
│
▼◄──────────────────────────────────────────────┘
validation_subgraph ────────────────────────────────┐
│ │
├──► nutrition_checker ──┐ │
├──► allergy_checker ────┼──► aggregator │ (병렬 실행)
└──► time_checker ───────┘ │
│
▼◄──────────────────────────────────────────────┘
decision_maker
│
├── 통과 ──► 다음 끼니 (또는 완료)
│
└── 실패 ──► retry_count < 5 ? meal_planning_subgraph : 에러
```




---

## State 스키마

```python
from typing import TypedDict, Literal, Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages 
class UserProfile(BaseModel):
 goal: Literal["다이어트", "벌크업", "유지", "질병관리"]
 weight: float # kg
 height: float # cm
 age: int
 gender: Literal["male", "female"]
 activity_level: Literal["low", "moderate", "high", "very_high"]
 restrictions: list[str] # 알레르기 + 식이선호
 health_conditions: list[str] # ["당뇨", "고혈압", "고지혈증"]
 calorie_adjustment: int | None # 사용자 지정 조정값
 budget: int # 원
 budget_type: Literal["weekly", "daily", "per_meal"]
 cooking_time: Literal["15분 이내", "30분 이내", "제한 없음"]
 skill_level: Literal["초급", "중급", "고급"]
 meals_per_day: int # 1-4
 days: int # 1-7 
class MacroTargets(BaseModel):
 calories: float
 carb_g: float
 protein_g: float
 fat_g: float
 carb_ratio: int # 50
 protein_ratio: int # 30
 fat_ratio: int # 20 
class MealRecommendation(BaseModel):
 menu_name: str
 ingredients: list[dict] # [{"name": "닭가슴살", "amount": "150g"}]
 estimated_calories: float
 estimated_cost: int
 cooking_time_minutes: int
 reasoning: str 
class Menu(BaseModel):
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
class ValidationResult(BaseModel):
 validator: str
 passed: bool
 reason: str | None = None
 details: dict | None = None 
class DayMealPlan(BaseModel):
 day: int
 meals: list[Menu]
 daily_totals: dict 
class MealPlanState(TypedDict):
 # 입력
 profile: UserProfile 
# 계산된 목표
 daily_targets: MacroTargets
 per_meal_targets: MacroTargets # 끼니당 목표
 per_meal_budget: int # 끼니당 예산 
# 현재 진행
 current_day: int
 current_meal_type: Literal["아침", "점심", "저녁", "간식"]
 current_meal_index: int # 0부터 시작 
# 전문가 추천 (병렬 실행 결과)
 nutritionist_recommendation: MealRecommendation | None
 chef_recommendation: MealRecommendation | None
 budget_recommendation: MealRecommendation | None 
# 통합된 현재 메뉴
 current_menu: Menu | None 
# 검증 결과 (병렬 실행 결과)
 validation_results: list[ValidationResult] 
# 누적 결과
 completed_meals: list[Menu]
 weekly_plan: list[DayMealPlan] 
# 제어
 retry_count: int
 max_retries: int # 5
 error_message: str | None 
# 스트리밍용 이벤트
 events: Annotated[list[dict], add_messages]
```






---

## 상수 정의 (constants.py)

```python
# 활동 계수
ACTIVITY_MULTIPLIERS = {
    "low": 1.2,
    "moderate": 1.375,
    "high": 1.55,
    "very_high": 1.725,
}

# 목표별 칼로리 조정
CALORIE_ADJUSTMENTS = {
    "다이어트": -500,
    "벌크업": +500,
    "유지": 0,
    "질병관리": 0,  # LLM이 판단
}

# 목표별 매크로 비율 (탄:단:지)
MACRO_RATIOS = {
    "다이어트": {"carb": 50, "protein": 30, "fat": 20},
    "벌크업": {"carb": 40, "protein": 40, "fat": 20},
    "유지": {"carb": 55, "protein": 20, "fat": 25},
    "당뇨": {"carb": 45, "protein": 25, "fat": 30},
    "고혈압": {"carb": 55, "protein": 20, "fat": 25},
    "고지혈증": {"carb": 55, "protein": 25, "fat": 20},
}

# 질병별 제한
HEALTH_CONSTRAINTS = {
    "당뇨": {
        "max_sugar_g": 25,
        "prefer_low_gi": True,
    },
    "고혈압": {
        "max_sodium_mg": 2000,
        "prefer_high_potassium": True,
    },
    "고지혈증": {
        "max_saturated_fat_g": 15,
        "max_cholesterol_mg": 300,
    },
}

# 조리시간 제한 (분)
COOKING_TIME_LIMITS = {
    "15분 이내": 15,
    "30분 이내": 30,
    "제한 없음": 180,
}

# 검증 허용 범위
VALIDATION_TOLERANCE = 0.20  # ±20%

# 재시도 설정
MAX_RETRIES = 5

# 끼니 타입
MEAL_TYPES = ["아침", "점심", "저녁", "간식"]

# 알레르기 목록 (식약처 22종)
ALLERGENS = [
    "알류(계란)", "우유", "메밀", "땅콩", "대두", "밀",
    "고등어", "게", "새우", "돼지고기", "복숭아", "토마토",
    "아황산류", "호두", "닭고기", "쇠고기", "오징어",
    "조개류", "잣", "오리고기", "토끼고기", "아몬드",
]

# 식이 선호
DIETARY_PREFERENCES = [
    "채식(락토오보)", "비건", "페스코",
    "저염식", "저당식", "저지방", "글루텐프리",
]
```

---

## 유틸리티 함수 (nutrition.py)

```python
def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor 공식으로 BMR 계산"""
    if gender == "male":
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        return (10 * weight) + (6.25 * height) - (5 * age) - 161

def calculate_tdee(bmr: float, activity_level: str) -> float:
    """TDEE 계산"""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier

def calculate_daily_targets(profile: UserProfile) -> MacroTargets:
    """일일 영양 목표 계산"""
    bmr = calculate_bmr(profile.weight, profile.height, profile.age, profile.gender)
    tdee = calculate_tdee(bmr, profile.activity_level)

    # 칼로리 조정
    adjustment = profile.calorie_adjustment or CALORIE_ADJUSTMENTS.get(profile.goal, 0)
    daily_calories = tdee + adjustment

    # 매크로 비율 결정
    if profile.health_conditions:
        # 질병이 있으면 가장 엄격한 비율 적용
        ratios = get_strictest_ratios(profile.health_conditions)
    else:
        ratios = MACRO_RATIOS.get(profile.goal, MACRO_RATIOS["유지"])

    return MacroTargets(
        calories=daily_calories,
        carb_g=(daily_calories * ratios["carb"] / 100) / 4,
        protein_g=(daily_calories * ratios["protein"] / 100) / 4,
        fat_g=(daily_calories * ratios["fat"] / 100) / 9,
        carb_ratio=ratios["carb"],
        protein_ratio=ratios["protein"],
        fat_ratio=ratios["fat"],
    )

def calculate_per_meal_targets(daily: MacroTargets, meals_per_day: int) -> MacroTargets:
    """끼니당 영양 목표 계산 (균등 배분)"""
    return MacroTargets(
        calories=daily.calories / meals_per_day,
        carb_g=daily.carb_g / meals_per_day,
        protein_g=daily.protein_g / meals_per_day,
        fat_g=daily.fat_g / meals_per_day,
        carb_ratio=daily.carb_ratio,
        protein_ratio=daily.protein_ratio,
        fat_ratio=daily.fat_ratio,
    )
```

---

## 각 노드 구현

### 1. nutrition_calculator

```python
async def nutrition_calculator(state: MealPlanState) -> dict:
    """BMR/TDEE/매크로 목표 계산"""
    profile = state["profile"]

    daily_targets = calculate_daily_targets(profile)
    per_meal_targets = calculate_per_meal_targets(daily_targets, profile.meals_per_day)

    # 예산 계산
    if profile.budget_type == "weekly":
        total_meals = profile.meals_per_day * profile.days
        per_meal_budget = profile.budget // total_meals
    elif profile.budget_type == "daily":
        per_meal_budget = profile.budget // profile.meals_per_day
    else:
        per_meal_budget = profile.budget

    return {
        "daily_targets": daily_targets,
        "per_meal_targets": per_meal_targets,
        "per_meal_budget": per_meal_budget,
        "current_day": 1,
        "current_meal_index": 0,
        "current_meal_type": MEAL_TYPES[0] if profile.meals_per_day >= 1 else "점심",
        "retry_count": 0,
        "completed_meals": [],
        "weekly_plan": [],
        "events": [{"type": "progress", "node": "nutrition_calculator", "status": "completed"}],
    }
```

### 2. 전문가 에이전트들 (병렬 실행)

**nutritionist.py:**

```python
async def nutritionist_agent(state: MealPlanState) -> dict:
    """영양사 에이전트: 영양 균형 관점에서 메뉴 추천"""
    profile = state["profile"]
    targets = state["per_meal_targets"]

    prompt = f"""당신은 전문 영양사입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 영양 목표 (1끼니 기준)
- 칼로리: {targets.calories:.0f}kcal
- 탄수화물: {targets.carb_g:.0f}g
- 단백질: {targets.protein_g:.0f}g
- 지방: {targets.fat_g:.0f}g

## 제한 사항
- 알레르기/제외 식품: {', '.join(profile.restrictions) or '없음'}
- 건강 상태: {', '.join(profile.health_conditions) or '없음'}

## 추가 고려사항
{"- 당류 25g 이하, 저GI 식품 선호" if "당뇨" in profile.health_conditions else ""}
{"- 나트륨 667mg 이하 (1끼니)" if "고혈압" in profile.health_conditions else ""}
{"- 포화지방 5g 이하 (1끼니)" if "고지혈증" in profile.health_conditions else ""}

영양 균형을 최우선으로 고려하여 메뉴를 추천해주세요.

## 출력 형식 (JSON)
{{
    "menu_name": "메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "estimated_calories": 500,
    "estimated_cost": 5000,
    "cooking_time_minutes": 20,
    "reasoning": "추천 이유"
}}
"""

    response = await llm.ainvoke(prompt)
    recommendation = parse_json_response(response)

    return {
        "nutritionist_recommendation": MealRecommendation(**recommendation),
        "events": [{"type": "progress", "node": "nutritionist", "status": "completed"}],
    }
```

**chef.py:**

```python
async def chef_agent(state: MealPlanState) -> dict:
    """셰프 에이전트: 맛과 조리 용이성 관점에서 메뉴 추천"""
    profile = state["profile"]
    targets = state["per_meal_targets"]
    time_limit = COOKING_TIME_LIMITS[profile.cooking_time]

    prompt = f"""당신은 전문 셰프입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 조리 조건
- 조리 시간: {time_limit}분 이내
- 요리 실력: {profile.skill_level}
- 제외 재료: {', '.join(profile.restrictions) or '없음'}

## 영양 목표 (참고)
- 칼로리: {targets.calories:.0f}kcal
- 단백질: {targets.protein_g:.0f}g

## 요리 실력별 가이드
- 초급: 전자레인지, 끓이기, 간단한 볶음만 가능
- 중급: 볶음, 굽기, 찜 가능
- 고급: 복합 조리, 베이킹, 다양한 기법 가능

맛있고 조리하기 쉬운 메뉴를 추천해주세요.

## 출력 형식 (JSON)
{{
    "menu_name": "메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "estimated_calories": 500,
    "estimated_cost": 5000,
    "cooking_time_minutes": 20,
    "reasoning": "추천 이유"
}}
"""

    response = await llm.ainvoke(prompt)
    recommendation = parse_json_response(response)

    return {
        "chef_recommendation": MealRecommendation(**recommendation),
        "events": [{"type": "progress", "node": "chef", "status": "completed"}],
    }
```

**budget.py:**

```python
async def budget_agent(state: MealPlanState) -> dict:
    """예산 관리 에이전트: 비용 효율 관점에서 메뉴 추천"""
    profile = state["profile"]
    targets = state["per_meal_targets"]
    budget = state["per_meal_budget"]

    prompt = f"""당신은 가계부 전문가이자 요리 연구가입니다.

다음 조건에 맞는 {state["current_meal_type"]} 메뉴 1개를 추천해주세요.

## 예산 조건
- 1끼니 예산: {budget:,}원
- 가성비를 최우선으로 고려

## 영양 목표 (참고)
- 칼로리: {targets.calories:.0f}kcal
- 단백질: {targets.protein_g:.0f}g

## 제한 사항
- 제외 재료: {', '.join(profile.restrictions) or '없음'}

예산 내에서 영양가 있는 메뉴를 추천해주세요.
저렴하면서도 영양가 높은 식재료를 활용하세요.

## 출력 형식 (JSON)
{{
    "menu_name": "메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "estimated_calories": 500,
    "estimated_cost": 5000,
    "cooking_time_minutes": 20,
    "reasoning": "추천 이유 (비용 효율 강조)"
}}
"""

    response = await llm.ainvoke(prompt)
    recommendation = parse_json_response(response)

    return {
        "budget_recommendation": MealRecommendation(**recommendation),
        "events": [{"type": "progress", "node": "budget", "status": "completed"}],
    }
```

### 3. conflict_resolver

```python
async def conflict_resolver(state: MealPlanState) -> dict:
    """3명의 전문가 의견을 통합하여 최종 메뉴 결정"""
    nutritionist = state["nutritionist_recommendation"]
    chef = state["chef_recommendation"]
    budget = state["budget_recommendation"]
    profile = state["profile"]
    targets = state["per_meal_targets"]

    prompt = f"""당신은 식단 기획 총괄 매니저입니다.

3명의 전문가가 각자의 관점에서 메뉴를 추천했습니다.
이를 종합하여 최적의 메뉴 1개를 결정해주세요.

## 전문가 추천

### 영양사 추천
- 메뉴: {nutritionist.menu_name}
- 예상 칼로리: {nutritionist.estimated_calories}kcal
- 예상 비용: {nutritionist.estimated_cost:,}원
- 조리 시간: {nutritionist.cooking_time_minutes}분
- 추천 이유: {nutritionist.reasoning}

### 셰프 추천
- 메뉴: {chef.menu_name}
- 예상 칼로리: {chef.estimated_calories}kcal
- 예상 비용: {chef.estimated_cost:,}원
- 조리 시간: {chef.cooking_time_minutes}분
- 추천 이유: {chef.reasoning}

### 예산 전문가 추천
- 메뉴: {budget.menu_name}
- 예상 칼로리: {budget.estimated_calories}kcal
- 예상 비용: {budget.estimated_cost:,}원
- 조리 시간: {budget.cooking_time_minutes}분
- 추천 이유: {budget.reasoning}

## 결정 기준 (우선순위)
1. 영양 목표 충족 (칼로리 {targets.calories:.0f}kcal ±20%)
2. 알레르기 성분 배제: {', '.join(profile.restrictions) or '없음'}
3. 조리 시간 준수: {profile.cooking_time}
4. 예산 준수: {state["per_meal_budget"]:,}원

위 기준을 모두 만족하는 메뉴를 선택하거나,
전문가들의 의견을 조합한 새로운 메뉴를 제안해주세요.

## 출력 형식 (JSON)
{{
    "menu_name": "최종 메뉴명",
    "ingredients": [{{"name": "재료명", "amount": "100g"}}],
    "calories": 500,
    "carb_g": 60,
    "protein_g": 30,
    "fat_g": 15,
    "sodium_mg": 500,
    "sugar_g": 10,
    "cooking_time_minutes": 20,
    "estimated_cost": 5000,
    "recipe_steps": ["1단계", "2단계", "3단계"]
}}
"""

    response = await llm.ainvoke(prompt)
    menu_data = parse_json_response(response)

    current_menu = Menu(
        meal_type=state["current_meal_type"],
        **menu_data
    )

    return {
        "current_menu": current_menu,
        "events": [{"type": "progress", "node": "conflict_resolver", "status": "completed"}],
    }
```

### 4. 검증 에이전트들 (병렬 실행)

**nutrition_checker.py:**

```python
async def nutrition_checker(state: MealPlanState) -> dict:
    """영양 목표 충족 여부 검증 (±20%)"""
    menu = state["current_menu"]
    targets = state["per_meal_targets"]
    tolerance = VALIDATION_TOLERANCE

    checks = []

    # 칼로리 검증
    cal_min = targets.calories * (1 - tolerance)
    cal_max = targets.calories * (1 + tolerance)
    cal_ok = cal_min <= menu.calories <= cal_max
    checks.append(("칼로리", cal_ok, menu.calories, targets.calories))

    # 단백질 검증
    protein_min = targets.protein_g * (1 - tolerance)
    protein_max = targets.protein_g * (1 + tolerance)
    protein_ok = protein_min <= menu.protein_g <= protein_max
    checks.append(("단백질", protein_ok, menu.protein_g, targets.protein_g))

    all_passed = all(c[1] for c in checks)

    failed_items = [f"{c[0]}: {c[2]:.0f} (목표: {c[3]:.0f})" for c in checks if not c[1]]

    result = ValidationResult(
        validator="nutrition_checker",
        passed=all_passed,
        reason=None if all_passed else f"영양 목표 미충족: {', '.join(failed_items)}",
        details={"checks": checks}
    )

    return {
        "validation_results": [result],
        "events": [{"type": "validation", "validator": "nutrition", "passed": all_passed}],
    }
```

**allergy_checker.py:**

```python
async def allergy_checker(state: MealPlanState) -> dict:
    """알레르기 성분 포함 여부 검증"""
    menu = state["current_menu"]
    restrictions = state["profile"].restrictions

    if not restrictions:
        result = ValidationResult(
            validator="allergy_checker",
            passed=True,
            reason=None
        )
    else:
        # 재료에서 알레르기 성분 검사
        ingredient_names = [ing["name"].lower() for ing in menu.ingredients]
        found_allergens = []

        for restriction in restrictions:
            restriction_lower = restriction.lower()
            for ing_name in ingredient_names:
                if restriction_lower in ing_name or ing_name in restriction_lower:
                    found_allergens.append(f"{ing_name} ({restriction})")

        passed = len(found_allergens) == 0

        result = ValidationResult(
            validator="allergy_checker",
            passed=passed,
            reason=None if passed else f"알레르기 성분 포함: {', '.join(found_allergens)}",
            details={"found_allergens": found_allergens}
        )

    return {
        "validation_results": [result],
        "events": [{"type": "validation", "validator": "allergy", "passed": result.passed}],
    }
```

**time_checker.py:**

```python
async def time_checker(state: MealPlanState) -> dict:
    """조리 시간 제한 준수 검증"""
    menu = state["current_menu"]
    profile = state["profile"]
    time_limit = COOKING_TIME_LIMITS[profile.cooking_time]

    passed = menu.cooking_time_minutes <= time_limit

    result = ValidationResult(
        validator="time_checker",
        passed=passed,
        reason=None if passed else f"조리시간 초과: {menu.cooking_time_minutes}분 > {time_limit}분",
        details={"actual": menu.cooking_time_minutes, "limit": time_limit}
    )

    return {
        "validation_results": [result],
        "events": [{"type": "validation", "validator": "time", "passed": passed}],
    }
```

### 5. decision_maker

```python
async def decision_maker(state: MealPlanState) -> dict:
    """검증 결과를 종합하여 다음 액션 결정"""
    validation_results = state["validation_results"]
    retry_count = state["retry_count"]
    max_retries = state.get("max_retries", MAX_RETRIES)

    all_passed = all(v.passed for v in validation_results)

    if all_passed:
        # 성공: 현재 메뉴를 completed_meals에 추가
        completed_meals = state["completed_meals"] + [state["current_menu"]]

        # 다음 끼니로 이동
        profile = state["profile"]
        current_meal_index = state["current_meal_index"] + 1
        total_meals_per_day = profile.meals_per_day

        if current_meal_index >= total_meals_per_day:
            # 하루 완료, 다음 날로
            current_day = state["current_day"] + 1
            current_meal_index = 0

            # 오늘 식단 저장
            today_meals = completed_meals[-total_meals_per_day:]
            day_plan = DayMealPlan(
                day=state["current_day"],
                meals=today_meals,
                daily_totals=calculate_daily_totals(today_meals)
            )
            weekly_plan = state["weekly_plan"] + [day_plan]
        else:
            current_day = state["current_day"]
            weekly_plan = state["weekly_plan"]

        # 끼니 타입 결정
        meal_types = MEAL_TYPES[:total_meals_per_day]
        current_meal_type = meal_types[current_meal_index] if current_meal_index < len(meal_types) else "점심"

        return {
            "completed_meals": completed_meals,
            "weekly_plan": weekly_plan,
            "current_day": current_day,
            "current_meal_index": current_meal_index,
            "current_meal_type": current_meal_type,
            "retry_count": 0,  # 리셋
            "validation_results": [],  # 리셋
            "nutritionist_recommendation": None,
            "chef_recommendation": None,
            "budget_recommendation": None,
            "current_menu": None,
            "events": [{"type": "meal_complete", "day": state["current_day"], "meal": state["current_meal_type"]}],
        }
    else:
        # 실패: 재시도 또는 에러
        if retry_count < max_retries:
            failed_validators = [v.validator for v in validation_results if not v.passed]
            return {
                "retry_count": retry_count + 1,
                "validation_results": [],
                "nutritionist_recommendation": None,
                "chef_recommendation": None,
                "budget_recommendation": None,
                "current_menu": None,
                "events": [{"type": "retry", "attempt": retry_count + 1, "reason": failed_validators}],
            }
        else:
            # 최대 재시도 초과
            return {
                "error_message": f"최대 재시도 횟수({max_retries})를 초과했습니다.",
                "events": [{"type": "error", "message": "max_retries_exceeded"}],
            }
```

---

## 그래프 정의 (graph.py)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph import Send

def should_continue(state: MealPlanState) -> str:
    """완료 조건 체크"""
    if state.get("error_message"):
        return "error"

    profile = state["profile"]
    current_day = state["current_day"]

    if current_day > profile.days:
        return "complete"

    return "continue"

def create_meal_planner_graph():
    graph = StateGraph(MealPlanState)

    # 노드 추가
    graph.add_node("nutrition_calculator", nutrition_calculator)
    graph.add_node("nutritionist", nutritionist_agent)
    graph.add_node("chef", chef_agent)
    graph.add_node("budget", budget_agent)
    graph.add_node("conflict_resolver", conflict_resolver)
    graph.add_node("nutrition_checker", nutrition_checker)
    graph.add_node("allergy_checker", allergy_checker)
    graph.add_node("time_checker", time_checker)
    graph.add_node("decision_maker", decision_maker)

    # 시작 → 영양 계산
    graph.add_edge(START, "nutrition_calculator")

    # 영양 계산 → 3 전문가 (병렬)
    graph.add_edge("nutrition_calculator", "nutritionist")
    graph.add_edge("nutrition_calculator", "chef")
    graph.add_edge("nutrition_calculator", "budget")

    # 3 전문가 → 통합
    graph.add_edge("nutritionist", "conflict_resolver")
    graph.add_edge("chef", "conflict_resolver")
    graph.add_edge("budget", "conflict_resolver")

    # 통합 → 3 검증 (병렬)
    graph.add_edge("conflict_resolver", "nutrition_checker")
    graph.add_edge("conflict_resolver", "allergy_checker")
    graph.add_edge("conflict_resolver", "time_checker")

    # 3 검증 → 결정
    graph.add_edge("nutrition_checker", "decision_maker")
    graph.add_edge("allergy_checker", "decision_maker")
    graph.add_edge("time_checker", "decision_maker")

    # 결정 → 조건부 분기
    graph.add_conditional_edges(
        "decision_maker",
        should_continue,
        {
            "continue": "nutritionist",  # 다음 끼니 → 다시 전문가들에게
            "complete": END,
            "error": END,
        }
    )

    return graph.compile()
```

---

## 테스트 코드

```python
import asyncio
from app.agents.graph import create_meal_planner_graph
from app.models.state import UserProfile

async def test_meal_planner():
    graph = create_meal_planner_graph()

    # 테스트 프로필
    profile = UserProfile(
        goal="다이어트",
        weight=70,
        height=175,
        age=30,
        gender="male",
        activity_level="moderate",
        restrictions=["우유", "땅콩"],
        health_conditions=[],
        calorie_adjustment=None,
        budget=100000,
        budget_type="weekly",
        cooking_time="30분 이내",
        skill_level="중급",
        meals_per_day=3,
        days=1,  # 테스트는 1일만
    )

    initial_state = {
        "profile": profile,
        "max_retries": 5,
    }

    # 그래프 실행 (스트리밍)
    async for event in graph.astream(initial_state):
        print(f"Event: {event}")

    print("=== 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_meal_planner())
```

---

## 환경 변수 (.env.example)

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-3-5-haiku-latest
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

---

## requirements.txt

```
langgraph>=0.2.0
langchain>=0.3.0
langchain-anthropic>=0.3.0
pydantic>=2.0.0
python-dotenv>=1.0.0
fastapi>=0.115.0
uvicorn>=0.32.0
httpx>=0.27.0
```

---

## 추가 요구사항

1. **Mock 모드**: 실제 LLM 호출 없이 테스트할 수 있는 mock 응답 옵션
2. **로깅**: 각 노드 실행 시 상세 로그 출력
3. **에러 핸들링**: LLM 응답 파싱 실패, API 오류 등 예외 처리
4. **타임아웃**: 노드별 타임아웃 설정 (기본 60초)
5. **SSE 이벤트**: FastAPI에서 SSE 스트리밍으로 events 전달

---

## 실행 방법

```bash
# 테스트 실행
python -m pytest tests/ -v

# 단일 테스트
python tests/test_graph.py

# API 서버 실행
uvicorn app.main:app --reload --port 8000
```


