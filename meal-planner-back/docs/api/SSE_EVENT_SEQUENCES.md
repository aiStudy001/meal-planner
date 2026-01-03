# SSE Event Sequences

## 이벤트 타입 (6가지)

### 1. progress
**노드 실행 진행 상태**

```json
{
  "type": "progress",
  "data": {
    "node": "nutrition_calculator" | "meal_planning_supervisor" | "nutritionist_agent" | "chef_agent" | "budget_agent" | "day_iterator",
    "status": "calculating" | "planning" | "recommending" | "adjusting" | ...,
    "message": {} // node-specific data
  }
}
```

**발생 시점**: 각 노드가 실행을 시작할 때

**주요 노드**:
- `nutrition_calculator`: 영양 목표 계산
- `meal_planning_supervisor`: 식단 계획 조정
- `nutritionist_agent`: 영양사 추천
- `chef_agent`: 요리사 메뉴 생성
- `budget_agent`: 예산 조정
- `day_iterator`: 끼니/날짜 진행

---

### 2. validation
**검증 결과 (5개 validator)**

```json
{
  "type": "validation",
  "data": {
    "validator": "nutrition_checker" | "allergy_checker" | "time_checker" | "health_checker" | "budget_checker",
    "passed": true | false,
    "reason": "영양 목표 충족" | "칼로리 20% 초과" | null,
    "issues": ["칼로리 초과: 800kcal (목표: 667kcal)"] // passed=false인 경우
  }
}
```

**발생 시점**: Menu 생성 후 5개 validator 실행

**Validator 목록**:
1. `nutrition_checker`: 칼로리/매크로 ±20% 범위
2. `allergy_checker`: 알레르기/식이선호 위반 확인
3. `time_checker`: 조리 시간 제한 확인
4. `health_checker`: 건강 상태별 제약 (나트륨/당분)
5. `budget_checker`: 예산 범위 ±20%

**통과 조건**: 모든 validator passed=true

---

### 3. retry
**재시도 이벤트**

```json
{
  "type": "retry",
  "data": {
    "attempt": 1~5,
    "reason": "칼로리 20% 초과"
  }
}
```

**발생 시점**: Validation 실패 시 (max_retries=5)

**재시도 프로세스**:
1. Validation 실패 감지
2. `retry_count` 증가
3. 이전 실패 정보를 `previous_validation_failures`에 추가
4. Nutritionist/Chef/Budget agent 재실행
5. 새로운 Menu 생성 → 다시 Validation

**종료 조건**:
- 통과: Validation passed → meal_complete
- 실패: retry_count ≥ 5 → error 이벤트

---

