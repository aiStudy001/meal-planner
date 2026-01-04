# Meal Planner Agents 상세 문서

이 문서는 `meal-planner-back/app/agents` 폴더에 존재하는 LangGraph 기반 에이전트 시스템을 **처음 접한 사람도 전체 구조를 이해**할 수 있도록 설명합니다. 그래프가 어떤 순서로 실행되고, 어떤 상태(State)를 주고받으며, 재시도·검증·관측이 어떻게 설계되어 있는지를 단계별로 다룹니다.

```
app/agents
├── graphs
│   ├── main_graph.py            # 전체 파이프라인 정의
│   ├── meal_planning_subgraph.py
│   └── validation_subgraph.py
├── nodes
│   ├── meal_planning/           # 영양사·셰프·예산 전문가
│   ├── validation/              # 영양/알레르기/시간 검증 노드
│   ├── day_iterator.py          # 끼니·날짜 진행
│   ├── decision_maker.py        # 조건부 라우팅
│   ├── meal_planning_supervisor.py
│   ├── validation_supervisor.py
│   ├── ...
└── __init__.py
```

---

## 1. 핵심 구성요소 요약

- **LangGraph**  
  `main_graph.py`에서 `StateGraph(MealPlanState)`로 전체 파이프라인을 선언하며, `START/END` 노드와 조건부 라우팅을 활용합니다.

- **LLM 서비스**  
  전문가(`nutritionist`, `chef`, `budget`)와 충돌 해결(`conflict_resolver`)은 `app.services.llm_service`를 통해 JSON 응답을 받아 Pydantic 모델로 검증합니다.

- **상태(State)와 Reducer**  
  `app.models.state.MealPlanState`가 모든 노드 사이의 공용 데이터 계약입니다. `List` 필드는 LangGraph reducer(`operator.add`)가 적용되어 병렬 노드가 안전하게 데이터를 push 합니다.

- **관측성**  
  모든 노드가 `app.utils.logging.get_logger`로 JSON 로그를 남기고, UI/스트리밍을 위한 `events` 리스트에 진행 상황을 push 합니다.

- **실시간 가격 조회 서비스**  
  `app.services.ingredient_pricing`이 Tavily/캐시/폴백 소스를 통해 재료 단가를 계산해 주며, 예산 에이전트가 셰프 추천 재료의 실제 비용을 평가할 때 사용합니다.

---

## 2. MealPlanState 상세 보기

각 노드는 동일한 TypedDict 상태를 읽고 부분 업데이트를 반환합니다. 리스트 필드 중 일부(`validation_results`, `events`)는 커스텀 reducer를 사용하여 **최근 N개만 유지**하므로 스트리밍/장시간 세션에서도 메모리 사용량이 안정적으로 유지됩니다. 주요 필드 그룹은 아래와 같습니다.

### 입력 (사용자가 전달)

| 필드        | 타입            | 설명                                                                                                                   |
| --------- | ------------- | -------------------------------------------------------------------------------------------------------------------- |
| `profile` | `UserProfile` | 목표(`goal`), 체형, 활동량, 식단 기간(`days`), 끼니 수(`meals_per_day`), 예산(`budget` & `budget_type`), 조리 시간, 알레르기/선호 제한 등을 포함합니다. |

### 계산된 목표

| 필드                 | 타입             | 생성자                                                     |
| ------------------ | -------------- | ------------------------------------------------------- |
| `daily_targets`    | `MacroTargets` | `nutrition_calculator`가 BMR/TDEE와 목표 매크로 비율을 계산하여 채웁니다. |
| `per_meal_targets` | `MacroTargets` | 하루 목표를 끼니 수로 나눈 값입니다.                                   |
| `per_meal_budget`  | `int`          | 예산 유형(주간/일간/끼니별)에 따라 자동 계산됩니다.                          |

### 진행 상황

| 필드                   | 설명                           |
| -------------------- | ---------------------------- |
| `current_day`        | 현재 생성 중인 날짜(1~profile.days). |
| `current_meal_type`  | `"아침"`, `"점심"` 등 현재 끼니 이름.   |
| `current_meal_index` | 하루 끼니 중 0 기반 인덱스.            |

### 전문가 추천 & 최종 메뉴

| 필드                                                                            | 타입                  | 역할    |
| ----------------------------------------------------------------------------- | ------------------- | ----- |
| `nutritionist_recommendation`, `chef_recommendation`, `budget_recommendation` | `MealRecommendation | None` |
| `current_menu`                                                                | `Menu               | None` |

### 검증 및 재시도

