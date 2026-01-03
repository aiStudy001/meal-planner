## 🍽️ AI 식단 플래너 프로젝트 - 전체 정리

---

## 1. 프로젝트 개요

| 항목        | 내용                                  |
| --------- | ----------------------------------- |
| **프로젝트명** | AI 식단 플래너 (AI Meal Planner)         |
| **목표**    | AI 에이전트가 개인 맞춤형 7일 식단을 생성하는 서비스     |
| **핵심 특징** | 멀티 에이전트 협업, 병렬 처리, 검증 파이프라인, 자동 재시도 |
| **개발 기간** | 5일 (12/31 ~ 1/4)                    |
| **제출 마감** | 1/4 (토) 21:00                       |

---

## 2. 기술 스택

### 2.1 전체 구성

| 영역           | 기술                                         | 버전/상세          |
| ------------ | ------------------------------------------ | -------------- |
| **Frontend** | Svelte 5 + Vite + TailwindCSS + TypeScript | shadcn-svelte  |
| **Backend**  | FastAPI + LangGraph                        | MVC 패턴         |
| **LLM**      | Claude 3.5 Haiku                           | Anthropic API  |
| **검색**       | Tavily API                                 | Primary        |
| **배포**       | AWS EC2                                    | Docker Compose |
| **런타임**      | Python 3.13 + Node.js 24                   | conda + mise   |
| **상태관리**     | Server-side (LangGraph State)              | 메모리 기반         |
| **스트리밍**     | SSE (Server-Sent Events)                   | 실시간 진행상태       |
| **레포지토리**    | Multi-repo                                 | FE/BE 분리       |

### 2.2 Fallback 전략 (프레임워크)

- **Primary**: Svelte 5
- **Fallback**: Vue 3 (Day 4 14:00까지 Input 페이지 미완성 시 전환)

---

## 3. 비즈니스 로직

### 3.1 BMR/TDEE 계산

**Mifflin-St Jeor 공식:**

```
남성: BMR = (10 × 체중kg) + (6.25 × 키cm) - (5 × 나이) + 5
여성: BMR = (10 × 체중kg) + (6.25 × 키cm) - (5 × 나이) - 161

TDEE = BMR × 활동계수
```

**활동계수 (4단계):**

| 레벨        | 계수    | 설명              |
| --------- | ----- | --------------- |
| Low       | 1.2   | 좌식 생활           |
| Moderate  | 1.375 | 가벼운 운동 1-3회/주   |
| High      | 1.55  | 중간 운동 3-5회/주    |
| Very High | 1.725 | 강도 높은 운동 6-7회/주 |

---

### 3.2 칼로리 조정

**목표별 기본값:**

| 목표   | 조정값       | 사용자 조정 범위                   |
| ---- | --------- | --------------------------- |
| 다이어트 | -500 kcal | -1000 ~ 0 (권장: -800 ~ -200) |
| 벌크업  | +500 kcal | 0 ~ +1000 (권장: +200 ~ +800) |
| 유지   | ±0        | -                           |
| 질병관리 | LLM 판단    | 질병별 상이                      |

**프리셋 옵션:**

```python
CALORIE_PRESETS = {
    "다이어트": [
        {"label": "느슨하게", "value": -300},
        {"label": "보통", "value": -500, "default": True},
        {"label": "강하게", "value": -700},
    ],
    "벌크업": [
        {"label": "느슨하게", "value": +300},
        {"label": "보통", "value": +500, "default": True},
        {"label": "강하게", "value": +700},
    ],
}
```

**사용자 조정 로직 (Hybrid B+D):**

- **Basic Mode**: 프리셋 선택 (느슨/보통/강함)
- **Advanced Mode**: 직접 숫자 입력 + 유효성 검사
- 범위 초과 시: 경고 + 권장값 제안 → 사용자가 수용/유지 선택

---

### 3.3 매크로 비율 (탄:단:지)