### 4. meal_complete
**끼니 완료**

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
      "recipe_steps": ["재료 준비하기", "조리하기", "완성"],
      "cooking_time_minutes": 20,
      "estimated_cost": 5000,
      "validation_warnings": []
    }
  }
}
```

**발생 시점**: Validation 통과 후 Menu가 `completed_meals`에 추가될 때

**Warning**: `validation_warnings`에 경미한 경고 포함 가능 (예: 나트륨 15% 초과는 통과이지만 경고)

---

### 5. complete
**전체 완료 (주간 식단)**

```json
{
  "type": "complete",
  "data": {
    "result": [
      {
        "day": 1,
        "meals": [
          {/* Menu 1 */},
          {/* Menu 2 */},
          {/* Menu 3 */}
        ],
        "total_calories": 2100.0,
        "total_carb_g": 262.5,
        "total_protein_g": 157.5,
        "total_fat_g": 46.7,
        "total_cost": 15000
      },
      {
        "day": 2,
        "meals": [...],
        "total_calories": 2050.0,
        "total_carb_g": 256.0,
        "total_protein_g": 154.0,
        "total_fat_g": 45.5,
        "total_cost": 14500
      }
      // ... days 3-7
    ]
  }
}
```

**발생 시점**: 모든 날짜/끼니 완료 후 (`current_day > profile.days`)

**구조**:
- `result`: 배열 (길이 = `days`)
- 각 DailyPlan: `day`, `meals`, `total_*` 필드
- `meals`: Menu 배열 (길이 = `meals_per_day`)

---

### 6. error
**에러 발생**

```json
{
  "type": "error",
  "data": {
    "message": "LLM API 응답 시간이 25초를 초과하였습니다 (요청 내용 길이: 500자)",
    "code": "GRAPH_ERROR" | "LLM_TIMEOUT" | "VALIDATION_ERROR" | "UNKNOWN_ERROR"
  }
}
```

**발생 시점**:
- LLM timeout (25초 초과)
- Graph 실행 중 예외 발생
- 5회 재시도 후에도 Validation 실패
- 기타 서버 에러

**에러 코드**:
- `LLM_TIMEOUT`: LLM API 응답 시간 초과
- `GRAPH_ERROR`: LangGraph 실행 에러
- `VALIDATION_ERROR`: 5회 재시도 후 검증 실패
- `UNKNOWN_ERROR`: 기타 예상치 못한 에러

---

## 정상 플로우 (1일 1끼)

```
1. progress → nutrition_calculator (영양 목표 계산)
2. progress → meal_planning_supervisor (식단 계획 조정)
3. progress → nutritionist_agent (영양사 추천)
4. progress → chef_agent (요리사 메뉴 생성)
5. progress → budget_agent (예산 조정)
6. validation → nutrition_checker (passed: true)
7. validation → allergy_checker (passed: true)
8. validation → time_checker (passed: true)
9. validation → health_checker (passed: true)
10. validation → budget_checker (passed: true)
11. meal_complete → {"day": 1, "meal": "아침", "menu": {...}}
12. complete → {"result": [{"day": 1, "meals": [...]}]}
```

**총 이벤트 수**: 12 events

**소요 시간**: ~15-30초

---

## Retry 플로우 (Validation 실패 → 재시도 → 성공)

```
1. progress → nutrition_calculator
2. progress → meal_planning_supervisor
3. progress → nutritionist_agent
4. progress → chef_agent
5. progress → budget_agent
6. validation → nutrition_checker (passed: false, reason: "칼로리 20% 초과")
7. validation → allergy_checker (passed: true)
8. validation → time_checker (passed: true)
9. validation → health_checker (passed: true)
10. validation → budget_checker (passed: true)

11. ⚠️ retry → {"attempt": 1, "reason": "칼로리 초과"}

12. progress → nutritionist_agent (재실행)
13. progress → chef_agent (재실행)
14. progress → budget_agent (재실행)
15. validation → nutrition_checker (passed: true) ✅
16. validation → allergy_checker (passed: true)
17. validation → time_checker (passed: true)
18. validation → health_checker (passed: true)
19. validation → budget_checker (passed: true)
20. meal_complete → {"day": 1, "meal": "아침", "menu": {...}}
21. complete → {"result": [...]}
```

**총 이벤트 수**: 21 events (retry 1회)

**소요 시간**: ~30-45초

---

## 에러 플로우 (LLM Timeout)

```
1. progress → nutrition_calculator
2. progress → meal_planning_supervisor
3. progress → nutritionist_agent

4. ❌ error → {"message": "LLM API 응답 시간이 25초를 초과하였습니다", "code": "LLM_TIMEOUT"}
```

**총 이벤트 수**: 4 events

**종료**: 스트림 즉시 종료

---

## 에러 플로우 (5회 재시도 후 실패)

```
1. progress → nutrition_calculator
2. progress → meal_planning_supervisor

# Attempt 1
3. progress → nutritionist_agent
4. progress → chef_agent
5. progress → budget_agent
6. validation → nutrition_checker (passed: false)
7. retry → {"attempt": 1, "reason": "칼로리 초과"}

