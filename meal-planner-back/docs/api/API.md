# Meal Planner API Reference

## 기본 정보
- Base URL: http://localhost:8000
- 인증: 없음 (Open API)
- Content-Type: application/json
- SSE Response: text/event-stream

## Endpoints

### 1. Health Check
```
GET /api/health
```

**응답**:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

**Status Codes**:
- 200: 서비스 정상 작동

---

### 2. 식단 생성 (SSE 스트리밍)
```
POST /api/generate
```

**Request Body**: MealPlanRequest (17개 필드)

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| goal | string | Yes | "다이어트" \| "벌크업" \| "유지" \| "질병관리" | 식단 목표 |
| weight | float | Yes | 0 < weight ≤ 300 | 체중 (kg) |
| height | float | Yes | 50 < height ≤ 250 | 키 (cm) |
| age | int | Yes | 0 < age ≤ 150 | 나이 |
| gender | string | Yes | "male" \| "female" | 성별 |
| activity_level | string | Yes | "low" \| "moderate" \| "high" \| "very_high" | 활동 수준 |
| restrictions | string[] | No | Sanitized (한글/영문/숫자/공백/하이픈) | 알레르기/식이선호 |
| health_conditions | string[] | No | Sanitized (한글/영문/숫자/공백/하이픈) | 건강 상태 (당뇨, 고혈압 등) |
| calorie_adjustment | int \| null | No | - | 칼로리 조정값 |
| macro_ratio | object \| null | No | - | 매크로 비율 (carb/protein/fat) |
| budget | int | Yes | 10,000 ≤ budget ≤ 1,000,000 | 예산 (원) |
| budget_type | string | No | "weekly" \| "daily" \| "per_meal" | 예산 타입 (기본: weekly) |
| budget_distribution | string | No | "equal" \| "weighted" | 예산 배분 방식 (기본: equal) |
| cooking_time | string | Yes | "15분 이내" \| "30분 이내" \| "제한 없음" | 조리 시간 |
| skill_level | string | Yes | "초급" \| "중급" \| "고급" | 요리 실력 |
| meals_per_day | int | Yes | 1 ≤ meals_per_day ≤ 4 | 하루 끼니 수 |
| days | int | Yes | 1 ≤ days ≤ 7 | 계획 일수 |

**Validation Rules**:
1. **끼니당 최소 예산**: 2,000원/끼니
   - Calculation: `per_meal_budget = budget / (meals_per_day * days)` (for weekly)
   - Error: 422 Validation Error if `per_meal_budget < 2,000`

2. **Prompt Injection 방지**:
   - `restrictions`, `health_conditions` 필드는 sanitization 적용
   - 허용 문자: 한글, 영문, 숫자, 공백, 하이픈만
   - 차단 패턴: "ignore", "instructions", "prompt" 등

**Response (SSE Stream)**:

Server-Sent Events 스트림으로 실시간 진행 상황 전송:

```
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
```

**Event Types (6가지)**:

#### 1. progress
노드 실행 진행 상태

```json
{
  "type": "progress",
  "data": {
    "node": "nutrition_calculator" | "meal_planning_supervisor" | "nutritionist_agent" | "chef_agent" | "budget_agent" | "day_iterator",
    "status": "calculating" | "planning" | ...,
    "message": {} // node-specific data
  }
}
```

#### 2. validation
검증 결과 (5개 validator)

```json
{
  "type": "validation",
  "data": {
    "validator": "nutrition_checker" | "allergy_checker" | "time_checker" | "health_checker" | "budget_checker",
    "passed": true | false,
    "reason": "영양 목표 충족" | null,
    "issues": ["칼로리 초과: 800kcal"] // passed=false인 경우
  }
}
```

#### 3. retry
재시도 이벤트

```json
{
  "type": "retry",
  "data": {
    "attempt": 1~5,
    "reason": "칼로리 20% 초과"
  }
}
```

#### 4. meal_complete
끼니 완료

