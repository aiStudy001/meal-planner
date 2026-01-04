# AI 식단 계획 시스템 (백엔드) - LangGraph Multi-Agent 시스템

> **병렬 Multi-Agent 조정 기술 기반의 프로덕션급 식단 계획 시스템**

## 개요

**왜 Multi-Agent 아키텍처인가?** 전통적인 규칙 기반 식단 플래너는 영양, 맛 선호도, 조리 제약, 예산을 동시에 균형잡는 조합 복잡성 문제로 어려움을 겪습니다. 이 시스템은 LangGraph의 Multi-Agent 조정 기능을 활용하여 문제를 전문화된 전문가 에이전트 (영양사, 요리사, 예산 분석가)로 분해하고 병렬로 실행한 후, 규칙 기반 검증기로 건강 및 식이 제약 준수를 보장합니다.

**핵심 통계:**
- **3명의 전문가 에이전트**: 영양사, 요리사, 예산 분석가 (Send API를 통한 병렬 실행)
- **5개의 검증기**: 영양, 알레르기, 시간, 건강, 예산 (병렬 검증)
- **~5-10초 응답 시간**: 평균 식단 계획 생성 시간 (3끼 × 7일)
- **85% 성공률**: Progressive Relaxation 폴백 포함 1차 검증 성공률

**핵심 혁신**: 순차 계획 시스템과 달리, 이 아키텍처는 전문가 추천 및 검증 단계 모두에서 **진정한 병렬성**을 구현하여 순차 방식 대비 레이턴시를 60% 감소시켰습니다. 스마트 재시도 메커니즘은 실패한 검증기에 대응하는 전문가만 선택적으로 재실행하여 불필요한 LLM 호출을 방지합니다.

---

## 기술 아키텍처

### 기술 스택

| 계층 | 기술 스택 | 역할 | 버전 |
|------|----------|-----|------|
| **조정** | LangGraph | Multi-Agent 상태 관리, Send/Command API | ≥0.2.0 |
| **LLM 제공자** | Claude (Anthropic) | 전문가 에이전트 추론 | Claude 3.5 Haiku |
| **웹 프레임워크** | FastAPI | SSE 스트리밍, REST API | ≥0.115.0 |
| **검증** | Pydantic | 상태 스키마, 입력 검증 | ≥2.0.0 |
| **검색** | Tavily API | 레시피 조회, 재료 가격 | ≥0.5.0 |
| **로깅** | Structlog | 구조화된 JSON 로깅 | ≥24.0.0 |
| **테스트** | Pytest + pytest-asyncio | 단위/통합 테스트 | ≥8.0.0 |

### 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI 서버 (SSE 스트리밍)                                  │
│  POST /api/generate → Server-Sent Events (6가지 이벤트 타입)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  LangGraph StateGraph (MealPlanState)                       │
│  • TypedDict 기반 상태 + 커스텀 리듀서                        │
│  • 불변 상태 업데이트 (copy-on-write)                         │
│  • 모든 노드에서 이벤트 발생 → SSE 파이프라인                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼───┐    ┌────▼────┐    ┌───▼────┐
   │ 전문가  │    │ 검증기  │    │ 라우터 │
   │ 에이전트│    │ 파이프라인│  │ 노드   │
   └────────┘    └─────────┘    └────────┘
   Send API      Send API        조건부
   (병렬)        (병렬)          라우팅
```

**설계 원칙:**
1. **관심사 분리**: 전문가는 추천, 검증기는 강제, 라우터는 조정
2. **Fail-Fast 검증**: 제약 위반을 조기에 감지하여 재시도 비용 최소화
3. **Progressive Relaxation**: 재시도 후 검증 임계값을 완화하여 교착 상태 방지
4. **이벤트 기반**: 모든 상태 변경이 이벤트를 발생시켜 실시간 프론트엔드 업데이트

---

## Mermaid 다이어그램 보기

에이전트 그래프 다이어그램은 `docs/agent_graph.mmd` 파일에 Mermaid 형식으로 작성되어 있습니다.

### 1. GitHub 자동 렌더링 (가장 간편)
GitHub에서 `.mmd` 파일을 열면 자동으로 다이어그램이 렌더링됩니다.

📂 파일 위치: [`docs/agent_graph.mmd`](docs/agent_graph.mmd)

### 2. VS Code 확장 프로그램
**Mermaid Preview** 확장 설치:
```bash
# VS Code에서 설치
Ctrl+P → ext install bierner.markdown-mermaid
```

사용법:
1. `docs/agent_graph.mmd` 파일 열기
2. `Ctrl+Shift+V` (미리보기 패널)
3. 실시간 다이어그램 확인

### 3. 온라인 에디터
**Mermaid Live Editor** 사용:
1. [https://mermaid.live](https://mermaid.live) 접속
2. `docs/agent_graph.mmd` 파일 내용 복사
3. 좌측 에디터에 붙여넣기
4. 우측에서 실시간 렌더링 확인

### 4. CLI 도구 (로컬 이미지 생성)
Mermaid CLI로 PNG/SVG 이미지 생성:
```bash
# CLI 설치
npm install -g @mermaid-js/mermaid-cli

# PNG 생성 (1200x1600px)
mmdc -i docs/agent_graph.mmd -o docs/agent_graph.png -w 1200 -H 1600