# Attempt 2
8. progress → nutritionist_agent
9. progress → chef_agent
10. progress → budget_agent
11. validation → nutrition_checker (passed: false)
12. retry → {"attempt": 2, "reason": "칼로리 초과"}

# ... Attempts 3-5 (동일 패턴)

# Final failure
50. retry → {"attempt": 5, "reason": "칼로리 초과"}
51. ❌ error → {"message": "5회 재시도 후에도 검증을 통과하지 못했습니다", "code": "VALIDATION_ERROR"}
```

**총 이벤트 수**: ~51 events

**종료**: 5회 재시도 후 에러 발생, 스트림 종료

---

## 전체 7일 3끼 플로우 (정상)

```
Day 1:
- 아침: progress(3) + validation(5) + meal_complete = 9 events
- 점심: progress(3) + validation(5) + meal_complete = 9 events
- 저녁: progress(3) + validation(5) + meal_complete = 9 events
Subtotal: 27 events

Day 2-6: 각 27 events
Subtotal: 27 × 6 = 162 events

Day 7:
- 아침: 9 events
- 점심: 9 events
- 저녁: 9 events + complete = 28 events
Subtotal: 28 events

Total: 27 + 162 + 28 = 217 events
```

**실제 이벤트 수**: ~190-220 events (retry 포함 시 증가)

**소요 시간**: 60-120초

---

## 이벤트 카운트 공식

**정상 플로우 (retry 없음)**:
```
total_events = (meals_per_day × days × 9) + 1
             = (3 × 7 × 9) + 1
             = 190 events
```

**Retry 포함 시**:
```
total_events = base_events + (retry_count × 3)
             = 190 + (5 retries × 3 agents)
             = 205 events (예시)
```

**이벤트 breakdown (끼니당)**:
- progress: 3 (nutritionist + chef + budget)
- validation: 5 (5 validators)
- meal_complete: 1
- **Total per meal**: 9 events

---

## SSE 프로토콜 준수

**HTTP Headers**:
```
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**Event Format**:
```
data: {"type":"progress","data":{...}}

data: {"type":"validation","data":{...}}

```

**특징**:
- 각 이벤트는 `data:` prefix로 시작
- JSON 형식으로 serialize
- 이벤트 간 빈 줄 구분
- 스트림 종료 시 연결 닫힘

---

## 클라이언트 처리 권장사항

### 1. Progress 추적
```javascript
let currentDay = 0;
let currentMeal = "";
let completedMeals = 0;

if (event.type === 'meal_complete') {
  completedMeals++;
  const progress = (completedMeals / (mealsPerDay * days)) * 100;
  updateProgressBar(progress);
}
```

### 2. Validation 실패 대응
```javascript
if (event.type === 'validation' && !event.data.passed) {
  showWarning(`${event.data.validator} 검증 실패: ${event.data.reason}`);
}

if (event.type === 'retry') {
  showRetryIndicator(event.data.attempt, event.data.reason);
}
```

### 3. 에러 처리
```javascript
if (event.type === 'error') {
  eventSource.close();
  showErrorMessage(event.data.message);

  if (event.data.code === 'LLM_TIMEOUT') {
    offerRetryOption();
  }
}
```

### 4. 타임아웃 관리
```javascript
const timeout = setTimeout(() => {
  eventSource.close();
  showError('응답 시간 초과 (2분)');
}, 120000); // 2분

eventSource.addEventListener('complete', () => {
  clearTimeout(timeout);
});
```

---

## 성능 특성

| 항목 | 값 |
|-----|-----|
| 평균 이벤트 간격 | ~0.5-2초 |
| 총 스트림 시간 (7일 3끼) | 60-120초 |
| 이벤트 크기 (평균) | ~500 bytes |
| 대역폭 사용량 (7일 3끼) | ~100KB |
| Retry 발생률 | ~10-20% |
| 에러 발생률 | <1% |