| 목표   | 탄수화물 | 단백질 | 지방  |
| ---- | ---- | --- | --- |
| 다이어트 | 50%  | 30% | 20% |
| 벌크업  | 40%  | 40% | 20% |
| 유지   | 55%  | 20% | 25% |
| 당뇨병  | 45%  | 25% | 30% |
| 고혈압  | 55%  | 20% | 25% |

**허용 범위:**

- 탄수화물: 20-70%
- 단백질: 10-50%
- 지방: 10-50%
- 합계: 반드시 100%

---

### 3.4 건강 상태 (3종, 복수 선택 가능)

| 질병       | 주요 제한                                  |
| -------- | -------------------------------------- |
| **당뇨병**  | 탄수화물 40-50%, 당류 ≤25g/일, 저GI 식품 선호      |
| **고혈압**  | 나트륨 ≤2000mg/일, 고칼륨 식품 권장               |
| **고지혈증** | 지방 20-25%, 포화지방 ≤15g/일, 콜레스테롤 ≤300mg/일 |

**복수 선택 시:** 가장 엄격한 값 적용

---

### 3.5 알레르기 목록 (식약처 22종)

| 카테고리        | 항목                            |
| ----------- | ----------------------------- |
| **동물성 단백질** | 알류(계란), 우유, 쇠고기, 돼지고기, 닭고기    |
| **해산물**     | 고등어, 게, 새우, 오징어, 조개류(굴/전복/홍합) |
| **견과류**     | 땅콩, 호두, 잣                     |
| **곡류/두류**   | 밀, 메밀, 대두                     |
| **과일**      | 복숭아, 토마토                      |
| **기타**      | 아황산류                          |

---

### 3.6 식이 선호 (7종)

| 옵션        | 설명           |
| --------- | ------------ |
| 채식 (락토오보) | 유제품, 계란 허용   |
| 비건        | 동물성 식품 완전 배제 |
| 페스코       | 해산물 허용 채식    |
| 저염식       | 나트륨 제한       |
| 저당식       | 당류 제한        |
| 저지방       | 지방 제한        |
| 글루텐프리     | 밀, 보리, 호밀 배제 |

---

### 3.7 조리 설정

**조리 시간 (3단계):**

| 옵션     | 설명        |
| ------ | --------- |
| 15분 이내 | 초간단 요리    |
| 30분 이내 | 일반 가정식    |
| 제한 없음  | 복잡한 요리 가능 |

**요리 실력 (3단계):**

| 레벨  | 설명     | 툴팁                 |
| --- | ------ | ------------------ |
| 초급  | 기본 조리  | 전자레인지, 끓이기, 간단한 볶음 |
| 중급  | 일반 조리  | 볶음, 굽기, 찜          |
| 고급  | 복잡한 조리 | 복합 조리, 베이킹, 다양한 기법 |

---

### 3.8 식단 설정

| 항목   | 옵션              |
| ---- | --------------- |
| 끼니 수 | 1-4끼/일 (사용자 선택) |
| 기간   | 1-7일 (사용자 선택)   |

---

### 3.9 예산 설정

**입력 방식 (3가지 모두 제공):**

- 주간 총액
- 일간 총액
- 끼니당 금액

**배분 방식 (사용자 선택):**

- 균등 배분
- 차등 배분 (아침 < 점심 < 저녁)

**최소 금액:**

| 단위  | 에러        | 경고        |
| --- | --------- | --------- |
| 주간  | < 10,000원 | < 30,000원 |
| 끼니당 | < 1,000원  | < 2,000원  |

---

### 3.10 검증 규칙

| 항목          | 기준             |
| ----------- | -------------- |
| **영양 허용범위** | 목표값 ±20%       |
| **재시도 횟수**  | 최대 5회/끼니       |
| **타임아웃**    | 60초/끼니, 15분/전체 |

**입력값 검증:**