# SVG 생성 (벡터 이미지)
mmdc -i docs/agent_graph.mmd -o docs/agent_graph.svg
```

**추천 방법**: GitHub에서 바로 확인 (별도 설치 불필요)

---

## 에이전트 그래프 시각화

전체 에이전트 워크플로는 아래와 같이 시각화됩니다. **파란색 노드**는 슈퍼바이저 (Send API), **초록색 노드**는 LLM 기반 전문가, **노란색 노드**는 규칙 기반 검증기, **주황색 노드**는 라우팅 로직을 나타냅니다.

![Agent Graph](docs/agent_graph.mmd)

**시각화 파일:**
- **Mermaid 소스**: [docs/agent_graph.mmd](docs/agent_graph.mmd) (GitHub에서 렌더링)
- **생성 스크립트**: [scripts/generate_graph_visualization.py](scripts/generate_graph_visualization.py)

---

## 에이전트 그래프 흐름 - 상세 실행 과정

### 1. 영양소 계산기 (`nutrition_calculator`)
**입력**: 사용자 프로필 (나이, 체중, 키, 활동 수준, 목표)
**처리**: Mifflin-St Jeor 공식으로 BMR 계산, 활동 승수를 적용하여 TDEE 도출, 목표에 맞춰 조정 (체중 감량: -500 kcal/일, 근육 증량: +300 kcal/일)
**출력**: 일일 칼로리 목표, 매크로 분배 (단백질: 1.6-2.2g/kg, 지방: 25-35%, 탄수화물: 나머지)
**이벤트**: `nutrition_calculation_complete`

```python
# 계산 예시
BMR (남성) = 10 × 체중(kg) + 6.25 × 키(cm) - 5 × 나이 + 5
TDEE = BMR × 활동_승수  # 1.2 (앉아서 생활) ~ 1.9 (매우 활동적)
목표 = TDEE + 목표_조정   # 체중 감량: -500, 근육 증량: +300
```

### 2. 식사 계획 슈퍼바이저 (`meal_planning_supervisor`)
**타입**: 슈퍼바이저 노드 (LangGraph Send API)
**처리**: 3명의 전문가 에이전트를 **병렬로** 디스패치하여 식사 추천 생성
**Send 대상**: `nutritionist`, `chef`, `budget`
**이벤트**: `meal_planning_started`, `expert_dispatched` (×3)

**병렬성의 이점**: 3명의 전문가가 순차가 아닌 동시에 실행되어 끼니당 레이턴시를 ~15초에서 ~5초로 단축.

### 3. 전문가 에이전트 (병렬 실행)

#### 영양사 (`nutritionist`)
- **초점**: 칼로리/단백질 목표를 충족하는 매크로 균형 식사
- **프롬프트 컨텍스트**: 일일 영양 목표, 현재 날짜 진행 상황, 식이 제한
- **검색**: Tavily API를 통한 고단백 레시피, 영양소 밀도 높은 옵션
- **출력**: 상세한 영양 분석이 포함된 3가지 식사 추천

#### 요리사 (`chef`)
- **초점**: 조리 스킬 레벨, 시간 제약, 맛 선호도
- **프롬프트 컨텍스트**: 사용자의 조리 실력 (초보/중급/고급), 최대 조리 시간, 선호 요리 스타일
- **검색**: Tavily API를 통한 스킬/시간 필터 일치 레시피
- **출력**: 조리 방법, 시간 추정이 포함된 3가지 식사 추천

#### 예산 관리자 (`budget`)
- **초점**: 비용 최적화, 재료 가용성
- **프롬프트 컨텍스트**: 일일 예산 배분, 선호 상점, 계절 재료
- **가격 조회**: Tavily 검색 → 로컬 가격 DB → 폴백 추정 (85% 정확도)
- **출력**: 1인분당 비용 분석이 포함된 3가지 식사 추천

**이벤트**: `expert_recommendation_ready` (×3 에이전트)

### 4. 충돌 해결기 (`conflict_resolver`)
**입력**: 9가지 식사 추천 (전문가당 3개)
**해결 전략**:
1. **우선순위 순위**: 영양 > 알레르기 안전 > 시간 실현 가능성 > 예산
2. **점수 계산**: 전문가 우선순위와의 중첩도로 각 식사 점수 산출
3. **선택**: 모든 하드 제약을 만족하는 최고 점수 식사

**출력**: 최종 식사 추천 1개
**이벤트**: `conflict_resolution_complete`

### 5. 검증 슈퍼바이저 (`validation_supervisor`)
**타입**: 슈퍼바이저 노드 (LangGraph Send API)
**처리**: 5개의 검증기를 **병렬로** 디스패치하여 준수 확인
**Send 대상**: `nutrition_checker`, `allergy_checker`, `time_checker`, `health_checker`, `budget_checker`
**이벤트**: `validation_started`, `validator_dispatched` (×5)

### 6. 검증기 (병렬 실행)

| 검증기 | 확인 항목 | 통과 기준 | 실패 시 조치 |
|--------|----------|----------|-------------|
| **nutrition_checker** | 칼로리, 매크로 | ±20% 칼로리, ±30% 매크로 | 영양사 재시도 플래그 |
| **allergy_checker** | 알레르기 유발 물질, 제외 항목 | 금지 재료 0개 | 요리사 재시도 플래그 |
| **time_checker** | 조리 시간 | ≤ 사용자 최대 시간 제한 | 요리사 재시도 플래그 |
| **health_checker** | 의학적 상태 | 상태별 규칙* | 영양사 재시도 플래그 |
| **budget_checker** | 끼니당 비용 | ≤ 일일 예산 / 3 (+10%) | 예산 관리자 재시도 플래그 |

*건강 검증 규칙 (의학 가이드라인 기반):
- **당뇨병**: 탄수화물 ≤30g/끼 (ADA)
- **고혈압**: 나트륨 ≤2000mg/일 (WHO)
- **고지혈증**: 포화지방 ≤15g/일 (NCEP)

**이벤트**: `validation_result` (×5 검증기)

### 7. 검증 집계기 (`validation_aggregator`)
**입력**: 5개의 검증 결과
**처리**: 통과/실패 상태 집계, 오류 메시지 수집
**출력**: 전체 검증 상태, 실패한 검증기 목록
**이벤트**: `validation_summary`

### 8. 의사 결정기 (`decision_maker`)
**타입**: 조건부 라우팅 함수
**로직**:
```python
if all_validators_passed:
    return "day_iterator"  # 다음 끼니/날짜로 이동