| 필드                             | 설명                       |
| ------------------------------ | ------------------------ |
| `validation_results`           | `list[ValidationResult]` |
| `previous_validation_failures` | `list[dict]`             |
| `retry_count` / `max_retries`  | 현재 재시도 횟수 / 허용 횟수(기본 5). |
| `_validation_warnings`         | `list[str]               |

### 누적 결과 & 이벤트

| 필드                | 설명                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------ |
| `completed_meals` | 하루 동안 확정된 메뉴 리스트. 끼니를 모두 채우면 `DailyPlan` 생성 후 비웁니다.                                  |
| `weekly_plan`     | 완성된 `DailyPlan` 리스트. 모든 날짜가 끝나면 최종 산출물로 반환됩니다.                                       |
| `events`          | `[{type,node,status,data}]` 구조의 로그. SSE나 UI에서 그대로 활용하며 최대 20개까지만 유지(`limit_events`). |

---

## 3. 전체 실행 흐름

아래 다이어그램은 실제 그래프(`main_graph.py`)에서 정의된 노드와 엣지를 그대로 표현한 것입니다.

```
START
  │
  ▼
nutrition_calculator
  │
  ▼
meal_planning_supervisor --(Send)--> {nutritionist, chef, budget} --> conflict_resolver
                                                                           │
                                                                           ▼
validation_supervisor --(Send)--> {nutrition_checker, allergy_checker, time_checker, health_checker, budget_checker}
                                                                           │
                                                                           ▼
                                                                   validation_aggregator
                                                                           │
                                                                           ▼
                                                                decision_maker (함수)
                                                                           │
                     ┌─────────────────────────────────────────────────────┴─────────────────────────────────────────────────────┐
                     ▼                                                                                                         ▼
                retry_router --(특정 전문가 재실행 or meal_planning_supervisor)            day_iterator --{다음 끼니 | 다음 날 | END}