| 항목  | 경고 범위     | 에러 범위    |
| --- | --------- | -------- |
| 체중  | 30-200kg  | 1-300kg  |
| 키   | 100-220cm | 50-250cm |
| 나이  | 100+ 경고   | 10 미만 에러 |

---

### 3.11 필수 면책조항

```
⚠️ 이 서비스는 일반적인 영양 정보를 제공하며 의학적 조언을 대체하지 않습니다.
질병 관리가 필요한 경우 반드시 의료 전문가와 상담하세요.
```

---

## 4. 프로젝트 구조

### 4.1 Frontend (meal-planner-frontend)

```
meal-planner-frontend/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── Dockerfile
├── .env.example
├── index.html
├── src/
│   ├── main.ts
│   ├── App.svelte
│   ├── app.css
│   ├── router.ts                 # svelte-spa-router
│   ├── routes/
│   │   ├── Home.svelte           # 서비스 소개
│   │   ├── Input.svelte          # 프로필 입력
│   │   ├── Processing.svelte     # 생성 중 (진행상태)
│   │   └── Result.svelte         # 결과 (7일 식단)
│   ├── components/
│   │   ├── ui/                   # shadcn-svelte
│   │   ├── ProfileForm.svelte
│   │   ├── GoalSelector.svelte
│   │   ├── HealthConditions.svelte
│   │   ├── MealCard.svelte
│   │   ├── WeeklyCalendar.svelte
│   │   ├── NutritionSummary.svelte
│   │   ├── AgentProgress.svelte
│   │   └── GroceryList.svelte
│   ├── stores/
│   │   ├── profile.ts
│   │   └── mealPlan.ts
│   ├── api/
│   │   └── client.ts             # SSE client
│   ├── types/
│   │   └── index.ts
│   └── utils/
│       └── nutrition.ts
└── static/
```

### 4.2 Backend (meal-planner-backend)

```
meal-planner-backend/
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── controllers/              # [C] API 라우트
│   │   ├── __init__.py
│   │   └── meal_plan.py
│   ├── services/                 # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── meal_plan_service.py
│   │   └── llm_service.py
│   ├── models/                   # [M] 데이터 스키마
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   ├── responses.py
│   │   └── state.py
│   ├── agents/                   # LangGraph
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── nodes/
│   │   │   ├── nutrition_calculator.py
│   │   │   ├── meal_planning/
│   │   │   │   ├── supervisor.py
│   │   │   │   ├── nutritionist.py
│   │   │   │   ├── chef.py
│   │   │   │   ├── budget.py
│   │   │   │   └── conflict_resolver.py
│   │   │   ├── validation/
│   │   │   │   ├── supervisor.py
│   │   │   │   ├── nutrition_checker.py
│   │   │   │   ├── allergy_checker.py
│   │   │   │   └── time_checker.py
│   │   │   └── decision_maker.py
│   │   └── tools/
│   │       └── recipe_search.py
│   └── utils/
│       ├── nutrition.py
│       └── constants.py
├── data/
│   └── recipes_cache.json        # 로컬 캐시 (Option E)
└── tests/
    ├── test_nutrition.py
    └── test_graph.py
```

---

## 5. LangGraph 아키텍처

### 5.1 전체 그래프 흐름