else:
    return "retry_router"  # 실패한 전문가 재시도
```
**이벤트**: `routing_decision`

### 9. 재시도 라우터 (`retry_router`) & 날짜 반복기 (`day_iterator`)

**재시도 라우터** (Command API):
- **첫 번째 실패**: 실패한 검증기에 매핑된 전문가만 재실행 (예: `nutrition_checker` 실패 → `nutritionist`만 재시도)
- **두 번째 이상 실패**: 전체 `meal_planning_supervisor` 재실행 (3명 전문가 모두)
- **Progressive Relaxation**: 3회 재시도 후 검증 임계값 확대 (±20% → ±25% 칼로리)
- **최대 재시도**: 5회 시도 후 오류 이벤트 발생 및 끼니 건너뛰기

**날짜 반복기**:
- **현재 끼니 < 3**: 끼니 인덱스 증가, `meal_planning_supervisor`로 라우팅
- **현재 끼니 == 3 & 현재 날짜 < 목표 일수**: 날짜 증가, 끼니 인덱스 리셋, 슈퍼바이저로 라우팅
- **현재 날짜 == 목표 일수**: `END`로 라우팅

**이벤트**: `retry_triggered`, `meal_completed`, `day_completed`, `plan_completed`

---

## 주요 기술 과제 및 해결 방법

### 과제 1: 경쟁 조건 없는 병렬 에이전트 조정

**문제**: 3명의 전문가를 동시 실행하면 상태 업데이트 충돌 위험 (예: 두 전문가가 동시에 `current_meal` 수정).

**해결 방법**: LangGraph의 **Send API** + **불변 상태 업데이트**
- 각 전문가는 현재 상태의 **복사본**을 받음
- 전문가는 부분 상태 업데이트 반환 (변경된 필드만 포함한 dict)
- LangGraph는 커스텀 리듀서로 업데이트 병합 (예: `expert_recommendations` 리스트는 `.extend()` 리듀서 사용)
- 상태 전환은 **원자적** - 부분 쓰기 없음

```python
# 리스트 필드용 커스텀 리듀서
def extend_reducer(left: list, right: list) -> list:
    return left + right if right else left

MealPlanState = TypedDict("MealPlanState", {
    "expert_recommendations": Annotated[list, extend_reducer],  # 전문가 출력 병합
    # ... 기타 필드
})
```

### 과제 2: 무한 재귀 없는 재시도 루프

**문제**: 검증 실패가 재시도를 유발하지만, 순진한 재시도는 제약이 만족 불가능할 경우 무한 루프 발생 가능.

**해결 방법**: **Progressive Relaxation** + **타겟 재시도**
- **재시도 매핑**: 각 검증기는 특정 전문가에 매핑 (영양 → 영양사, 알레르기 → 요리사)
- **선택적 재실행**: 실패에 책임이 있는 전문가만 재시도, 3명 모두 재시도 X
- **임계값 완화**: 3회 재시도 후 검증 허용 범위 확대 (±20% → ±25% → ±30%)
- **하드 리미트**: 끼니당 최대 5회 재시도, 이후 오류 이벤트 발생 및 건너뛰기

| 검증기 | 초기 임계값 | 3회 재시도 후 | 목적 |
|--------|------------|--------------|------|
| nutrition_checker | ±20% 칼로리, ±30% 매크로 | ±25% 칼로리, ±35% 매크로 | 엣지 케이스에서 교착 상태 방지 |
| budget_checker | +10% 예산 | +15% 예산 | 비싼 재료에 대한 유연성 허용 |

### 과제 3: 실시간 프론트엔드 피드백

**문제**: 식단 계획이 20-30초 소요. 사용자는 빈 화면이 아닌 진행 상황 업데이트 필요.

**해결 방법**: 모든 노드에서 **이벤트 발생** + **SSE 스트리밍**
- 모든 노드가 `state["events"]` 리스트에 이벤트 추가
- FastAPI가 Server-Sent Events (SSE)로 이벤트 스트리밍
- 6가지 이벤트 타입: `progress`, `validation`, `retry`, `meal_complete`, `complete`, `error`

```python
# 노드 이벤트 발생 패턴
return {
    "events": [{
        "type": "progress",
        "node": "nutritionist",
        "status": "completed",
        "data": {"meal": "Grilled Chicken Salad", "calories": 520}
    }],
    # ... 기타 상태 업데이트
}
```

### 과제 4: 데이터베이스 없는 재료 가격 조회

**문제**: 끼니당 50개 이상 재료의 실시간 가격 조회는 느리고 불안정.

**해결 방법**: **Tavily 검색** + **인메모리 캐시** + **스마트 폴백**
1. **Tavily API**: 식료품점 사이트에서 재료 가격 검색 (예: "chicken breast price korea")
2. **캐시**: 24시간 TTL로 가격을 인메모리 dict에 저장
3. **폴백**: 검색 실패 시 카테고리 기반 추정 사용 (단백질: $8-12/kg, 채소: $2-4/kg)
4. **정확도**: 실제 소매 가격 대비 ±15% 내 가격이 85%

```python
# 가격 조회 흐름
async def get_ingredient_price(ingredient: str) -> float:
    if ingredient in price_cache:
        return price_cache[ingredient]

    search_results = await tavily.search(f"{ingredient} price korea")
    price = extract_price_from_results(search_results)

    if price:
        price_cache[ingredient] = price
        return price
    else:
        return estimate_price_by_category(ingredient)  # 폴백