```

**📊 시각화된 그래프**: 전체 그래프의 시각적 표현은 [`docs/agent_graph.mmd`](../../docs/agent_graph.mmd)를 참고하세요. GitHub에서 자동으로 렌더링됩니다.

- `StateGraph`는 **Send API**로 병렬 분기(`meal_planning_supervisor`, `validation_supervisor`)와 **조건부 엣지**(`validation_aggregator → decision_maker`, `day_iterator → should_continue`)를 조합합니다.
- `validation_supervisor`는 현재 5개의 검증기(nutrition/allergy/time/health/budget)를 동시에 호출합니다.
- `decision_maker`는 함수형 노드로 등록되어 조건에 따라 `"retry_router"` 또는 `"day_iterator"` 문자열을 반환합니다.

---

## 4. 단계별 상세 설명

### 4.1 준비 단계 - `nutrition_calculator`

- **역할**: BMR/TDEE, 목표 매크로, 끼니당 예산 계산.
- **읽는 상태**: `profile`.
- **쓰는 상태**:
  - `daily_targets`, `per_meal_targets`, `per_meal_budget`
  - 진행 관련 필드 초기화: `current_day=1`, `current_meal_index=0`, `current_meal_type="아침"` 등
  - `retry_count=0`, `completed_meals=[]`, `weekly_plan=[]`, `events=[...]`
- **주요 로직**:
  1. `calculate_bmr`, `calculate_tdee`로 기본 에너지 요구량 산정.
  2. 목표(`goal`)와 질병 제약에 따라 `MACRO_RATIOS` 혹은 `get_strictest_ratios` 적용.
  3. 예산(`budget_type`)을 해석하여 끼니당 금액 산출.

### 4.2 Meal Planning 클러스터

#### 4.2.1 `meal_planning_supervisor`

- **LangGraph Command**를 반환하여 `Send("nutritionist", state)` 등 세 노드를 동시에 호출합니다.
- 상태는 복사 없이 그대로 전달되며, 각 노드는 자신이 필요한 필드만 읽고 업데이트를 반환합니다.

#### 4.2.2 전문가 노드 (`nodes/meal_planning/…`)

| 노드                   | 주요 책임                           | 입력                                                                                                            | 출력                                      |
| -------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `nutritionist_agent` | 칼로리/매크로·질병 제약 중심 추천             | `profile`, `per_meal_targets`, `previous_validation_failures`                                                 | `nutritionist_recommendation`, `events` |
| `chef_agent`         | 조리 시간·난이도·맛 중심 추천, 필요 시 레시피 검색  | `profile`, `per_meal_targets`, `COOKING_TIME_LIMITS`, `recipe_search_service`, `previous_validation_failures` | `chef_recommendation`, `events`         |
| `budget_agent`       | Tavily 가격 정보를 포함한 cost-first 추천 | `per_meal_budget`, `per_meal_targets`, `previous_validation_failures`, `chef_recommendation`                  | `budget_recommendation`, `events`       |

- **LLM 프롬프트 특징**
  - 모든 노드는 **JSON 응답 형식**을 엄격히 명시하여 Pydantic 검증 실패를 줄입니다.
  - 재시도 시 `previous_validation_failures`에서 자신과 관련된 검증 실패만 추려 "**이전 시도 피드백**" 섹션으로 프롬프트에 첨부합니다.
  - `chef_agent`는 `ENABLE_RECIPE_SEARCH`가 켜져 있으면 실제 레시피 검색 결과를 prompt context에 추가하여 답변 품질을 높입니다.
  - `budget_agent`는 셰프 추천 재료(`chef_recommendation.ingredients`)를 받아 `ingredient_pricing` 서비스로 Tavily 가격을 조회한 뒤 LLM에 실제 비용 정보를 전달합니다.

#### 4.2.3 `budget_router`

- **역할**: chef가 완료된 이후 budget 노드를 별도로 호출해야 하는 시나리오에서 사용 가능한 라우팅 노드입니다.
- **동작**: `Send("budget", state)` 한 줄짜리 Command를 반환하며, 로그로 셰프 추천 재료 존재 여부를 남깁니다.
- **활용 예**: 커스텀 그래프나 실험용 서브그래프에서 chef → budget 순차 실행이 필요할 때 삽입할 수 있습니다. (기본 메인 그래프는 supervisor가 세 전문가를 동시에 호출합니다.)

#### 4.2.4 `conflict_resolver`

- 세 전문가 추천을 비교/조합해 최종 메뉴(`Menu`)를 생성합니다.
- **복구 전략**: 특정 전문가만 재실행했는데 다른 추천이 `None`인 경우, `current_menu`(이전 결과)를 `MealRecommendation`으로 변환하여 결측 데이터를 채웁니다.
- **LLM 프롬프트**는 다음 정보를 포함합니다.
  1. 각 전문가의 메뉴 이름/칼로리/비용/조리시간/이유.
  2. 우선순위 규칙(영양 목표 → 알레르기 → 조리 시간 → 예산).
  3. JSON 출력 스키마(매크로·나트륨·당·레시피 단계 포함).
- 결과는 `current_menu`에 저장되고, SSE 이벤트(`node: conflict_resolver`)가 발행됩니다.

### 4.3 Validation 클러스터

#### 4.3.1 `validation_supervisor`

- `Send`로 다섯 검증 노드를 병렬 실행합니다. 각 노드는 `current_menu`, `profile`, `per_meal_targets`, `per_meal_budget` 등을 읽습니다.

#### 4.3.2 검증 노드

| 노드                  | 검증 내용                                               | 허용치/정책                                | 실패 시 상태                                        |
| ------------------- | --------------------------------------------------- | ------------------------------------- | ---------------------------------------------- |
| `nutrition_checker` | 칼로리 ±20%, 영양소 ±30% 이내인지 확인                          | 재시도 3회 이상이면 허용치를 각각 25%, 35%로 완화      | `ValidationResult(passed=False, issues=[...])` |
| `allergy_checker`   | `profile.restrictions`에 포함된 재료가 사용됐는지 검사            | 부분 문자열 매칭(대소문자 무시). 제한 사항이 없으면 자동 통과. | `issues`에 제한 식품 명시                             |
| `time_checker`      | `COOKING_TIME_LIMITS[profile.cooking_time]` 이하인지 검사 | 제한 초과분 분 수를 메시지에 포함                   | `issues`에 초과 정보 저장                             |
| `health_checker`    | 건강 조건(당뇨/고혈압/고지혈증 등)에 따른 설탕·나트륨·포화지방 제한             | 조건별 상한을 초과하면 세부 메시지 기록                | `issues`에 조건별 위반 내용                            |
| `budget_checker`    | 메뉴 예상 비용이 예산 허용 범위 내인지 확인                           | 재시도 횟수에 따라 허용 비율이 110%→115%로 완화       | `issues`에 초과 금액/비율 정보                          |

- 결과는 모두 `validation_results` 리스트에 누적(-add reducer)되며, 각 노드는 진행 이벤트를 push 합니다.

#### 4.3.3 `validation_aggregator`

- `validation_results`를 요약하여 로깅하고, 실패 항목을 `previous_validation_failures`에 정형화된 dict로 저장합니다.
- `previous_validation_failures` 예시:
  
  ```python
  {
      "validator": "nutrition_checker",
      "issues": ["칼로리 범위 초과: ..."],
      "retry_count": 1,
      "menu_name": "닭가슴살 샐러드"
  }
  ```
- 이 정보는 다음 번 전문가 실행 시 프롬프트에 자동으로 포함됩니다.

### 4.4 라우팅 및 반복

#### 4.4.1 `decision_maker`

- 입력: `validation_results`, `retry_count`, `max_retries`, `current_menu`.
- 동작:
  1. 실패 검증이 없으면 `"day_iterator"`.
  2. 실패가 있고 `retry_count < max_retries`면 `"retry_router"`.
  3. 실패 + 재시도 한계 도달 → 경고 메시지를 `_validation_warnings`에 기록하고 `"day_iterator"`.

#### 4.4.2 `retry_router`

- 입력: `retry_count`, `validation_results`.
- 로직:
  - **첫 실패(`retry_count == 0`)**: `RETRY_MAPPING`을 사용해 실패 검증과 직결되는 전문가만 재실행합니다.
    - `nutrition_checker`, `health_checker` → `nutritionist`
    - `allergy_checker`, `time_checker` → `chef`
    - `budget_checker` → `budget`
    - 매핑이 없거나 실패 목록이 비어 있으면 전체 재실행.
  - **두 번째 이후 실패**: 모든 전문가를 다시 실행하기 위해 `meal_planning_supervisor`로 보냅니다.
- 상태 업데이트:
  - `retry_count += 1`
  - `validation_results` 초기화
  - 재실행 대상이 아닌 추천은 그대로 유지하여 불필요한 LLM 호출을 방지
  - 이벤트(`node: retry_router`) 발행

#### 4.4.3 `day_iterator`

- 역할: 메뉴를 저장하고 다음 끼니/다음 날/완료를 결정합니다.
- 처리 순서:
  1. `_validation_warnings`가 있다면 `current_menu.validation_warnings`에 붙여 사용자에게 경고 표시.
  2. `completed_meals.append(current_menu)`
  3. 하루의 모든 끼니가 끝났다면 `calculate_daily_totals`로 요약 후 `DailyPlan` 생성, `weekly_plan`에 추가.
  4. 모든 날이 채워졌으면 `weekly_plan`만 반환하고 그래프는 `END`.
  5. 아직 끼니가 남아 있으면 `current_meal_index`와 `current_meal_type`을 다음 끼니로 이동.
  6. 다음 날로 넘어가거나 다음 끼니로 갈 때 **재시도 상태 및 추천 캐시를 초기화**하여 새로운 시도를 준비합니다.
- 출력 상태는 다음 실행 노드(`meal_planning_supervisor`)가 첫 호출처럼 행동할 수 있도록 구성됩니다.

---

## 5. 재시도 및 피드백 루프 심화

1. **실패 기록 저장**  
   
   - `validation_aggregator`가 실패 정보를 `previous_validation_failures`에 구조화하여 저장합니다.
   - 각 항목은 `retry_count`를 포함하여, 다음 회차에서 어떤 문제가 발생했는지 추적할 수 있습니다.

2. **전문가 프롬프트 주입**  
   
   - `nutritionist_agent`는 `validator == "nutrition_checker"`이면서 `retry_count == 현재 retry - 1`인 항목만 필터링합니다.
   - `chef_agent`는 `allergy_checker`, `time_checker` 실패 내역을 사용합니다.
   - `budget_agent`는 참고용으로 최근 실패 3개를 간단히 요약합니다.

3. **점진적 완화(Progressive Relaxation)**  
   
   - `nutrition_checker`는 재시도 3회 이상이면 허용 범위를 완화하여 영양 목표에 너무 오래 갇히지 않도록 합니다.

4. **경고 부착**  
   
   - 재시도 한계를 초과했을 때에도 그래프는 다음 끼니로 진행합니다. 대신 실패한 검증 메시지를 `_validation_warnings`에 보관했다가 `day_iterator`가 `current_menu.validation_warnings`에 붙입니다.

5. **RETRY_MAPPING**  
   
   - `app.utils.constants.RETRY_MAPPING`에서 검증기 → 전문가 매핑을 관리하므로, 새로운 검증을 추가하면 이 매핑을 업데이트하여 특정 전문가만 재실행하도록 만들 수 있습니다.

---

## 6. 관측성 & 이벤트

- **로그**: 모든 노드가 `logger.info/debug/warning/error`를 JSON 형태로 출력합니다. 예를 들어 `decision_maker`는 라우팅 결과와 실패 검증 목록을 로그에 남깁니다.
- **SSE 이벤트**: 상태 업데이트에 `events` 리스트를 포함시키면 LangGraph reducer가 리스트를 병합하므로, 어떤 노드에서든 `events=[{...}]` 형태로 append 할 수 있습니다.
  
  ```python
  {
      "type": "progress",
      "node": "chef",
      "status": "completed",
      "data": {"menu": "훈제연어 샐러드"}
  }
  ```
- **UI/모니터링 활용**: 프론트엔드 또는 테스트 스크립트에서 `state["events"]`를 꺼내면 각 노드의 완료 시점, 실패 알림, 최종 완료(`type: "complete"`) 등을 실시간으로 표시할 수 있습니다.

---

## 7. 확장 및 커스터마이징 가이드

1. **새 전문가/검증기 추가**
   
   - `MealPlanState`에 추천/검증 결과 필드를 추가합니다.
   - 해당 노드 파일을 `nodes/...`에 생성하고 `main_graph.py`에서 `graph.add_node` 및 엣지를 추가합니다.
   - Supervisor(Send) 노드의 `Command` 목록을 업데이트합니다.
   - 검증 결과가 재시도 로직에 영향을 주어야 한다면 `RETRY_MAPPING`과 `decision_maker` 조건을 확장합니다.

2. **상태 필드 변경**
   
   - `MealPlanState` TypedDict와 관련 Pydantic 모델(Pydantic 검증에 쓰임)을 동시에 수정해야 합니다.
   - Reducer(`Annotated[..., add]`)가 필요한 리스트 필드는 `typing.Annotated`를 사용하여 자동 병합을 지정하세요.

3. **테스트/디버깅**
   
   - `graphs/meal_planning_subgraph.py`, `validation_subgraph.py`를 사용하면 특정 단계만 떼어내어 빠르게 실험할 수 있습니다.
   - `run_example.py`에 포함된 샘플 state를 수정하여 그래프를 수동 실행할 수 있습니다.

---

## 8. 노드 빠른 참조표

| 노드                         | 파일                                         | 주요 입력                                                                    | 주요 출력                                    | 비고                    |
| -------------------------- | ------------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------- | --------------------- |
| `nutrition_calculator`     | `nodes/nutrition_calculator.py`            | `profile`                                                                | 목표/예산, 진행 초기화                            | 그래프 최초 단계             |
| `meal_planning_supervisor` | `nodes/meal_planning_supervisor.py`        | `state` 전체                                                               | `Command(Send ×3)`                       | 병렬 전문가 호출             |
| `nutritionist_agent`       | `nodes/meal_planning/nutritionist.py`      | `per_meal_targets`, `previous_validation_failures`                       | `nutritionist_recommendation`            | LLM 기반                |
| `chef_agent`               | `nodes/meal_planning/chef.py`              | `cooking_time`, `skill_level`, `recipe_search`                           | `chef_recommendation`                    | 레시피 검색 통합             |
| `budget_router`            | `nodes/meal_planning/budget_router.py`     | `state` 전체                                                               | `Command(Send budget)`                   | chef 이후 budget 순차 실행용 |
| `budget_agent`             | `nodes/meal_planning/budget.py`            | `per_meal_budget`, `chef_recommendation`                                 | `budget_recommendation`                  | Tavily 가격 검색          |
| `conflict_resolver`        | `nodes/meal_planning/conflict_resolver.py` | 전문가 추천, `per_meal_targets`                                               | `current_menu`                           | 최종 메뉴 확정              |
| `validation_supervisor`    | `nodes/validation_supervisor.py`           | `current_menu`                                                           | `Command(Send ×5)`                       | 검증 병렬 실행              |
| `nutrition_checker`        | `nodes/validation/nutrition_checker.py`    | `current_menu`, `per_meal_targets`, `retry_count`                        | `ValidationResult`                       | 허용치 완화 로직 포함          |
| `allergy_checker`          | `nodes/validation/allergy_checker.py`      | `current_menu`, `profile.restrictions`                                   | `ValidationResult`                       | 제한 없으면 자동 통과          |
| `time_checker`             | `nodes/validation/time_checker.py`         | `current_menu`, `profile.cooking_time`                                   | `ValidationResult`                       | 시간 초과 경고              |
| `health_checker`           | `nodes/validation/health_checker.py`       | `current_menu`, `profile.health_conditions`                              | `ValidationResult`                       | 당뇨/고혈압/고지혈증 검증        |
| `budget_checker`           | `nodes/validation/budget_checker.py`       | `current_menu`, `per_meal_budget`, `retry_count`                         | `ValidationResult`                       | 예산 초과 허용치 완화          |
| `validation_aggregator`    | `nodes/validation_aggregator.py`           | `validation_results`, `retry_count`                                      | `previous_validation_failures`, `events` | 실패 로그 축적              |
| `decision_maker`           | `nodes/decision_maker.py`                  | 검증 결과, 재시도 정보                                                            | `"day_iterator"` or `"retry_router"`     | 함수형 라우팅               |
| `retry_router`             | `nodes/retry_router.py`                    | `retry_count`, `validation_results`                                      | `Command(goto=…)`, 재시도 상태 갱신             | 특정 전문가 재실행            |
| `day_iterator`             | `nodes/day_iterator.py`                    | `current_menu`, `completed_meals`, `weekly_plan`, `_validation_warnings` | 진행 상태 갱신                                 | 끼니/날짜 전환              |

---

## 9. 노드별 상세 설명

각 노드가 어떤 입력을 읽고 어떤 업데이트를 반환하는지, 실패 시 어떻게 대응하는지를 보다 구체적으로 정리했습니다.

### `nutrition_calculator` (`nodes/nutrition_calculator.py`)

- **주요 책임**: `profile`을 바탕으로 BMR/TDEE를 계산하고 목표 매크로 및 끼니당 예산을 설정합니다.
- **입력**: 사용자 프로필 전 필드.
- **출력/업데이트**: `daily_targets`, `per_meal_targets`, `per_meal_budget`, 첫 끼니 정보(`current_day/type/index`), `weekly_plan`, `completed_meals`, `retry_count`, 초기 `events`.
- **오류 처리**: 계산 실패 시 로거에 에러를 남기고 예외를 올립니다(상위에서 try/except 필요).

### `meal_planning_supervisor` (`nodes/meal_planning_supervisor.py`)

- **주요 책임**: `Send` API로 세 전문가 노드를 병렬 호출합니다.
- **입력**: 전체 상태를 그대로 넘깁니다.
- **출력**: `Command(goto=[Send(...), ...])`만 반환하며, 자체 업데이트는 없습니다.
- **특징**: Supervisor 자체는 I/O가 없지만 로그로 어떤 끼니/요일을 처리 중인지 남깁니다.

### `nutritionist_agent` (`nodes/meal_planning/nutritionist.py`)

- **주요 책임**: 끼니 목표 칼로리/매크로, 건강 조건에 맞는 메뉴를 LLM으로 생성합니다.
- **입력**: `per_meal_targets`, `profile.health_conditions`, `profile.restrictions`, `previous_validation_failures`, `retry_count`.
- **출력**: `nutritionist_recommendation`, 진행 이벤트.
- **재시도 전략**: `previous_validation_failures` 중 `nutrition_checker` 실패만 추려 프롬프트에 포함하고, 재시도 회차를 명시합니다.

### `chef_agent` (`nodes/meal_planning/chef.py`)

- **주요 책임**: 조리 시간 제한, 요리 실력, 맛 요소를 고려한 메뉴 추천.
- **입력**: `profile.cooking_time`, `profile.skill_level`, `per_meal_targets`, `previous_validation_failures`, `retry_count`.
- **출력**: `chef_recommendation`, 이벤트.
- **특징**: `ENABLE_RECIPE_SEARCH`가 True이면 `recipe_search_service`에서 실제 레시피를 찾아 프롬프트에 첨부하며, `allergy/time_checker` 실패 피드백을 반영합니다.

### `budget_agent` (`nodes/meal_planning/budget.py`)

- **주요 책임**: 끼니당 예산 내에서 가성비 높은 메뉴를 제안하며, 실제 재료 가격을 조회합니다.
- **입력**: `per_meal_budget`, `per_meal_targets`, `profile.restrictions`, `previous_validation_failures`, `chef_recommendation`.
- **출력**: `budget_recommendation`, 이벤트. 추천 데이터에는 `ingredient_prices`가 포함됩니다.
- **동작**:
  - `chef_recommendation.ingredients`가 있으면 `_parse_amount_to_grams`로 수량을 정규화한 뒤 `ingredient_pricing` 서비스를 호출합니다.
  - 서비스는 **Tavily API → 로컬 캐시 → 폴백 추정** 순서로 가격 정보를 조회하며, LLM 프롬프트의 `## 재료별 실시간 가격` 섹션으로 전달됩니다.