```
__start__
    │
    ▼
nutrition_calculator ──────────────────────────────────┐
    │                                                  │
    ▼                                                  │
┌─────────────────────────────────────────────────┐    │
│         meal_planning_supervisor                │    │
│  ┌──────────┬──────────┬──────────┐            │    │
│  ▼          ▼          ▼          │            │    │
│ nutritionist  chef    budget      │  (병렬)    │    │
│  │          │          │          │            │    │
│  └──────────┴──────────┴──────────┘            │    │
│              │                                  │    │
│              ▼                                  │    │
│       conflict_resolver                         │    │
└─────────────────────────────────────────────────┘    │
    │                                                  │
    ▼                                                  │
┌─────────────────────────────────────────────────┐    │
│         validation_supervisor                   │    │
│  ┌──────────────┬───────────────┬────────────┐ │    │
│  ▼              ▼               ▼            │ │    │
│ nutrition    allergy         time            │ │(병렬)
│ _checker     _checker        _checker        │ │    │
│  └──────────────┴───────────────┴────────────┘ │    │
│                     │                          │    │
│                     ▼                          │    │
│            validation_aggregator               │    │
└─────────────────────────────────────────────────┘    │
    │                                                  │
    ▼                                                  │
decision_maker                                         │
    │                                                  │
    ├── 통과 ──► day_iterator ──► (다음 날 or 완료)    │
    │               │                                  │
    │               └──────────────────────────────────┘
    │
    └── 실패 ──► retry_router
                    │
                    ├── 1개 실패 ──► 해당 노드만 재실행
                    │
                    └── 2개+ 실패 ──► meal_planning 전체 재실행
```

### 5.2 노드 상세

| 노드                       | 역할              | 입력                    | 출력                            |
| ------------------------ | --------------- | --------------------- | ----------------------------- |
| **nutrition_calculator** | BMR/TDEE/매크로 계산 | profile               | daily_calories, macro_targets |
| **nutritionist**         | 영양 관점 메뉴 추천     | targets, restrictions | recommendation                |
| **chef**                 | 맛/조리 관점 메뉴 추천   | targets, skill, time  | recommendation                |
| **budget**               | 비용 관점 메뉴 추천     | targets, budget       | recommendation                |
| **conflict_resolver**    | 3개 추천 통합        | 3x recommendations    | current_menu                  |
| **nutrition_checker**    | 영양 검증 (±20%)    | menu, targets         | validation_result             |
| **allergy_checker**      | 알레르기 검증         | menu, restrictions    | validation_result             |
| **time_checker**         | 조리시간 검증         | menu, max_time        | validation_result             |
| **decision_maker**       | 통과/재시도 결정       | validation_results    | next_action                   |

### 5.3 State 스키마

```python
from typing import TypedDict, Literal, Optional
from pydantic import BaseModel

class UserProfile(BaseModel):
    goal: Literal["다이어트", "벌크업", "유지", "질병관리"]
    weight: float  # kg
    height: float  # cm
    age: int
    gender: Literal["male", "female"]
    activity_level: Literal["low", "moderate", "high", "very_high"]
    restrictions: list[str]  # 알레르기 + 식이선호
    health_conditions: list[str]  # 당뇨, 고혈압, 고지혈증
    calorie_adjustment: Optional[int]
    macro_ratio: Optional[dict]  # {"carb": 50, "protein": 30, "fat": 20}
    budget: int
    budget_type: Literal["weekly", "daily", "per_meal"]
    budget_distribution: Literal["equal", "weighted"]
    cooking_time: Literal["15분 이내", "30분 이내", "제한 없음"]
    skill_level: Literal["초급", "중급", "고급"]
    meals_per_day: int  # 1-4
    days: int  # 1-7

class MacroTargets(BaseModel):
    carb_g: float
    protein_g: float
    fat_g: float

class MealRecommendation(BaseModel):
    menu_name: str
    ingredients: list[dict]
    reasoning: str

class Menu(BaseModel):
    meal_type: Literal["아침", "점심", "저녁", "간식"]
    menu_name: str
    calories: float
    carb_g: float
    protein_g: float
    fat_g: float
    sodium_mg: float
    ingredients: list[dict]
    recipe_steps: list[str]
    recipe_url: Optional[str]
    cooking_time: int  # 분
    estimated_cost: int  # 원

class ValidationResult(BaseModel):
    passed: bool
    reason: Optional[str]

class DayPlan(BaseModel):
    day: int
    meals: list[Menu]
    daily_summary: dict

class MealPlanState(TypedDict):
    # 입력
    profile: UserProfile

    # 계산된 목표
    daily_calories: float
    macro_targets: MacroTargets

    # 현재 진행 상태
    current_day: int
    current_meal: Literal["아침", "점심", "저녁", "간식"]

    # 전문가 추천
    nutritionist_recommendation: MealRecommendation
    chef_recommendation: MealRecommendation
    budget_recommendation: MealRecommendation

    # 통합 결과
    current_menu: Menu

    # 검증 결과
    nutrition_check: ValidationResult
    allergy_check: ValidationResult
    time_check: ValidationResult

    # 최종 결과
    weekly_meal_plan: list[DayPlan]
    grocery_list: list[dict]

    # 제어
    retry_count: int
    max_retries: int  # 5
    error_message: Optional[str]
```