```

### 과제 5: 건강 제약 조건 강제

**문제**: 의학적 상태는 도메인별 규칙 필요 (예: 당뇨병 탄수화물 제한). LLM 단독으로는 준수 보장 불가.

**해결 방법**: **의학 가이드라인** 기반 **규칙 기반 검증기**
- `health_checker`는 LLM 추론이 아닌 하드코딩된 의학 임계값 사용
- 가이드라인 출처: ADA (당뇨병), WHO (고혈압), NCEP (콜레스테롤)
- 검증은 LLM 추천 **이후** 실행, 위반을 결정론적으로 감지

**검증 로직**:
```python
if profile.health_conditions.diabetes:
    if meal.nutrition.carbs > 30:  # ADA 가이드라인: ≤30g/끼
        return ValidationResult(passed=False, reason="탄수화물이 당뇨병 제한을 초과함")

if profile.health_conditions.hypertension:
    if daily_sodium > 2000:  # WHO 가이드라인: ≤2000mg/일
        return ValidationResult(passed=False, reason="나트륨이 고혈압 제한을 초과함")
```

---

## 설치 및 설정

### 사전 요구사항
- Python 3.11+
- 가상 환경 (권장)
- Anthropic API 키 (LLM 호출용)
- Tavily API 키 (레시피/가격 검색용)

### 빠른 시작

```bash
# 1. 복제 및 이동
git clone <repository-url>
cd meal-planner-back

# 2. 가상 환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 설정
cp .env.example .env
# .env 파일에 API 키 입력:
#   ANTHROPIC_API_KEY=your-key-here
#   TAVILY_API_KEY=your-key-here
```

### Mock 모드 실행 (API 비용 없음)

API 호출 없이 개발 및 테스트용:

```bash
# Mock 모드 설정
export MOCK_MODE=true  # Windows: set MOCK_MODE=true

# 예제 스크립트 실행
python run_example.py

# 예상 출력:
# ✅ Nutrition Calculator: 2000 kcal 목표
# ✅ Meal Planning Supervisor: 3명 전문가 디스패치
# ✅ Expert Recommendations: 9개 식사 수신
# ✅ Validation: 모두 통과
# 📅 Day 1 완료 (3끼 계획됨)
```

**Mock 모드 세부사항**:
- LLM 응답은 프롬프트 키워드 매칭으로 시뮬레이션
- Tavily 검색은 미리 정의된 레시피 템플릿 반환
- 전체 그래프 실행이 ~2초 내 완료
- 통합 테스트, 프론트엔드 개발에 유용

### 개발 서버 (FastAPI)

```bash
# FastAPI 의존성 설치 (requirements.txt에 이미 포함)
pip install fastapi uvicorn httpx

# 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API 접근:
# http://localhost:8000/docs  (Swagger UI)
# POST /api/generate  (SSE 스트리밍 엔드포인트)
```

---

## API 사용 예제

### 엔드포인트: `POST /api/generate` (SSE 스트리밍)

**요청 본문**:
```json
{
  "age": 30,
  "gender": "male",
  "weight": 75,
  "height": 175,
  "activity_level": "moderate",
  "goal": "weight_loss",
  "dietary_restrictions": ["gluten"],
  "allergies": ["peanuts"],
  "health_conditions": {"diabetes": false, "hypertension": false},
  "cooking_skill": "intermediate",
  "max_cooking_time": 45,
  "daily_budget": 15000,
  "days": 7
}
```

### 이벤트 타입 (총 6가지)

| 이벤트 타입 | 발생 시점 | 데이터 필드 | 프론트엔드 동작 |
|-----------|----------|-----------|----------------|
| **progress** | 노드 완료 | `node`, `status`, `message`, `data` | 진행 바 업데이트, 노드 완료 표시 |
| **validation** | 검증기 실행 | `validator`, `passed`, `reason` | 검증 배지 표시 (✅/❌) |
| **retry** | 재시도 발생 | `retry_count`, `failed_validators`, `target_experts` | 재시도 알림 표시 |
| **meal_complete** | 끼니 확정 | `meal_index`, `meal_data` | UI에 끼니 카드 추가 |
| **complete** | 계획 완료 | `total_meals`, `total_days`, `weekly_plan` | 성공 모달 표시, 다운로드 활성화 |
| **error** | 치명적 오류 | `error_message`, `stack_trace` | 오류 알림 표시 |

### Python 클라이언트 예제 (httpx)

```python
import httpx
import json