- **재시도 전략**: 다른 검증 실패 요약을 참고용으로 프롬프트 하단에 첨부하지만 직접적인 제약 조건은 예산에 집중합니다.

### `budget_router` (`nodes/meal_planning/budget_router.py`)

- **주요 책임**: chef 실행 이후 budget 노드를 명시적으로 호출해야 할 때 사용할 수 있는 간단한 라우터.
- **입력/출력**: 현재 상태를 그대로 받아 `Command(goto=[Send("budget", state)])`를 반환합니다.
- **활용 포인트**: 특정 실험이나 서브그래프에서 budget을 순차 실행하고 싶을 때 삽입해, 셰프가 남긴 재료 정보를 확실히 활용할 수 있습니다.

### `conflict_resolver` (`nodes/meal_planning/conflict_resolver.py`)

- **주요 책임**: 전문가 추천을 통합하여 최종 `Menu`를 결정.
- **입력**: 세 전문가 추천, `current_menu`(재시도 시), `per_meal_targets`, `profile`, `per_meal_budget`.
- **출력**: `current_menu`, 이벤트.
- **특징**: 결측 추천은 이전 메뉴 정보를 `MealRecommendation`으로 재생성해 채우고, LLM에게 우선순위 규칙과 JSON 스키마를 명확히 전달합니다.

