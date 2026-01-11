# 에이전트 구조 비교 메모

## README와 백엔드 LangGraph 비교

- `README.md:22-48`에서 설명한 세 전문 에이전트(영양사·셰프·예산)와 다섯 검증자, 그리고 `Nutrition Calculator → Meal Planning Supervisor → {전문가} → Conflict Resolver → Validation Supervisor → {검증자} → Validation Aggregator → Decision Maker → Day Iterator/Retry Router` 라우팅 순서는 `meal-planner-back/app/agents/graphs/main_graph.py:50-125`에서 동일한 노드/엣지로 구현되어 있습니다.
- README가 강조한 병렬 실행 역시 실제 코드에서 LangGraph `Command(Send…)`로 구현됩니다. `meal-planner-back/app/agents/nodes/meal_planning_supervisor.py:29-33`은 세 전문가 노드를 동시에 호출하고, `meal-planner-back/app/agents/nodes/validation_supervisor.py:29-35`는 다섯 검증자를 병렬로 호출합니다.
- 그림 1의 의사결정 단계(검증 통과 시 진행, 실패 시 재시도)는 `meal-planner-back/app/agents/nodes/decision_maker.py:10-52`와 1:1로 대응합니다. 모든 검증을 통과하면 `day_iterator`로, 실패하면 `retry_router`로 이동하며 재시도 한도 도달 시 경고만 남기고 진행합니다.
- README가 설명한 날짜/끼니 반복 또한 `meal-planner-back/app/agents/graphs/main_graph.py:116-138`에서 확인됩니다. `day_iterator`는 주어진 일수만큼 `meal_planning_supervisor`를 다시 호출하다가 완료되면 `END`로 종료합니다.
- **README에 없는 보조 노드:** 백엔드에는 셰프 결과를 예산 노드로 확실히 넘기기 위한 `budget_router` (`meal-planner-back/app/agents/nodes/meal_planning/budget_router.py:10-29`)가 추가되어 있으며, 이는 재생성 서브그래프를 구성할 때(`meal-planner-back/app/agents/graphs/meal_planning_subgraph.py:30-47`) 사용됩니다.

## 식단 재생성 vs 전체 식단 생성

| 구분 | 전체 생성 (`/api/generate`) | 끼니 재생성 (`/api/regenerate-meal`) |
| --- | --- | --- |
| API 진입점 | `meal-planner-back/app/controllers/meal_plan.py:49-129` (`MealPlanRequest`) | `meal-planner-back/app/controllers/meal_plan.py:131-177` (`RegenerateMealRequest`) |
| 입력 데이터 | 목표, 활동량, 예산 등 원본 프로필 필드를 `meal-planner-back/app/models/requests.py:19-118`에서 검증 | 이미 직렬화된 `UserProfile`, 일일 영양 목표, 끼니 예산, 기존 식단 컨텍스트를 `meal-planner-back/app/models/requests.py:145-200`으로 전달 |
| 초기 상태 구성 | `stream_meal_plan`이 빈 `MealPlanState`를 만들고 `nutrition_calculator` 노드가 매크로·예산을 계산 (`meal-planner-back/app/services/stream_service.py:19-118`) | `build_regeneration_state`가 목표 끼니/요일, 끼니별 목표, 재시도 카운터, 컨텍스트를 미리 채운 상태를 반환 (`meal-planner-back/app/services/regeneration_service.py:69-172`) |
| 실행 그래프 | `get_meal_planner_graph` 전체를 실행하여 전문가 → 검증자 → 의사결정 → 날짜 반복까지 모두 수행 (`meal-planner-back/app/services/stream_service.py:119-182`) | `get_meal_planning_subgraph`만 실행하여 전문가와 Conflict Resolver까지만 돌리고 검증·의사결정·반복은 생략 (`meal-planner-back/app/services/stream_service.py:333-409`, `app/agents/graphs/meal_planning_subgraph.py:30-47`) |
| 재시도/루프 | Decision Maker와 Retry Router가 끼니당 `max_retries` 내에서 자동 재시도 후 Day Iterator로 이동 (`meal-planner-back/app/agents/nodes/decision_maker.py:10-52`) | 전문가 프롬프트에 `retry_count`가 전달되므로 부분적으로 재시도 피드백은 적용되지만, 검증 기반 루프나 Day Iterator는 실행되지 않음 |
| SSE 이벤트 | `progress`, `validation`, `retry`, `meal_complete`, 최종 `complete` 이벤트로 주간 식단 전체를 반환 (`meal-planner-back/app/services/stream_service.py:186-217`, `153-160`) | 동일한 변환기를 사용하되 `meal_complete`를 `meal_regenerate_progress`로 바꾸고 `meal_regenerate_complete` 이벤트로 단일 메뉴만 반환 (`meal-planner-back/app/services/stream_service.py:369-430`, `471-489`) |
| 재귀 한도 | `days × meals_per_day × 11`을 기준으로 동적으로 계산해 장기 플랜을 감당 (`meal-planner-back/app/services/stream_service.py:120-158`) | 단일 끼니만 처리하므로 고정 `recursion_limit=20`으로 충분 (`meal-planner-back/app/services/stream_service.py:333-352`) |
| 컨텍스트 활용 | `weekly_plan`과 `completed_meals`가 그래프 실행 중 자연스럽게 쌓이고 SSE로 전달 | 요청 바디에 `completed_meals_context`, `recently_used_recipes`, `used_ingredients`가 담겨 동일성 확보와 중복 방지에 활용 (`meal-planner-back/app/models/requests.py:149-199`) |

**핵심 차이:** 전체 생성은 모든 끼니에 대해 전문가 생성 → 검증 → 재시도 → 일자 이동을 반복하며 완전한 주간 식단과 검증 로그를 스트리밍합니다. 반면 재생성은 이미 만들어진 식단의 특정 끼니만 다시 계산하도록 상태를 고정하고, 세 전문가와 Conflict Resolver만 빠르게 돌려 새로운 메뉴 한 건을 반환하도록 설계되어 있습니다. 이 덕분에 재생성 응답 지연이 짧고, UI는 전체 계획을 다시 받지 않고도 대상 끼니만 갱신할 수 있습니다.