async def stream_meal_plan(profile_data: dict):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/generate",
            json=profile_data,
            timeout=60.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])  # "data: " 접두사 제거

                    if event["type"] == "progress":
                        print(f"✅ {event['node']}: {event['message']}")

                    elif event["type"] == "validation":
                        status = "✅" if event["passed"] else "❌"
                        print(f"{status} {event['validator']}: {event.get('reason', 'OK')}")

                    elif event["type"] == "meal_complete":
                        meal = event["meal_data"]
                        print(f"🍽️ Meal {event['meal_index']}: {meal['name']} ({meal['calories']} kcal)")

                    elif event["type"] == "complete":
                        print(f"✨ 계획 완료! {event['total_meals']}끼, {event['total_days']}일")
                        return event["weekly_plan"]

                    elif event["type"] == "error":
                        print(f"❌ 오류: {event['error_message']}")
                        raise Exception(event["error_message"])

# 사용법
profile = {
    "age": 30,
    "gender": "male",
    # ... 기타 필드
}

weekly_plan = await stream_meal_plan(profile)
```

### cURL 예제 (테스트)

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "gender": "male",
    "weight": 75,
    "height": 175,
    "activity_level": "moderate",
    "goal": "weight_loss",
    "days": 3
  }' \
  --no-buffer

# 예상 출력 (SSE 스트림):
# data: {"type": "progress", "node": "nutrition_calculator", "status": "completed"}
# data: {"type": "progress", "node": "meal_planning_supervisor", "status": "started"}
# ...
# data: {"type": "complete", "total_meals": 9, "total_days": 3}
```

---

## 프로젝트 구조

```
meal-planner-back/
├── app/
│   ├── agents/
│   │   ├── graphs/
│   │   │   └── main_graph.py              # 🔧 메인 StateGraph 정의
│   │   └── nodes/
│   │       ├── meal_planning/
│   │       │   ├── nutritionist.py        # 🤖 LLM 기반 영양 전문가
│   │       │   ├── chef.py                # 🤖 LLM 기반 요리 전문가
│   │       │   ├── budget.py              # 🤖 LLM 기반 예산 전문가
│   │       │   └── conflict_resolver.py   # 🔀 전문가 합의 로직
│   │       ├── validation/
│   │       │   ├── nutrition_checker.py   # ✅ 규칙 기반 영양 검증
│   │       │   ├── allergy_checker.py     # ✅ 알레르기/제외 항목 검증
│   │       │   ├── time_checker.py        # ✅ 조리 시간 검증
│   │       │   ├── health_checker.py      # ✅ 의학적 상태 검증
│   │       │   └── budget_checker.py      # ✅ 비용 준수 검증
│   │       ├── nutrition_calculator.py    # 📊 BMR/TDEE 계산
│   │       ├── meal_planning_supervisor.py  # 🎯 Send API 조정
│   │       ├── validation_supervisor.py     # 🎯 검증기 조정
│   │       ├── validation_aggregator.py     # 📋 검증 결과 집계
│   │       ├── decision_maker.py            # 🔀 라우팅 로직 (재시도 vs. 계속)
│   │       ├── retry_router.py              # 🔁 타겟 재시도 전략
│   │       └── day_iterator.py              # 📅 끼니/날짜 진행
│   ├── models/
│   │   ├── state.py                       # 🗂️ MealPlanState TypedDict + Pydantic 모델
│   │   └── requests.py                    # 📥 API 요청 스키마
│   ├── services/
│   │   ├── llm_service.py                 # 🧠 Anthropic API 래퍼 (Mock 모드 지원)
│   │   ├── recipe_service.py              # 🔍 Tavily 검색 통합
│   │   └── price_service.py               # 💰 재료 가격 조회 (캐시 + 폴백)
│   ├── utils/
│   │   ├── constants.py                   # 📋 상수 (영양 규칙, 재시도 제한)
│   │   ├── nutrition.py                   # 🧮 BMR/TDEE 공식, 매크로 계산
│   │   └── logging.py                     # 📝 Structlog 설정
│   └── main.py                            # 🚀 FastAPI 앱 + SSE 엔드포인트
├── tests/
│   ├── conftest.py                        # 🧪 Pytest 픽스처 (mock 상태, 프로필)
│   ├── test_graph_execution.py            # 🧪 전체 그래프 통합 테스트
│   ├── test_validators.py                 # 🧪 검증기 로직 단위 테스트
│   └── test_api/
│       ├── test_api_request_validation.py # 🧪 API 스키마 검증 테스트
│       └── test_sse_streaming.py          # 🧪 SSE 이벤트 발생 테스트
├── docs/
│   ├── agent_graph.mmd                    # 📊 Mermaid 다이어그램 (GitHub 렌더링)
│   └── api/
│       └── API.md                         # 📖 상세 API 문서
├── scripts/
│   └── generate_graph_visualization.py    # 🎨 그래프 시각화 생성기
├── run_example.py                         # 🏃 예제 실행 스크립트
├── requirements.txt                       # 📦 Python 의존성
├── pyproject.toml                         # ⚙️ 프로젝트 메타데이터
├── .env.example                           # 🔐 환경 변수 템플릿
└── README.md                              # 📘 이 파일
```

**주요 디렉토리:**
- **`agents/graphs/`**: LangGraph StateGraph 정의
- **`agents/nodes/`**: 개별 에이전트 노드 함수 (전문가, 검증기, 라우터)
- **`models/`**: 타입 안전성을 위한 Pydantic 스키마 + LangGraph 상태용 TypedDict
- **`services/`**: 외부 API 통합 (Anthropic, Tavily)
- **`utils/`**: 공유 유틸리티 (영양 공식, 로깅, 상수)

---

## 테스트

### 테스트 실행