### `validation_supervisor` (`nodes/validation_supervisor.py`)

- **주요 책임**: 검증 노드 다섯 개를 병렬 수행.
- **입력**: `current_menu`, `profile`, `per_meal_targets`, `per_meal_budget`.
- **출력**: `Command(goto=[Send(...)] ×5)`.
- **특징**: Supervisor 자체는 상태 변경이 없고, 검증 개시 로그만 남깁니다.

### `nutrition_checker` (`nodes/validation/nutrition_checker.py`)

- **주요 책임**: 메뉴의 칼로리/매크로가 목표 범위 안인지 판단.
- **입력**: `current_menu`, `per_meal_targets`, `retry_count`.
- **출력**: `validation_results` 리스트에 `ValidationResult` 추가, 이벤트.
- **재시도 전략**: 재시도 3회 이상이면 허용 편차를 자동 완화하여 교착상태를 피합니다.

### `allergy_checker` (`nodes/validation/allergy_checker.py`)

- **주요 책임**: 메뉴 재료가 `profile.restrictions`를 침해하는지 검사.
- **입력**: `current_menu.ingredients`, `profile.restrictions`.
- **출력**: `validation_results`에 `ValidationResult`, 이벤트.
- **특징**: 제한 사항이 없으면 곧바로 통과하며 reason에 `"제한 사항이 없습니다."`를 기록합니다.