```json
{
  "type": "meal_complete",
  "data": {
    "day": 1~7,
    "meal": "아침" | "점심" | "저녁" | "간식",
    "menu": {
      "meal_type": "아침",
      "menu_name": "닭가슴살 샐러드",
      "calories": 550.0,
      "carb_g": 70.0,
      "protein_g": 40.0,
      "fat_g": 10.0,
      "sodium_mg": 400.0,
      "sugar_g": 5.0,
      "ingredients": [
        {"name": "닭가슴살", "amount": "150g", "amount_g": 150.0},
        {"name": "현미밥", "amount": "210g", "amount_g": 210.0}
      ],
      "recipe_steps": ["재료 준비", "조리", "완성"],
      "cooking_time_minutes": 20,
      "estimated_cost": 5000,
      "validation_warnings": []
    }
  }
}
```

#### 5. complete
전체 완료 (주간 식단)

```json
{
  "type": "complete",
  "data": {
    "result": [
      {
        "day": 1,
        "meals": [/* Menu objects */],
        "total_calories": 2100.0,
        "total_carb_g": 262.5,
        "total_protein_g": 157.5,
        "total_fat_g": 46.7,
        "total_cost": 15000
      }
      // ... days 2-7
    ]
  }
}
```

#### 6. error
에러 발생

```json
{
  "type": "error",
  "data": {
    "message": "LLM API 응답 시간이 25초를 초과하였습니다",
    "code": "GRAPH_ERROR" | "LLM_TIMEOUT" | "VALIDATION_ERROR" | "UNKNOWN_ERROR"
  }
}
```

---

## Error Responses

| Status | Scenario | Response Body | Example |
|--------|----------|---------------|---------|
| 409 | 중복 요청 (동일 프로필) | `{"error": "...", "request_key": "..."}` | 동일한 프로필로 이미 식단 생성이 진행 중입니다. |
| 422 | Validation 실패 | `{"detail": [...]}` | Pydantic validation errors (예산 부족, 필드 범위 초과, injection 차단) |
| 500 | 서버 에러 | `{"detail": "..."}` | LLM timeout, graph 실행 에러 등 |

**409 Conflict 상세**:
```json
{
  "error": "동일한 프로필로 이미 식단 생성이 진행 중입니다. 잠시 후 다시 시도해주세요.",
  "request_key": "a1b2c3d4e5f6g7h8"
}
```

**422 Validation Error 상세**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "budget"],
      "msg": "끼니당 예산이 너무 낮습니다. 현재: 1,905원/끼니, 최소 요구: 2,000원/끼니 (예산 타입: weekly, 하루 3끼, 7일)",
      "input": 40000
    }
  ]
}
```

**500 Internal Server Error 상세**:
```json
{
  "detail": "LLM API 응답 시간이 25초를 초과하였습니다 (요청 내용 길이: 500자)"
}
```

---

## Request Deduplication

동일한 프로필로 생성된 **SHA256 해시 기반** 중복 요청 방지:

**Key 생성 필드**:
- goal, weight, height, age, gender, activity_level, budget, budget_type, meals_per_day, days

**동작 방식**:
1. 요청 수신 시 위 필드로 해시 생성 (16자 prefix)
2. Active requests에 키 존재 여부 확인
3. 존재 시 → 409 Conflict 반환
4. 존재하지 않으면 → 처리 진행, 완료 시 제거

**유효 기간**: 요청 처리 중에만 유지 (완료/에러 시 자동 제거)

---

## Performance Characteristics

- **평균 응답 시간**: 30-120초 (7일 3끼 기준)
- **SSE 이벤트 수**: ~190 events (7일 3끼: 21끼 × 9 events/끼)
- **Timeout**: LLM 호출당 25초, 전체 요청 timeout 없음 (SSE 스트림)
- **Concurrency**: Active requests 관리 (중복 방지)

---

## Example Request

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
  "budget_distribution": "equal",
  "cooking_time": "30분 이내",
  "skill_level": "중급",
  "meals_per_day": 3,
  "days": 7
}
```