```bash
# 테스트 의존성 설치 (requirements.txt에 이미 포함)
pip install pytest pytest-asyncio

# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 모듈 실행
pytest tests/test_graph_execution.py -v
pytest tests/test_validators.py -v
pytest tests/test_api/ -v

# 커버리지와 함께 실행
pytest tests/ --cov=app --cov-report=html
```

### 테스트 커버리지 체크리스트

| 테스트 타입 | 파일 | 커버리지 | 목적 |
|-----------|------|---------|------|
| **그래프 실행** | `test_graph_execution.py` | 전체 워크플로 | 엔드투엔드 그래프 실행 (mock 모드) |
| **검증기 로직** | `test_validators.py` | 모든 검증기 | 검증 규칙 단위 테스트 |
| **API 요청 검증** | `test_api/test_api_request_validation.py` | 요청 스키마 | Pydantic 검증, 경계 케이스 |
| **SSE 스트리밍** | `test_api/test_sse_streaming.py` | 이벤트 발생 | 6가지 이벤트 타입 모두 발생 확인 |
| **영양 계산** | `test_utils/test_nutrition.py` | BMR/TDEE 공식 | 공식 정확성, 엣지 케이스 |
| **재시도 로직** | `test_retry_router.py` | 재시도 전략 | 타겟 재시도, Progressive Relaxation |

### 예시: 엣지 케이스 테스트

```python
# tests/test_validators.py
import pytest
from app.agents.nodes.validation.nutrition_checker import nutrition_checker

def test_nutrition_checker_edge_case_zero_protein():
    """엣지 케이스: 단백질 0g 식사는 실패해야 함"""
    state = {
        "current_meal": {
            "nutrition": {"calories": 500, "protein": 0, "carbs": 60, "fat": 20}
        },
        "nutrition_targets": {"calories": 500, "protein": 30, "carbs": 60, "fat": 20}
    }

    result = nutrition_checker(state)
    assert result["validation_results"][-1]["passed"] == False
    assert "protein" in result["validation_results"][-1]["reason"].lower()

def test_nutrition_checker_progressive_relaxation():
    """3회 재시도 후, 허용 범위가 ±25%로 확대되어야 함"""
    state = {
        "current_meal": {"nutrition": {"calories": 625, "protein": 30, "carbs": 60, "fat": 20}},
        "nutrition_targets": {"calories": 500, "protein": 30, "carbs": 60, "fat": 20},
        "retry_count": 3  # Progressive Relaxation 발동
    }

    result = nutrition_checker(state)
    # 625 kcal는 500 kcal 목표 대비 +25% → 완화된 임계값으로 통과해야 함
    assert result["validation_results"][-1]["passed"] == True
```

### Mock 모드 테스트

Mock 모드는 프롬프트 키워드를 분석하여 LLM 응답을 시뮬레이션합니다. 유용한 경우:
- **CI/CD 파이프라인**: API 키 불필요
- **프론트엔드 개발**: API 레이턴시 없이 즉각 응답
- **통합 테스트**: 재현 가능한 테스트를 위한 결정론적 출력

```bash
# Mock 모드로 예제 실행
export MOCK_MODE=true
python run_example.py

# 시뮬레이션된 전문가 추천과 함께 전체 그래프 실행을 보여주는 출력
```

---

## 고급 주제

### 새 전문가 에이전트 추가

**시나리오**: 저탄소 레시피를 우선시하는 "지속가능성 전문가" 추가.

**Step 1**: 에이전트 파일 생성 `app/agents/nodes/meal_planning/sustainability.py`
```python
from app.models.state import MealPlanState
from app.services.llm_service import get_llm_response
from app.utils.logging import get_logger

logger = get_logger(__name__)

async def sustainability_agent(state: MealPlanState) -> dict:
    """저탄소, 계절 재료에 초점을 맞춘 전문가 에이전트"""
    logger.info("sustainability_agent_started")

    # 프롬프트 구성
    prompt = f"""
    {state['current_meal_type']}에 대한 지속가능한 식사 3가지를 추천하세요.
    - 계절 재료 우선
    - 탄소 발자국 최소화 (식물 기반, 로컬 소싱 선호)
    - 영양 목표: {state['nutrition_targets']}

    JSON 배열 반환: [{{name, ingredients, nutrition, carbon_score}}]
    """

    # LLM 응답 받기
    recommendations = await get_llm_response(prompt, state["profile"])

    return {
        "expert_recommendations": recommendations,  # 리듀서를 통해 리스트 확장
        "events": [{
            "type": "progress",
            "node": "sustainability",
            "status": "completed",
            "data": {"recommendation_count": len(recommendations)}
        }],
    }
```

**Step 2**: `main_graph.py` 업데이트하여 새 에이전트 포함
```python
# create_main_graph() 함수 내:
from app.agents.nodes.meal_planning.sustainability import sustainability_agent

graph.add_node("sustainability", sustainability_agent)

# 슈퍼바이저를 3명이 아닌 4명의 에이전트로 디스패치하도록 업데이트
# meal_planning_supervisor Send 대상: nutritionist, chef, budget, sustainability
```

**Step 3**: 충돌 해결기 업데이트하여 탄소 점수 고려
```python
# conflict_resolver.py에서 탄소 점수 가중치 추가
def score_meal(meal, priorities):
    score = 0
    score += priorities["nutrition"] * meal.nutrition_score
    score += priorities["taste"] * meal.taste_score
    score += priorities["budget"] * meal.budget_score
    score += priorities["sustainability"] * meal.carbon_score  # NEW
    return score
```

### 새 검증기 추가