### `time_checker` (`nodes/validation/time_checker.py`)

- **주요 책임**: 조리 시간이 사용자 허용 범위 내인지 확인.
- **입력**: `current_menu.cooking_time_minutes`, `COOKING_TIME_LIMITS[profile.cooking_time]`.
- **출력**: `ValidationResult`, 이벤트.
- **특징**: 초과 시 초과 분량과 제한을 상세 메시지로 남겨 추후 프롬프트에 사용됩니다.

### `health_checker` (`nodes/validation/health_checker.py`)

- **주요 책임**: 프로필의 건강 조건(당뇨/고혈압/고지혈증 등)에 맞춰 당류, 나트륨, 포화지방을 검증합니다.
- **입력**: `profile.health_conditions`, `current_menu.carb_g`, `current_menu.sodium_mg`, `current_menu.fat_g`.
- **출력**: `ValidationResult`, 이벤트.
- **검증 기준** (의학 가이드라인 기반):
  - **당뇨병**: 탄수화물 ≤30g/끼 (ADA 권장)
  - **고혈압**: 나트륨 ≤2000mg/일 (WHO/대한고혈압학회)
  - **고지혈증**: 포화지방 ≤15g/일 (NCEP 권장)
- **특징**: 현재는 탄수화물/지방 수치로부터 당류/포화지방을 추정하며, 조건별 상한을 넘으면 구체적인 위반 메시지를 남깁니다. 건강 조건이 없으면 자동 통과합니다.