---

## 6. 데이터 소스 전략

### 6.1 구성

```
┌─────────────────────────────────────────────────────┐
│                    Primary                          │
│                  Tavily 웹 검색                      │
└─────────────────────┬───────────────────────────────┘
                      │ 실패 시
                      ▼
┌─────────────────────────────────────────────────────┐
│                  Fallback                           │
│   Option B: 농림수산식품교육문화정보원 API            │
│   Option E: KADX 만개의레시피 (로컬 캐시)            │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                 영양정보 보완                        │
│        Option D: 식품영양성분 DB API                 │
└─────────────────────────────────────────────────────┘
```

### 6.2 데이터 소스 링크

| 소스                  | 역할             | 링크                                                                                                                          |
| ------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Option B - 기본정보** | 조리시간, 난이도, 칼로리 | [농림수산식품교육문화정보원_레시피 기본정보 \| 공공데이터포털](https://www.data.go.kr/data/15057205/openapi.do)                                        |
| **Option B - 재료정보** | 재료 목록          | [농림수산식품교육문화정보원_레시피 재료정보 \| 공공데이터포털](https://www.data.go.kr/data/15058981/openapi.do)                                        |
| **Option D**        | 상세 영양정보        | [식품영양성분 데이터베이스](https://various.foodsafetykorea.go.kr/nutrient/industry/openApi/info.do)                                    |
| **Option E**        | 로컬 캐시 (CSV)    | [무료 레시피 데이터 - KADX 농식품 빅데이터 거래소](https://kadx.co.kr/opmk/frn/pmumkproductDetail/PMU_79c6f1a4-56dd-492e-ad67-c5acba0304d2/5) |

### 6.3 로컬 캐시 구조

```json
{
  "recipes": [
    {
      "id": "10001",
      "name": "닭가슴살 샐러드",
      "category": "샐러드",
      "cooking_time": "15분 이내",
      "difficulty": "초급",
      "servings": 2,
      "ingredients": [
        {"name": "닭가슴살", "amount": "150g"},
        {"name": "양상추", "amount": "100g"}
      ],
      "nutrition": {
        "calories": 350,
        "carb_g": 15,
        "protein_g": 40,
        "fat_g": 12,
        "sodium_mg": 450
      },
      "allergens": ["닭고기"],
      "tags": ["다이어트", "고단백"]
    }
  ]
}
```

---

## 7. API 명세

### 7.1 엔드포인트

| Method | Path            | 설명          |
| ------ | --------------- | ----------- |
| GET    | `/api/health`   | 헬스 체크       |
| POST   | `/api/generate` | 식단 생성 (SSE) |

### 7.2 요청 스키마

```json
{
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
  "cooking_time": "30분 이내",
  "skill_level": "중급",
  "meals_per_day": 3,
  "days": 7
}
```

### 7.3 SSE 이벤트 타입

| type            | 설명    | 데이터                       |
| --------------- | ----- | ------------------------- |
| `progress`      | 진행 상태 | node, status, message     |
| `validation`    | 검증 결과 | validator, passed, reason |
| `retry`         | 재시도   | attempt, reason           |
| `meal_complete` | 끼니 완료 | day, meal, menu           |
| `complete`      | 전체 완료 | result                    |
| `error`         | 에러    | message, code             |

---

## 8. 테스트 시나리오

### 8.1 유저 페르소나 (7개)

| #   | 페르소나     | 주요 특징                         |
| --- | -------- | ----------------------------- |
| 1   | 직장인 다이어터 | 30대 남성, 다이어트, 30분, 중급, 10만원/주 |
| 2   | 헬스 벌커    | 20대 남성, 벌크업, 제한없음, 고급, 15만원/주 |
| 3   | 비건 여성    | 30대 여성, 유지, 비건, 30분           |
| 4   | 당뇨+고혈압   | 50대 남성, 질병관리, 저당+저염           |
| 5   | 다중 알레르기  | 20대 여성, 다이어트, 우유+계란+밀 제외      |
| 6   | 극한 예산    | 30대 남성, 유지, 5만원/주             |
| 7   | 시간 제약    | 30대 여성, 다이어트, 15분, 초급         |

### 8.2 Edge Cases

**입력 극단값:**

- 체중 < 30kg 또는 > 200kg → 경고 + 진행
- 나이 < 10 → 에러 (서비스 대상 아님)
- 나이 > 100 → 경고 (고령자 주의)

**알레르기/식이 충돌:**

- 10개 이상 알레르기 → 경고
- 모든 단백질 소스 제외 → 경고
- 22개 전체 알레르기 → 에러
- 비건 + 고단백 벌크업 → 경고 + 식물성 단백질 집중

**건강 상태 충돌:**

- 당뇨 + 벌크업 → 경고 (의사 상담 권고)
- 고혈압 + 극단적 다이어트 → 경고

**재시도/실패:**

- 1개 검증 실패 → 해당 노드만 재실행
- 2개+ 검증 실패 → meal_planning 전체 재실행
- 5회 재시도 초과 → 에러 + 제안

**타임아웃:**

- 끼니당 > 60초 → 타임아웃 경고 + 재시도
- 전체 > 15분 → 부분 결과 반환
- LLM API 타임아웃 → 3회 재시도 후 에러
- Tavily 타임아웃 → Fallback 사용

---

## 9. 개발 일정

### 9.1 5일 스프린트

| Day   | 날짜        | 주요 작업                                                                 | 체크포인트                  |
| ----- | --------- | --------------------------------------------------------------------- | ---------------------- |
| **1** | 12/31 (화) | 프로젝트 셋업, 환경 구성, API 키, Docker                                         | `docker-compose up` 성공 |
| **2** | 1/1 (수)   | Backend 코어: State, nutrition_calculator, 3 experts, conflict_resolver | 1끼니 생성 (검증 없이)         |
| **3** | 1/2 (목)   | Backend 완성: Validators, decision_maker, 7일 루프, SSE                    | API로 7일 식단 JSON 반환     |
| **4** | 1/3 (금)   | Frontend: Svelte 학습, 4개 페이지, API 연동                                   | 로컬 E2E 동작              |
| **5** | 1/4 (토)   | 배포, 버그 수정, README, 데모 시나리오                                            | Live URL + 문서 완료       |

### 9.2 시간 버퍼

- **총 버퍼**: 10시간 (50시간의 20%)
- Day 3 지연 → Day 4 오전 사용
- Day 4 지연 → Day 5 오전 사용
- Day 5 배포 이슈 → 마감까지

---

## 10. 리스크 관리

### 10.1 주요 리스크

| ID  | 리스크                  | 심각도 | 예방                  | Plan B                     |
| --- | -------------------- | --- | ------------------- | -------------------------- |
| R1  | Svelte 학습 곡선         | 🔴  | Day 4 오전 2시간 학습     | Vue 3 전환 (Day 4 14:00 트리거) |
| R2  | LangGraph Send() API | 🔴  | Day 1 저녁 테스트        | 순차 실행으로 변경                 |
| R3  | LLM 응답 품질            | 🟡  | 프롬프트 템플릿 + JSON 스키마 | 재시도 로직                     |
| R4  | EC2 배포 이슈            | 🟡  | Day 1 Docker 로컬 테스트 | Railway/Render             |
| R5  | API 비용 초과            | 🟡  | Haiku 사용, 테스트 제한    | 일일 사용량 모니터링                |
| R8  | 시간 부족                | 🔴  | MVP 명확화             | Feature cut-off            |

### 10.2 MVP vs Nice-to-Have

**MVP (필수):**

- ✅ 프로필 입력 (기본 + 목표 + 제한사항)
- ✅ 7일 식단 생성
- ✅ 3 전문가 에이전트
- ✅ 영양 + 알레르기 검증
- ✅ 5회 재시도 로직
- ✅ SSE 실시간 진행상태
- ✅ 결과 페이지 (7일 캘린더)
- ✅ 배포 (Live URL)
- ✅ README

**Nice-to-Have:**

- ⬜ 장보기 목록 생성
- ⬜ Advanced 모드 (직접 숫자 입력)
- ⬜ 질병관리 옵션
- ⬜ 예산 배분 옵션
- ⬜ PDF 다운로드
- ⬜ 결과 히스토리

### 10.3 Cut-off 트리거

| 시점       | 조건           | 액션                 |
| -------- | ------------ | ------------------ |
| Day 3 저녁 | Backend 미완성  | Nice-to-Have 전체 제외 |
| Day 4 오후 | Frontend 미완성 | 질병관리 + Advanced 제외 |
| Day 5 오전 | 배포 실패        | Railway/Render 사용  |

---

## 11. 문서화

### 11.1 문서 목록

| 문서                                 | 위치                           | 우선순위 |
| ---------------------------------- | ---------------------------- | ---- |
| [README.md](http://README.md) (BE) | backend 레포 루트                | P0   |
| [README.md](http://README.md) (FE) | frontend 레포 루트               | P0   |
| API 문서                             | backend/docs/api.md          | P1   |
| 아키텍처 문서                            | backend/docs/architecture.md | P1   |
| .env.example                       | 각 레포 루트                      | P0   |

### 11.2 환경 변수

**Backend (.env.example):**

```
# LLM
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Search
TAVILY_API_KEY=tvly-xxxxx

# Public Data API
PUBLIC_DATA_API_KEY=xxxxx
FOOD_NUTRITION_API_KEY=xxxxx

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# CORS
CORS_ORIGINS=http://localhost:3000,<https://your-domain.com>
```

**Frontend (.env.example):**

```
VITE_API_URL=http://localhost:8000
```

---

## 12. 남은 준비 항목

### 12.1 Day 1 시작 전 필수

| 항목              | 상태      | 비고                           |
| --------------- | ------- | ---------------------------- |
| Claude API 키    | ⬜ 확인 필요 |                              |
| Tavily API 키    | ⬜ 확인 필요 |                              |
| 공공데이터포털 API 키   | ⬜ 신청 필요 | Option B                     |
| 식품영양성분 DB API 키 | ⬜ 신청 필요 | Option D                     |
| KADX 회원가입 + CSV | ⬜ 다운로드  | Option E                     |
| AWS 계정          | ⬜ 확인 필요 | EC2                          |
| GitHub 레포 생성    | ⬜       | FE/BE 각각                     |
| 개발 환경           | ⬜       | Python 3.13, Node 24, Docker |

### 12.2 추가 정리 가능 항목

| 항목              | 우선순위 |
| --------------- | ---- |
| 에이전트별 프롬프트 초안   | P1   |
| UI 와이어프레임       | P2   |
| API 키 발급 상세 가이드 | P2   |

---

이게 현재까지 정리된 전체 내용이야! 빠진 거 있거나 수정할 부분 있으면 말해줘.