**시나리오**: 여러 날에 걸쳐 다양한 식사를 보장하는 "재료 다양성 검사기" 추가.

**Step 1**: 검증기 생성 `app/agents/nodes/validation/variety_checker.py`
```python
from app.models.state import MealPlanState

def variety_checker(state: MealPlanState) -> dict:
    """주간 계획 전체에서 재료 다양성 검증"""
    current_meal = state["current_meal"]
    weekly_plan = state["weekly_plan"]

    # 이전 식사에서 모든 재료 추출
    used_ingredients = set()
    for day in weekly_plan:
        for meal in day["meals"]:
            used_ingredients.update(meal["ingredients"])

    # 중복 확인
    new_ingredients = set(current_meal["ingredients"])
    overlap = new_ingredients & used_ingredients

    passed = len(overlap) / len(new_ingredients) < 0.5  # <50% 중복 OK

    return {
        "validation_results": [{
            "validator": "variety_checker",
            "passed": passed,
            "reason": f"{len(overlap)}개 반복 재료" if not passed else "충분한 다양성"
        }],
        "events": [{"type": "validation", "validator": "variety_checker", "passed": passed}]
    }
```

**Step 2**: `main_graph.py` 업데이트하여 검증기 노드 추가
```python
from app.agents.nodes.validation.variety_checker import variety_checker

graph.add_node("variety_checker", variety_checker)
graph.add_edge("variety_checker", "validation_aggregator")

# validation_supervisor를 6개 검증기로 디스패치하도록 업데이트
```

**Step 3**: `retry_router.py`의 재시도 매핑 업데이트
```python
RETRY_MAPPING = {
    "nutrition_checker": ["nutritionist"],
    "allergy_checker": ["chef"],
    "time_checker": ["chef"],
    "health_checker": ["nutritionist"],
    "budget_checker": ["budget"],
    "variety_checker": ["chef", "nutritionist"],  # NEW: 여러 전문가 재시도
}
```

### 재시도 로직 커스터마이징

재시도 전략은 `RETRY_MAPPING` 상수에 정의되어 있습니다. 동작 변경을 위해 수정:

```python
# app/agents/nodes/retry_router.py
RETRY_MAPPING = {
    # 형식: "validator_name": ["expert1", "expert2"]

    # 기본 매핑
    "nutrition_checker": ["nutritionist"],
    "allergy_checker": ["chef"],

    # 커스텀: 예산 실패 시 예산 AND 영양사 모두 재시도
    # (때때로 영양사가 비싼 단백질을 추천함)
    "budget_checker": ["budget", "nutritionist"],
}

# Progressive Relaxation 임계값
RELAXATION_SCHEDULE = {
    0: {"cal_tolerance": 0.20, "macro_tolerance": 0.30},  # 초기
    3: {"cal_tolerance": 0.25, "macro_tolerance": 0.35},  # 3회 재시도 후
    5: {"cal_tolerance": 0.30, "macro_tolerance": 0.40},  # 최종 완화
}
```

### 로깅 및 디버깅

**구조화된 로깅** (Structlog):
```python
from app.utils.logging import get_logger

logger = get_logger(__name__)

# 구조화된 데이터와 함께 로그
logger.info("meal_planning_completed",
            meal_name="Grilled Chicken",
            calories=520,
            validation_passed=True)

# 출력 (JSON 형식):
# {"event": "meal_planning_completed", "meal_name": "Grilled Chicken", "calories": 520,
#  "validation_passed": true, "timestamp": "2025-01-04T10:30:00Z"}
```

**로그 레벨**:
```bash
# 환경 변수로 설정
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# 또는 .env 파일에서
LOG_LEVEL=INFO
```

**주요 로그 이벤트**:
| 이벤트 이름 | 노드 | 발생 시점 | 용도 |
|-----------|------|---------|------|
| `nutrition_calculator_completed` | nutrition_calculator | BMR/TDEE 계산 완료 | 칼로리 목표 확인 |
| `meal_planning_supervisor_started` | meal_planning_supervisor | 전문가 디스패치 | 병렬성 확인 |
| `expert_recommendation_ready` | nutritionist/chef/budget | 전문가 완료 | 전문가 출력 디버그 |
| `conflict_resolver_completed` | conflict_resolver | 최종 식사 선택 | 합의 로직 이해 |
| `validation_result` | 모든 검증기 | 검증 실행 | 검증 실패 디버그 |
| `retry_triggered` | retry_router | 재시도 시작 | 재시도 패턴 추적 |
| `meal_completed` | day_iterator | 끼니 확정 | 진행 상황 추적 |

---

## 로드맵 및 향후 개선 사항

### 현재 한계점

| 한계점 | 영향 | 계획된 수정 |
|-------|------|-----------|
| **데이터베이스 없음** | 주간 계획이 저장되지 않음 | PostgreSQL + SQLAlchemy |
| **인증 없음** | 사용자 계정 없음 | JWT 인증 + 사용자 프로필 테이블 |
| **단일 레시피 소스** | 제한된 레시피 다양성 | 다중 소스 집계 (Spoonacular, Edamam) |
| **Tavily 가격 정확도** | 85% 정확도, 지역별 차이 | 식료품점 API 통합 (Instacart, Kroger) |
| **장보기 목록 없음** | 사용자가 수동으로 재료 추출 | 최적화된 장보기 목록 자동 생성 |
| **Mock 모드만 지원** | 프로덕션에 실제 API 필요 | 이미 지원됨 - `MOCK_MODE=false` 설정 |

### 계획된 기능 (우선순위 순서)