### `budget_checker` (`nodes/validation/budget_checker.py`)

- **주요 책임**: 메뉴 예상 비용(`current_menu.estimated_cost`)이 예산 허용 범위 내인지 검증합니다.
- **입력**: `per_meal_budget`, `current_menu.estimated_cost`, `retry_count`.
- **출력**: `ValidationResult`, 이벤트.
- **특징**: 재시도 횟수에 따라 허용 오버비율이 10%→15%로 완화되는 Progressive Relaxation을 적용합니다.

### `validation_aggregator` (`nodes/validation_aggregator.py`)

- **주요 책임**: 병렬 검증 결과 요약, 실패 정보를 `previous_validation_failures`로 변환.
- **입력**: `validation_results`, `retry_count`, `current_menu`.
- **출력**: `previous_validation_failures`, 이벤트.
- **특징**: 실패한 validator 이름/이슈를 모두 로깅하며, 이후 전문가 프롬프트가 참고할 수 있는 구조화된 dict를 반환합니다.

### `decision_maker` (`nodes/decision_maker.py`)

- **주요 책임**: 다음 단계가 재시도인지 진행인지 결정.
- **입력**: `validation_results`, `retry_count`, `max_retries`, `current_menu`.
- **출력**: `"retry_router"` 또는 `"day_iterator"` 문자열.
- **특징**: 재시도 한계에 도달하면 `_validation_warnings`에 실패 메시지를 저장해 `day_iterator`로 전달합니다.