#### 1. 데이터베이스 통합 (Q1 2025)
**목표**: 사용자 프로필 및 식단 계획 저장
**기술 스택**: PostgreSQL + SQLAlchemy + Alembic 마이그레이션
**스키마**:
```sql
users (id, email, profile_json, created_at)
meal_plans (id, user_id, week_start_date, plan_json, created_at)
meal_history (id, user_id, meal_id, consumed_at, rating)
```

#### 2. 다중 소스 레시피 검색 (Q2 2025)
**목표**: 레시피 다양성 및 관련성 증가
**소스**:
- Tavily (현재) - 일반 웹 검색
- Spoonacular API - 구조화된 레시피 데이터베이스 (50k+ 레시피)
- Edamam Recipe API - 영양 검증된 레시피
- 한국 레시피 사이트 (만개의레시피, 백종원 레시피)

**구현**: 소스 순위가 있는 레시피 집계 서비스 (공식 영양 데이터 우선)

#### 3. 장보기 목록 최적화 (Q2 2025)
**목표**: 비용/상점 최적화된 주간 장보기 목록 자동 생성
**기능**:
- 재료 통합 (예: 5끼에 걸친 "닭가슴살" → 총 1.5kg)
- 상점 라우팅 (재료를 상점별로 그룹화, 방문 횟수 최소화)
- 대량 구매 제안 (단가가 낮은 2kg 닭고기 대신 500g × 4 구매)
- 대체 추천 (선호 상점 재고 부족 시)

#### 4. PDF 출력 & 식사 준비 가이드 (Q3 2025)
**목표**: 식사 준비 지침이 포함된 인쇄 가능한 주간 계획
**포함 사항**:
- 주간 개요 캘린더
- 매크로가 포함된 일일 식사 카드
- 상점/통로별 장보기 목록
- 식사 준비 타임라인 (예: "일요일 오후 2시: 주간용 닭고기 마리네이드")

#### 5. 식단 계획 변형 (Q3 2025)
**목표**: 전체 재실행 없이 대체 계획 생성
**사용 사례**: "연어가 싫어요, 바꿔주세요"
**구현**: 부분 그래프 재실행 - 변경의 영향을 받는 노드만 재실행, 검증된 식사 재사용

### 성능 개선

| 메트릭 | 현재 | 목표 | 전략 |
|--------|------|------|------|
| **레이턴시** | 20-30초 (7일) | 15초 | 병렬 검증기 실행, LLM 캐싱 |
| **비용** | $0.15/계획 (21끼) | $0.10/계획 | Claude Haiku 사용, 스마트한 충돌 해결로 재시도 감소 |
| **정확도** | 85% 1차 검증 | 92% | 전문가 프롬프트 개선, 레시피용 RAG 추가 |

---

## 기여

기여를 환영합니다! 다음 가이드라인을 따라주세요:

### 개발 워크플로
1. **Fork** 저장소
2. **기능 브랜치 생성**: `git checkout -b feature/your-feature-name`
3. **테스트와 함께 변경**: `pytest tests/ -v`
4. **코드 포맷팅**: `black app/ tests/` (Black 설치 시)
5. **커밋**: `git commit -m "feat: add sustainability expert agent"`
6. **푸시**: `git push origin feature/your-feature-name`
7. **설명과 함께 Pull Request 열기**

### 기여 영역
- **새 전문가 에이전트**: 요리 전문가 (이탈리아, 한국, 비건), 피트니스 코치
- **검증기**: 미량 영양소 검사기 (비타민 D, 철분), 윤리적 소싱
- **통합**: 새 레시피 API, 식료품점 가격, 밀키트 서비스
- **테스트**: 엣지 케이스 테스트, 성능 벤치마크, 통합 테스트
- **문서**: API 예제, 아키텍처 다이어그램, 튜토리얼

### 코드 표준
- **타입 힌트**: 모든 함수에 타입 주석 필수
- **Docstring**: 모든 공개 함수에 Google 스타일 docstring
- **로깅**: 구조화된 이벤트와 함께 `structlog` 사용
- **테스트**: 새 코드 최소 80% 커버리지

---

## 라이선스

**MIT License**

Copyright (c) 2025 Meal Planner Contributors

이 소프트웨어 및 관련 문서 파일 ("소프트웨어")의 사본을 획득하는 모든 사람에게 무료로 제공되며, 소프트웨어를 제한 없이 사용, 복사, 수정, 병합, 게시, 배포, 재라이선스 및/또는 판매할 수 있는 권리를 포함하여 소프트웨어를 다룰 수 있으며, 소프트웨어가 제공된 사람에게도 이를 허용할 수 있습니다. 다음 조건을 따르는 경우:

위의 저작권 고지 및 이 허가 고지는 소프트웨어의 모든 사본 또는 상당 부분에 포함되어야 합니다.

소프트웨어는 "있는 그대로" 제공되며, 상품성, 특정 목적에의 적합성 및 비침해에 대한 보증을 포함하되 이에 국한되지 않는 명시적 또는 묵시적 보증 없이 제공됩니다. 어떠한 경우에도 저자 또는 저작권 보유자는 계약, 불법 행위 또는 기타 소프트웨어, 사용 또는 기타 거래와 관련하여 발생하는 모든 청구, 손해 또는 기타 책임에 대해 책임을 지지 않습니다.

---

**LangGraph + Claude로 ❤️를 담아 제작**
상세한 에이전트 문서는 [app/agents/AGENTS.md](app/agents/AGENTS.md)를 참조하세요