### `retry_router` (`nodes/retry_router.py`)

- **주요 책임**: 재시도 대상 노드를 라우팅하고 상태를 초기화.
- **입력**: `retry_count`, `validation_results`.
- **출력**: `Command(goto=다음 노드, update=상태 변경)`.
- **로직 요약**: 첫 실패 시 `RETRY_MAPPING`에 따라 특정 전문가만 재실행, 이후에는 전체 재실행. 해당 전문가의 추천만 `None`으로 초기화하여 LLM 호출을 최소화합니다.

### `day_iterator` (`nodes/day_iterator.py`)

- **주요 책임**: 확정된 메뉴를 누적/요약하고 다음 끼니 혹은 다음 날로 이동, 주간 완료 시 종료.
- **입력**: `current_menu`, `completed_meals`, `weekly_plan`, `_validation_warnings`, `profile`, `current_day`, `current_meal_index`.
- **출력**: 다음 끼니/날짜를 위한 상태 업데이트 또는 최종 `weekly_plan`과 완료 이벤트.
- **특징**: `_validation_warnings`를 `current_menu.validation_warnings`로 붙이고, 하루가 끝나면 `DailyPlan`을 생성해 `weekly_plan`에 push합니다. `meals_per_day` 또는 meal index가 유효 범위를 벗어나면 즉시 오류 이벤트를 기록하거나 마지막 끼니 타입을 폴백으로 사용합니다.

---

## 10. Progressive Relaxation 정책

시스템은 재시도 시 검증 기준을 점진적으로 완화하여 데드락을 방지합니다. 주요 완화 정책은 다음과 같습니다:

| Validator           | 초기 허용 오차           | 3회 재시도 후           | 목적              |
| ------------------- | ------------------ | ------------------ | --------------- |
| `nutrition_checker` | ±20% 칼로리, ±30% 매크로 | ±25% 칼로리, ±35% 매크로 | 데드락 방지 및 실용성 확보 |
| `budget_checker`    | +10% 예산 초과 허용      | +15% 예산 초과 허용      | 유연한 비용 조정       |
| 기타 검증기              | 고정 기준 유지           | 고정 기준 유지           | 건강/안전 기준 엄격 유지  |

**적용 로직**:

- `nutrition_checker.py:51-61`: `retry_count >= 3`일 때 허용 오차 확대
- `budget_checker.py:31-36`: `retry_count >= 3`일 때 예산 오버비율 15%로 완화
- `allergy_checker`, `time_checker`, `health_checker`: 재시도 횟수와 무관하게 동일 기준 적용

---

## 11. 요약

- `meal-planner-back/app/agents`는 **LangGraph + LLM + 검증 노드**의 조합으로 식단을 생성합니다.
- `MealPlanState`가 모든 노드 간 데이터 계약이며, **Send/Command**를 이용해 병렬 실행과 라우팅을 구현합니다.
- 실패한 검증 → 재시도 → 피드백 주입 → 경고 부착으로 이어지는 루프 덕분에 **안정적이면서도 유연한** 재시도 전략을 제공합니다.
- Progressive Relaxation 정책으로 검증 기준을 점진적으로 완화하여 실용성과 안정성을 동시에 확보합니다.
- 이 문서를 바탕으로 노드별 책임, 데이터 흐름, 재시도/검증 메커니즘을 쉽게 파악하고 필요 시 확장할 수 있습니다.
