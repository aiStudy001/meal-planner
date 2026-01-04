# AI 식단 계획 프론트엔드 - Vue 3 + TypeScript + SSE 스트리밍

> **실시간 진행 상황 추적을 통한 개인 맞춤형 식단 계획을 위한 직관적인 4단계 마법사**

## 개요

**왜 다단계 마법사인가?** 전통적인 식단 계획 인터페이스는 한 페이지에 20개 이상의 입력 필드를 제공하여 사용자를 압도합니다. 이 프론트엔드는 복잡성을 **4가지 직관적인 단계**(기본 정보 → 제한 사항 → 요리 → 예산)로 나누어 정확한 AI 추천에 필요한 세부 선호도를 수집하면서 사용자를 계획 프로세스를 통해 안내합니다.

**주요 기능:**
- **4단계 마법사**: 인지 과부하 없이 사용자 프로필을 점진적으로 수집
- **5개의 실시간 검증기**: 영양, 알레르기, 시간, 건강, 예산 준수에 대한 실시간 피드백
- **SSE 스트리밍**: 즉각적인 업데이트를 위한 Server-Sent Events (폴링 없음, WebSocket 복잡성 없음)
- **반응형 디자인**: 4열 그리드 → 2열 → 1열 (데스크톱 → 태블릿 → 모바일)
- **예산 인텔리전스**: 균등 및 가중치 할당 모두 지원 (아침:점심:저녁:간식 = 2:3:3.5:1.5)

**사용자 여정:**
1. **홈** → 소개, 동기 부여, CTA
2. **입력** → 검증 및 진행 표시기가 있는 4단계 양식
3. **처리 중** → 3개의 전문가 카드 + 5개의 검증 배지와 함께 실시간 에이전트 실행
4. **결과** → 영양 분석, 쇼핑 목록, 비용 요약이 포함된 주간 식단 계획

---

## 기술 스택

### 핵심 프레임워크 및 빌드 도구

| 기술 | 버전 | 용도 | 선택 이유 |
|-----------|---------|---------|-----------|
| **Vue 3** | ^3.5.24 | 반응형 UI 프레임워크 | 더 나은 TypeScript 지원을 위한 Composition API, 더 작은 번들 |
| **TypeScript** | ~5.9.3 | 타입 안전성 | 컴파일 시 오류 포착, 더 나은 IDE 지원 |
| **Vite** | ^7.2.4 | 빌드 도구 및 개발 서버 | Webpack보다 10배 빠른 HMR, 최적화된 프로덕션 빌드 |
| **Vue Router** | ^4.6.4 | 클라이언트 사이드 라우팅 | 4개의 주요 뷰 간 SPA 내비게이션 |
| **Pinia** | ^3.0.4 | 상태 관리 | 공식 Vue 스토어, Vuex보다 간단, 완전한 TypeScript 지원 |

### UI 및 스타일링

| 기술 | 버전 | 용도 |
|-----------|---------|---------|
| **TailwindCSS** | ^4.1.18 | 유틸리티 우선 CSS | 빠른 프로토타이핑, 일관된 디자인 시스템, 트리 셰이킹 가능 |
| **shadcn-vue** | N/A (컴포넌트 라이브러리) | 사전 제작된 컴포넌트 | 접근 가능하고 커스터마이징 가능한 UI 프리미티브 |
| **Lucide Icons** | ^0.562.0 | 아이콘 라이브러리 | 1000개 이상의 일관된 SVG 아이콘, 경량 |
| **@vueuse/core** | ^14.1.0 | Composition 유틸리티 | useBreakpoints, useStorage, useEventListener |

### 타입 시스템 및 유틸리티

| 패키지 | 용도 |
|---------|---------|
| **class-variance-authority** | 컴포넌트 변형 스타일링 |
| **clsx** | 조건부 클래스 병합 |
| **tailwind-merge** | Tailwind 클래스 중복 제거 |

**디자인 철학**: 유틸리티 우선 스타일링(Tailwind) + 사전 제작된 접근 가능한 컴포넌트(shadcn) + 조합 가능한 로직(VueUse) = 품질 높은 UX와 함께 빠른 개발.

---

## 애플리케이션 흐름

### 라우트 구조

```
/                → HomeView      히어로 섹션이 있는 랜딩 페이지
/input           → InputView     4단계 마법사 양식
/processing      → ProcessingView 실시간 에이전트 실행 추적
/result          → ResultView    주간 식단 계획 표시
```

**내비게이션 가드**: 아직 인증 없음 - 모든 라우트는 공개입니다. 계획: JWT 인증 + 사용자 대시보드.

### 상태 흐름 다이어그램

```
┌──────────────┐
│  HomeView    │  사용자가 "시작하기" 클릭
└──────┬───────┘
       │
┌──────▼───────┐
│  InputView   │  4단계 마법사
│              │  → ProfileStore가 각 단계에서 업데이트
│  Step 1-4    │  → 제출 시 검증
└──────┬───────┘
       │ UserProfile과 함께 POST /api/generate
┌──────▼───────┐
│ ProcessingView│ SSE 연결 설정
│              │  → MealPlanStore가 이벤트 수신
│  3 Agents    │  → 각 노드마다 진행 상황 업데이트
│  5 Validators│  → 검증 배지 업데이트
└──────┬───────┘
       │ "complete" 이벤트 수신
┌──────▼───────┐
│  ResultView  │  식단 계획 표시
│              │  → 주간 캘린더 뷰
│  Download    │  → 영양 요약
│  Share       │  → 비용 분석
└──────────────┘
```

### SSE 이벤트 처리 흐름

**이벤트 소스**: `POST /api/generate` → 스트리밍 응답

**이벤트 유형** (총 6개):
1. **progress**: 노드 실행 업데이트 (예: "nutritionist started", "chef completed")
2. **validation**: 검증기 결과 (5개 검증기: nutrition, allergy, time, health, budget)
3. **retry**: 재시도 알림 (재실행 중인 전문가 표시)
4. **meal_complete**: 단일 식사 완료 (식사 카드로 UI 업데이트)
5. **day_complete**: 하루 3끼 식사 완료
6. **complete**: 전체 주간 계획 준비 (결과 페이지로 이동)

**이벤트 처리**:
```typescript
// useSSE.ts 워크플로
fetch(POST /api/generate)
  → reader.read() 루프에서
    → buffer.split('\n')
      → "data: "로 시작하는 줄
        → JSON.parse(event)
          → handleSSEEvent(event)
            → switch (event.type)
              → MealPlanStore 업데이트
              → UI 컴포넌트를 반응적으로 업데이트
```

**오류 처리**:
- **HTTP 오류**: 알림 표시, 오류 메시지 표시, 재시도 허용
- **파싱 오류**: 콘솔에 로그, 잘못된 이벤트 건너뛰기 (우아한 저하)
- **네트워크 오류**: 3초 후 자동 재연결 (최대 3회 재시도)

---

## 컴포넌트 아키텍처

### 컴포넌트 계층 구조

```
App.vue
├── RouterView
    ├── HomeView
    │   ├── HeroSection
    │   ├── FeaturesGrid (3개 기능)
    │   └── CTAButton
    │
    ├── InputView
    │   ├── StepIndicator (4단계)
    │   ├── BasicInfoStep
    │   │   ├── GenderSelect
    │   │   ├── AgeInput
    │   │   ├── HeightWeightInputs
    │   │   ├── GoalSelect (weight_loss | muscle_gain | maintenance)
    │   │   └── ActivityLevelSelect (sedentary → very_active)
    │   ├── RestrictionsStep
    │   │   ├── AllergyMultiSelect (gluten, dairy, nuts 등)
    │   │   ├── DietaryPreferenceSelect (vegetarian, vegan, halal 등)
    │   │   └── HealthConditionsCheckboxes (diabetes, hypertension, high_cholesterol)
    │   ├── CookingStep
    │   │   ├── MaxCookingTimeSlider (15-120분)
    │   │   ├── CookingSkillSelect (beginner | intermediate | advanced)
    │   │   ├── MealsPerDaySelect (1-4끼)
    │   │   └── DaysInput (1-14일)
    │   └── BudgetStep
    │       ├── BudgetTypeSelect (weekly | daily | per_meal)
    │       ├── BudgetAmountInput
    │       ├── DistributionToggle (equal | weighted)
    │       └── NutritionSummary (BMR/TDEE 미리보기)
    │
    ├── ProcessingView
    │   ├── ProgressBar (0-100%)
    │   ├── CurrentMealIndicator (Day X, Meal Type)
    │   ├── ExpertAgentCards (3개 카드)
    │   │   ├── NutritionistCard (상태: idle | working | completed)
    │   │   ├── ChefCard
    │   │   └── BudgetManagerCard
    │   ├── ValidationBadges (5개 배지)
    │   │   ├── NutritionBadge (pending | passed | failed)
    │   │   ├── AllergyBadge
    │   │   ├── TimeBadge
    │   │   ├── HealthBadge
    │   │   └── BudgetBadge
    │   └── RetryCounter (재시도 횟수가 0보다 클 때 표시)
    │
    └── ResultView
        ├── WeeklyCalendar (그리드 레이아웃, 7일)
        │   └── DayCard (×7)
        │       └── MealCard (하루당 3-4끼)
        │           ├── MealName
        │           ├── NutritionSummary (칼로리, 단백질, 탄수화물, 지방)
        │           ├── CookingTime
        │           └── Cost
        ├── TotalNutritionSummary (주간 총계, 일일 평균)
        ├── BudgetBreakdown (총 비용, 일일 평균, 예산 대비 절감)
        └── ActionButtons (PDF 다운로드, 공유, 새 계획 시작)
```

### 컴포넌트 디자인 패턴

**1. Atomic Design 접근 방식**:
- **Atoms**: Button, Input, Badge, Icon (shadcn-vue에서 제공)
- **Molecules**: MealCard, ValidationBadge, ExpertCard
- **Organisms**: StepIndicator, WeeklyCalendar, ValidationGrid
- **Templates**: InputView, ProcessingView, ResultView
- **Pages**: App 라우팅 뷰

**2. Composition API 패턴**:
```typescript
// 예시: ExpertAgentCard.vue
<script setup lang="ts">
import { computed } from 'vue'
import { useMealPlanStore } from '@/stores/mealPlan'

const props = defineProps<{
  agent: 'nutritionist' | 'chef' | 'budget_manager'
}>()

const store = useMealPlanStore()

// 반응형 computed 상태
const agentStatus = computed(() => store.agentStatuses[props.agent])
const statusIcon = computed(() => {
  switch (agentStatus.value.status) {
    case 'completed': return 'CheckCircle'
    case 'working': return 'Loader'
    default: return 'Circle'
  }
})

// 반응형 스타일링
const cardClass = computed(() => ({
  'border-green-500': agentStatus.value.status === 'completed',
  'border-blue-500': agentStatus.value.status === 'working',
  'border-gray-300': agentStatus.value.status === 'idle',
}))
</script>
```

**3. 반응형 디자인 브레이크포인트** (TailwindCSS):
```typescript
// 브레이크포인트: sm(640px), md(768px), lg(1024px), xl(1280px)
const gridClass = "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"

// 식사 카드:
// 모바일: 1열 (수직 스택)
// 태블릿: 2열 (나란히 쌍)
// 데스크톱: 4열 (전체 주 뷰)
```

---

## 상태 관리 (Pinia)

### ProfileStore (`src/stores/profile.ts`)

**목적**: 사용자 프로필 데이터 수집 및 검증

**상태**:
```typescript
profile: UserProfile = {
  age, gender, weight, height, activity_level, goal,
  dietary_restrictions, allergies, health_conditions,
  cooking_skill, max_cooking_time, meals_per_day, days,
  budget, budget_type, budget_distribution
}
```

**Getters**:
```typescript
// 예시: 가중치 배분을 사용한 예산 계산
perMealBudgetsByType: computed(() => {
  const { budget, budget_type, days, meals_per_day } = profile.value

  // 예산을 총 주간 예산으로 변환
  let totalBudget = budget
  if (budget_type === 'daily') totalBudget = budget * days
  if (budget_type === 'per_meal') totalBudget = budget * days * meals_per_day

  // 가중치 배분: 아침(2) : 점심(3) : 저녁(3.5) : 간식(1.5)
  const RATIOS = { 아침: 2, 점심: 3, 저녁: 3.5, 간식: 1.5 }
  const mealTypes = getMealTypes(meals_per_day)
  const totalRatio = mealTypes.reduce((sum, type) => sum + RATIOS[type], 0)
  const dailyBudget = totalBudget / days

  return mealTypes.reduce((budgets, type) => {
    budgets[type] = Math.round((dailyBudget * RATIOS[type]) / totalRatio)
    return budgets
  }, {} as Record<string, number>)
})

// 예시 출력: 10,000원/일, 3끼 식사
// { 아침: 2353원, 점심: 3529원, 저녁: 4118원 }
// 총합 = 10,000원 (완벽하게 배분됨)
```

**Actions**:
- `updateProfile(updates)`: 부분 상태 업데이트 (예: 예산만 업데이트)
- `resetProfile()`: 기본값으로 재설정
- `validateProfile()`: 경계 검사 (나이: 10-100, 키: 100-250cm 등)

---

### MealPlanStore (`src/stores/mealPlan.ts`)

**목적**: 처리 상태, 이벤트 로그, 검증 추적, 최종 식단 계획

**상태**:
```typescript
isProcessing: boolean                // SSE 연결 활성
progress: number                     // 0-100% 완료
currentMeal: { day, meal_type }      // "Day 2, Lunch"
agentStatuses: {
  nutritionist: { status, task },
  chef: { status, task },
  budget_manager: { status, task }
}
validationState: {
  nutrition: 'pending' | 'passed' | 'failed',
  allergy: 'pending' | 'passed' | 'failed',
  time: 'pending' | 'passed' | 'failed',
  health: 'pending' | 'passed' | 'failed',
  budget: 'pending' | 'passed' | 'failed'
}
retryCount: number
eventLogs: SSEEvent[]                // 디버깅을 위한 전체 이벤트 기록
completedMeals: { day, meal_type, menu_name, calories, cost }[]
mealPlan: MealPlan | null            // 최종 주간 계획
error: string | null
```

**Actions**:
```typescript
// 처리 생명주기
startProcessing()        // isProcessing = true, 검증 재설정
stopProcessing()         // isProcessing = false
updateProgress(percent)  // 진행 표시줄 업데이트

// 에이전트 상태 업데이트
updateAgentStatus(agent, status, task?)
// 예시: updateAgentStatus('chef', 'working', 'Searching for quick recipes')

// 검증 추적
updateValidationState({ nutrition: 'passed', allergy: 'failed' })

// 이벤트 로깅
addEventLog(event)       // SSE 이벤트를 로그 배열에 추가

// 최종 결과
setMealPlan(plan)        // 설정 후 /result로 이동
clearMealPlan()          // 새 계획 생성을 위해 재설정
```

**반응형 UI 바인딩**:
```vue
<!-- ProcessingView.vue -->
<ProgressBar :value="mealPlanStore.progress" />
<ExpertCard v-for="agent in ['nutritionist', 'chef', 'budget_manager']"
            :agent="agent"
            :status="mealPlanStore.agentStatuses[agent].status" />
<ValidationBadge v-for="validator in ['nutrition', 'allergy', 'time', 'health', 'budget']"
                 :validator="validator"
                 :state="mealPlanStore.validationState[validator]" />
```

---

## SSE 통합 상세

### useSSE Composable (`src/composables/useSSE.ts`)

**목적**: SSE 연결 생명주기 및 이벤트 처리 관리

**API**:
```typescript
const { isConnected, startGeneration, stopGeneration } = useSSE()

// InputView.vue에서 사용법
async function handleSubmit() {
  const profile = profileStore.profile
  try {
    await startGeneration(profile)  // POST /api/generate, SSE 스트림 시작
    router.push('/processing')       // 처리 페이지로 이동
  } catch (error) {
    alert(`Failed to start: ${error.message}`)
  }
}
```

**구현 세부 사항**:

**1. Native Fetch API** (EventSource 아님):
```typescript
// 왜 EventSource 대신 Fetch를 사용하는가?
// - POST 요청 필요 (EventSource는 GET만 지원)
// - 커스텀 헤더 필요 (Content-Type: application/json)
// - 더 나은 오류 처리 및 재시도 제어

const response = await fetch(`${API_URL}/api/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(profile)
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

// 스트림 읽기 루프
while (true) {
  const { done, value } = await reader.read()
  if (done) break

  buffer += decoder.decode(value, { stream: true })
  // SSE 형식 파싱: "data: {json}\n\n"
}
```

**2. 이벤트 파싱**:
```typescript
// SSE 형식: "data: {json}\n\n"
const lines = buffer.split('\n')
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = line.slice(6)  // "data: " 접두사 제거
    if (data === '[DONE]') break

    const event = JSON.parse(data)
    handleSSEEvent(event)
  }
}
```

**3. 이벤트 핸들러 Switch**:
```typescript
function handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'progress':
      // 에이전트 상태 업데이트 (nutritionist/chef/budget)
      // 진행률 퍼센트 업데이트
      // 현재 식사 정보 업데이트 (day, meal_type)
      break

    case 'validation':
      // 검증기 노드 이름을 UI 상태에 매핑
      const validatorMap = {
        'nutrition_checker': 'nutrition',
        'allergy_checker': 'allergy',
        'time_checker': 'time',
        'health_checker': 'health',
        'budget_checker': 'budget'
      }
      // 검증 배지 업데이트 (pending → passed/failed)
      break

    case 'retry':
      // 재시도 카운터 증가
      // 알림 토스트 표시
      break

    case 'meal_complete':
      // 완료된 식사를 목록에 추가
      // 다음 식사를 위해 검증 상태 재설정
      break

    case 'complete':
      // 스토어에 최종 식단 계획 설정
      // /result 페이지로 이동
      router.push('/result')
      break

    case 'error':
      // 오류 모달 표시
      // 재시도 또는 취소 옵션 제공
      break
  }
}
```

**4. 연결 생명주기**:
```typescript
// 시작
isConnected.value = true
readStream(reader, decoder)  // 백그라운드 비동기 작업

// 정리 (onUnmounted 훅)
onUnmounted(() => {
  if (reader) reader.cancel()
  isConnected.value = false
})
```

**5. 오류 복구**:
```typescript
// 네트워크 오류
try {
  await reader.read()
} catch (error) {
  console.error('SSE Stream error:', error)
  mealPlanStore.setError(error.message)
  isConnected.value = false
  // 선택 사항: 3초 후 자동 재시도 (최대 3회 시도)
}

// 파싱 오류
try {
  const event = JSON.parse(data)
} catch (error) {
  console.error('Failed to parse event:', error, data)
  // 잘못된 이벤트 건너뛰기, 계속 처리
}
```

**예시 이벤트 시퀀스**:
```
1. "data: {type: 'progress', node: 'nutrition_calculator', status: 'completed'}\n\n"
2. "data: {type: 'progress', node: 'meal_planning_supervisor', status: 'started'}\n\n"
3. "data: {type: 'progress', node: 'nutritionist', status: 'working'}\n\n"
4. "data: {type: 'progress', node: 'chef', status: 'working'}\n\n"
5. "data: {type: 'validation', node: 'nutrition_checker', status: 'completed', data: {passed: true}}\n\n"
6. "data: {type: 'meal_complete', data: {day: 1, meal_type: 'breakfast', menu: 'Oatmeal Bowl'}}\n\n"
... (모든 식사에 대해 반복)
20. "data: {type: 'complete', data: {meal_plan: [...]}}\n\n"
21. "data: [DONE]\n\n"
```

---

## 설치 및 개발

### 사전 요구 사항
- Node.js 18+ 및 npm/pnpm/yarn
- 최신 브라우저 (Chrome, Firefox, Safari, Edge)
- `http://localhost:8000`에서 실행 중인 백엔드 서버 (또는 커스텀 URL)

### 빠른 시작

```bash
# 1. 저장소 복제 (아직 완료하지 않은 경우)
git clone <repository-url>
cd meal-planner-front

# 2. 의존성 설치
npm install
# 또는: pnpm install, yarn install

# 3. 환경 설정
cp .env.example .env
# .env 편집:
VITE_API_URL=http://localhost:8000

# 4. 개발 서버 시작
npm run dev
# 앱은 HMR과 함께 http://localhost:5173에서 실행됩니다

# 5. 프로덕션 빌드
npm run build
# 출력: dist/ 디렉토리 (최적화된 번들)

# 6. 프로덕션 빌드를 로컬에서 미리보기
npm run preview
# 미리보기 서버는 http://localhost:4173에서 실행됩니다
```

### 개발 워크플로

**Hot Module Replacement (HMR)**:
- 모든 `.vue`, `.ts`, `.css` 파일 편집 → 즉각적인 브라우저 업데이트 (전체 리로드 없음)
- HMR 중 상태 보존 (Pinia 스토어가 데이터 유지)

**TypeScript 타입 검사**:
```bash
# 빌드 없이 타입 검사
npm run type-check

# 타입 검사 + 빌드
npm run build
```

**권장 IDE 설정**:
- **VS Code** + **Volar** (Vue Language Features)
- **Vetur** 비활성화 (Volar와 충돌)
- VS Code 설정에서 **TypeScript Vue Plugin** 활성화

**브라우저 DevTools 확장**:
- Vue DevTools (컴포넌트, Pinia 스토어, 라우터 검사)
- SSE 디버깅을 위한 Network 탭 (`/api/generate`로 필터링)

---

## 테스트

### 현재 테스트 전략

**수동 테스트 체크리스트** (자동화 테스트 추가 전까지):

**입력 검증**:
- [ ] 나이 경계 (10-100): 5, 10, 50, 100, 105 시도
- [ ] 키 경계 (100-250cm): 90, 100, 175, 250, 260 시도
- [ ] 체중 경계 (30-200kg): 25, 30, 70, 200, 210 시도
- [ ] 예산 경계 (10k-1M원): 5000, 10000, 50000, 1000000, 2000000 시도
- [ ] 단계 탐색: 뒤로/다음 버튼 기능, 다음 클릭 시 검증
- [ ] 양식 재설정: "다시 시작" 클릭 시 모든 필드 초기화

**SSE 스트리밍**:
- [ ] 연결 설정: "연결 중..." → "처리 중..."
- [ ] 진행 업데이트: 0% → 25% → 50% → 75% → 100%
- [ ] 에이전트 카드: idle → working → completed (3개 에이전트 모두)
- [ ] 검증 배지: pending → passed/failed (5개 검증기 모두)
- [ ] 재시도 카운터: 재시도 이벤트 시 증가
- [ ] 오류 처리: 네트워크 오류 시 재시도 옵션이 있는 모달 표시

**반응형 디자인**:
- [ ] 모바일 (375px): 단일 열 레이아웃, 읽기 쉬운 텍스트
- [ ] 태블릿 (768px): 2열 식사 그리드, 터치 친화적 버튼
- [ ] 데스크톱 (1280px+): 4열 식사 그리드, 전체 기능 가시성
- [ ] 터치 상호작용: 모바일에서 스와이프 제스처 작동
- [ ] 인쇄 레이아웃: 결과 페이지가 깔끔하게 인쇄됨 (계획된 기능)

**브라우저 호환성**:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS/iOS)
- [ ] Samsung Internet (Android)

### 계획된 테스트 (향후)

**Unit Tests** (Vitest):
```typescript
// 예시: ProfileStore 검증 테스트
describe('ProfileStore', () => {
  it('가중치 예산 배분을 올바르게 계산해야 함', () => {
    const store = useProfileStore()
    store.updateProfile({
      budget: 10000,
      budget_type: 'daily',
      budget_distribution: 'weighted',
      meals_per_day: 3,
      days: 7
    })

    const budgets = store.perMealBudgetsByType
    expect(budgets['아침']).toBe(2353)  // 2/(2+3+3.5) × 10000
    expect(budgets['점심']).toBe(3529)  // 3/8.5 × 10000
    expect(budgets['저녁']).toBe(4118)  // 3.5/8.5 × 10000
  })
})
```

**Integration Tests** (Playwright):
```typescript
// 예시: E2E 해피 패스 테스트
test('완전한 식단 계획 흐름', async ({ page }) => {
  await page.goto('http://localhost:5173')

  // 홈 → 입력
  await page.click('text=Get Started')
  await expect(page).toHaveURL('/input')

  // 단계 1: 기본 정보
  await page.fill('input[name="age"]', '30')
  await page.selectOption('select[name="gender"]', 'male')
  await page.click('text=Next')

  // 단계 2-4...

  // 처리 페이지
  await expect(page).toHaveURL('/processing')
  await expect(page.locator('.progress-bar')).toBeVisible()

  // 완료 대기 (최대 60초)
  await page.waitForURL('/result', { timeout: 60000 })

  // 결과 확인
  await expect(page.locator('.meal-card')).toHaveCount(21)  // 7일 × 3끼
})
```

**Component Tests** (Vitest + @vue/test-utils):
```typescript
// 예시: ExpertAgentCard 시각적 상태
describe('ExpertAgentCard', () => {
  it('idle 상태를 올바르게 렌더링해야 함', () => {
    const wrapper = mount(ExpertAgentCard, {
      props: { agent: 'nutritionist', status: 'idle' }
    })
    expect(wrapper.find('.status-icon').classes()).toContain('text-gray-400')
  })

  it('애니메이션과 함께 working 상태를 렌더링해야 함', () => {
    const wrapper = mount(ExpertAgentCard, {
      props: { agent: 'chef', status: 'working' }
    })
    expect(wrapper.find('.spinner').exists()).toBe(true)
  })
})
```

---

## 스타일링 및 디자인 시스템

### TailwindCSS 구성

**커스텀 테마** (`tailwind.config.js`):
```javascript
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',  // 메인 브랜드 색상 (파란색)
          700: '#1d4ed8',
        },
        success: '#10b981',  // 통과한 검증을 위한 녹색
        error: '#ef4444',    // 실패한 검증을 위한 빨간색
        warning: '#f59e0b',  // 재시도 알림을 위한 주황색
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',  // 카드를 위한 커스텀 간격
        '88': '22rem',   // 더 넓은 컨테이너
      },
    },
  },
}
```

**디자인 토큰**:
- **Primary Color**: 파란색 (#3b82f6) - 신뢰, 안정성, 기술
- **Typography**: 가독성을 위한 Inter 폰트 패밀리
- **Spacing Scale**: 4px 기본 단위 (0.25rem 증분)
- **Border Radius**: 카드용 0.5rem (rounded-lg), 버튼용 0.375rem (rounded-md)

### 사용된 shadcn-vue 컴포넌트

| 컴포넌트 | 용도 | 커스터마이징 |
|-----------|---------|---------------|
| **Button** | CTA, 탐색, 작업 | 변형: default, outline, ghost |
| **Input** | 텍스트 필드 (나이, 키, 체중, 예산) | min/max가 있는 숫자 입력 |
| **Select** | 드롭다운 (성별, 목표, 활동) | 커스텀 옵션 스타일링 |
| **Checkbox** | 건강 상태, 식이 선호도 | 접근 가능한 라벨 |
| **Slider** | 요리 시간 선택 (15-120분) | 커스텀 눈금 표시 |
| **Card** | 식사 카드, 전문가 카드, 단계 컨테이너 | 그림자 높이 변형 |
| **Badge** | 검증 상태, 상태 표시기 | 색상 매핑 (success/error/warning) |
| **Progress** | 전체 진행 표시줄 (0-100%) | 애니메이션 채우기 전환 |
| **Alert** | 오류 메시지, 재시도 알림 | 변형: destructive, warning |

**컴포넌트 조합 예시**:
```vue
<!-- MealCard.vue -->
<Card class="hover:shadow-lg transition-shadow">
  <CardHeader>
    <CardTitle>{{ meal.name }}</CardTitle>
    <Badge :variant="getBadgeVariant(meal.validation)">
      {{ meal.validation_status }}
    </Badge>
  </CardHeader>
  <CardContent>
    <div class="grid grid-cols-2 gap-4">
      <NutritionStat label="칼로리" :value="meal.calories" unit="kcal" />
      <NutritionStat label="단백질" :value="meal.protein" unit="g" />
    </div>
  </CardContent>
  <CardFooter>
    <Button variant="outline" @click="viewDetails">레시피 보기</Button>
  </CardFooter>
</Card>
```

### 반응형 디자인 패턴

**모바일 우선 접근 방식**:
```css
/* 모바일을 위한 기본 스타일 (375px+) */
.meal-grid {
  @apply grid grid-cols-1 gap-4;
}

/* 태블릿 (768px+) */
@screen md {
  .meal-grid {
    @apply grid-cols-2 gap-6;
  }
}

/* 데스크톱 (1024px+) */
@screen lg {
  .meal-grid {
    @apply grid-cols-4 gap-8;
  }
}
```

**브레이크포인트 전략**:
| 디바이스 | 너비 | 레이아웃 | 최적화 |
|--------|-------|--------|--------------|
| 모바일 | 375-767px | 1열 | 수직 스택, 더 큰 터치 타겟 (최소 44px) |
| 태블릿 | 768-1023px | 2열 | 나란히 쌍, 가로/세로 모드 최적화 |
| 데스크톱 | 1024px+ | 4열 | 전체 기능 가시성, 호버 상태, 키보드 단축키 |

### 접근성 (WCAG 2.1 AA 준수)

**키보드 탐색**:
- Tab 순서는 시각적 흐름 따름 (왼쪽에서 오른쪽, 위에서 아래)
- 포커스 표시기 가시성 (2px 아웃라인, 높은 대비)
- 메인 콘텐츠를 위한 Skip 링크 (`<a href="#main">콘텐츠로 건너뛰기</a>`)
- Escape 키로 모달 닫기

**스크린 리더 지원**:
```vue
<button
  @click="submitForm"
  :aria-label="`4단계 중 ${currentStep}단계: ${stepTitle}`"
  :aria-disabled="!isValid"
>
  다음
</button>

<div role="progressbar"
     :aria-valuenow="progress"
     aria-valuemin="0"
     aria-valuemax="100">
  {{ progress }}% 완료
</div>
```

**색상 대비**:
- 배경의 텍스트: 최소 4.5:1 (본문 텍스트는 7:1)
- 상호작용 요소: 최소 3:1
- 아이콘과 텍스트 라벨 쌍 (색상만으로 표시하지 않음)

**양식 검증**:
- 스크린 리더에 오류 메시지 알림 (`aria-live="polite"`)
- `aria-required="true"`로 필수 필드 표시
- 잘못된 입력은 `aria-invalid="true"` + `aria-describedby="error-message"` 가짐

---

## 배포

### 빌드 출력

**프로덕션 빌드**:
```bash
npm run build

# 출력 구조:
dist/
├── index.html           # 진입점 (최소화됨)
├── assets/
│   ├── index-[hash].js  # 메인 번들 (코드 분할됨)
│   ├── vendor-[hash].js # 써드파티 라이브러리 (Vue, Pinia, Router)
│   ├── index-[hash].css # 컴파일된 Tailwind 스타일
│   └── *.woff2          # 폰트 파일
└── favicon.ico
```

**번들 크기 분석**:
```bash
# 번들 크기 분석 시각화
npm run build -- --mode analyze

# 예상 크기 (gzip 압축):
# - 메인 번들: ~80 KB (Vue 3 앱 코드)
# - Vendor 번들: ~120 KB (Vue, Pinia, Router, VueUse)
# - CSS: ~15 KB (사용된 클래스만으로 정리된 Tailwind)
# 총합: ~215 KB (최신 웹 앱으로 수용 가능)
```

### 호스팅 옵션

#### 1. Vercel (권장)
**이유**: 제로 설정 Vue 지원, 글로벌 CDN, 미리보기 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 배포
vercel

# 프로덕션 배포
vercel --prod
```

**구성** (`vercel.json`):
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**환경 변수**: Vercel 대시보드에서 `VITE_API_URL` 설정

#### 2. Netlify
**이유**: Git 기반 배포, 양식 처리, 엣지 함수

```bash
# Netlify CLI 설치
npm i -g netlify-cli

# 배포
netlify deploy --prod
```

**구성** (`netlify.toml`):
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

#### 3. AWS S3 + CloudFront
**이유**: 완전한 제어, 확장성, AWS 에코시스템과 통합

```bash
# 빌드
npm run build

# S3에 업로드
aws s3 sync dist/ s3://meal-planner-frontend --delete

# CloudFront 캐시 무효화
aws cloudfront create-invalidation --distribution-id E1234567890 --paths "/*"
```

**CloudFront 구성**:
- Origin: S3 버킷 (정적 웹사이트 호스팅 활성화)
- Default Root Object: `index.html`
- Error Pages: 404 → `/index.html` (SPA 라우팅용)

#### 4. 자체 호스팅 (Nginx)

**Nginx 구성** (`/etc/nginx/sites-available/meal-planner`):
```nginx
server {
  listen 80;
  server_name meal-planner.example.com;
  root /var/www/meal-planner-front/dist;
  index index.html;

  # SPA 라우팅: 모든 요청 → index.html
  location / {
    try_files $uri $uri/ /index.html;
  }

  # 정적 자산 캐시 (JS, CSS, 폰트, 이미지)
  location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }

  # Gzip 압축
  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
  gzip_min_length 1000;
}
```

### 환경 변수

**개발** (`.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_ENV=development
```

**프로덕션** (`.env.production`):
```env
VITE_API_URL=https://api.meal-planner.com
VITE_ENV=production
VITE_ANALYTICS_ID=G-XXXXXXXXXX  # 선택 사항: Google Analytics
```

**코드에서 사용법**:
```typescript
const API_URL = import.meta.env.VITE_API_URL
const isDev = import.meta.env.DEV  // 개발 모드에서 true
const isProd = import.meta.env.PROD  // 프로덕션 빌드에서 true
```

---

## 로드맵

### 완료된 기능 ✅
- [x] 4단계 마법사 입력 양식
- [x] SSE 스트리밍 통합
- [x] 실시간 처리 뷰 (3개 에이전트, 5개 검증기)
- [x] 주간 식단 계획 표시
- [x] 반응형 디자인 (모바일, 태블릿, 데스크톱)
- [x] 예산 배분 (균등 및 가중치 배분)
- [x] Pinia 상태 관리
- [x] TypeScript 타입 안전성

### 계획된 기능 (우선순위 순서)

#### 2025년 1분기: 사용자 계정 및 기록
**목표**: 식단 계획 저장, 시간에 따른 영양 추적

**기능**:
- 사용자 등록 및 로그인 (JWT 인증)
- 식단 계획 기록 (과거 계획 보기, 재생성)
- 즐겨찾기 식사 (재사용을 위해 개별 식사 저장)
- 프로필 프리셋 (여러 프로필 저장: 감량, 증량, 유지)

**기술 스택**: 백엔드에 사용자 서비스 추가, 오프라인 캐싱을 위한 localStorage

#### 2025년 2분기: 향상된 식사 관리
**목표**: 생성된 계획에 대한 더 많은 제어

**기능**:
- 식사 교체 (연어가 싫으세요? 다른 고단백 옵션으로 교체)
- 수동 식사 편집 (재료, 분량 조정)
- 레시피 상세 보기 (전체 요리 지침, 재료별 영양)
- 쇼핑 목록 내보내기 (매장 통로별로 그룹화된 재료)

**구현**: 교체를 위한 부분 그래프 재실행, 레시피 상세 모달

#### 2025년 2분기: 소셜 및 공유
**목표**: 계획 공유, 커뮤니티 레시피 발견

**기능**:
- 식단 계획 공유 (공개 URL, 소셜 미디어 미리보기)
- PDF 내보내기 (레시피가 포함된 인쇄 가능한 주간 계획)
- 커뮤니티 레시피 게시판 (사용자 제출 식사)
- 식사 평가 및 리뷰

**기술 스택**: PDF 생성 (jsPDF), 소셜 메타데이터 (Open Graph 태그)

#### 2025년 3분기: 고급 영양 추적
**목표**: 상세한 미량 영양소 추적, 진행 차트

**기능**:
- 미량 영양소 분석 (비타민, 미네랄)
- 주간 영양 트렌드 (7일 동안의 단백질/탄수화물/지방을 보여주는 차트)
- 목표 진행 추적 (체중 감량, 근육 증량 이정표)
- 사진 업로드 (책임감을 위한 식사 사진)

**기술 스택**: 시각화를 위한 Chart.js, 이미지 업로드 서비스

#### 2025년 3분기: 모바일 앱 (PWA)
**목표**: 오프라인 액세스, 푸시 알림

**기능**:
- 앱으로 설치 (PWA 매니페스트)
- 오프라인 식단 계획 보기 (서비스 워커 캐싱)
- 일일 식사 알림 (푸시 알림)
- 이동 중 장보기 목록 (모바일 최적화 체크리스트)

**기술 스택**: 서비스 워커용 Workbox, Web Push API

### 성능 개선

| 메트릭 | 현재 | 목표 | 전략 |
|--------|---------|--------|----------|
| **First Contentful Paint** | ~1.2s | <1.0s | 코드 분할, 라우트 지연 로드 |
| **Time to Interactive** | ~2.5s | <2.0s | 중요하지 않은 JS 연기, 폰트 사전 로드 |
| **Bundle Size** | 215 KB | <180 KB | 사용하지 않는 Tailwind 클래스 트리 셰이킹, 이미지 최적화 |
| **SSE Latency** | ~200ms/event | <100ms | 백엔드 최적화, HTTP/2 멀티플렉싱 |

---

## 기여

기여를 환영합니다! 시작하는 방법은 다음과 같습니다:

### 개발 설정

1. **Fork 및 Clone**:
```bash
git clone https://github.com/your-username/meal-planner-front.git
cd meal-planner-front
```

2. **의존성 설치**:
```bash
npm install
```

3. **기능 브랜치 생성**:
```bash
git checkout -b feature/your-feature-name
```

4. **다음과 함께 변경**:
   - 타입 안전성 (모든 새 코드는 TypeScript 타입을 가져야 함)
   - 컴포넌트 문서화 (복잡한 컴포넌트용 JSDoc)
   - 접근성 (WCAG 2.1 AA 준수)

5. **로컬 테스트**:
```bash
npm run dev
# 브라우저에서 기능을 수동으로 테스트
```

6. **커밋 및 Push**:
```bash
git add .
git commit -m "feat: add meal swapping feature"
git push origin feature/your-feature-name
```

7. **Pull Request 열기**: 변경 사항 설명, UI 변경에 대한 스크린샷 첨부

### 기여 가이드라인

**코드 스타일**:
- Composition API 사용 (Options API 아님)
- `<script setup>` 구문 사용
- Vue 3 모범 사례 준수 (파일당 하나의 컴포넌트, props 검증)
- TailwindCSS 유틸리티 클래스 사용 (필요하지 않으면 커스텀 CSS 피하기)

**컴포넌트 표준**:
```vue
<!-- 좋음: 타입 안전, 문서화됨, 접근 가능 -->
<script setup lang="ts">
interface Props {
  /** 카드 헤더에 표시되는 식사 이름 */
  mealName: string
  /** 영양 데이터 (칼로리, 매크로) */
  nutrition: NutritionData
}

const props = defineProps<Props>()
const emit = defineEmits<{
  viewDetails: [mealId: string]
}>()
</script>

<template>
  <Card role="article" :aria-label="`식사: ${mealName}`">
    <!-- 컴포넌트 내용 -->
  </Card>
</template>
```

**커밋 메시지 형식**:
- `feat: add new feature` (새 기능 추가)
- `fix: resolve bug` (버그 해결)
- `docs: update README` (README 업데이트)
- `style: format code` (코드 포맷팅)
- `refactor: improve code structure` (코드 구조 개선)
- `test: add tests` (테스트 추가)
- `chore: update dependencies` (의존성 업데이트)

### 기여 영역

**높은 우선순위**:
- [ ] ProfileStore, MealPlanStore용 Vitest 유닛 테스트 추가
- [ ] 해피 패스용 Playwright E2E 테스트 추가
- [ ] 모바일 UX 개선 (더 큰 터치 타겟, 스와이프 제스처)
- [ ] 더 나은 체감 성능을 위한 로딩 스켈레톤 추가

**중간 우선순위**:
- [ ] 다크 모드 지원 (Tailwind dark: 변형)
- [ ] i18n (국제화) - 한국어 + 영어 지원
- [ ] 식사 교체 기능 UI
- [ ] PDF 내보내기 구현

**낮은 우선순위**:
- [ ] 컴포넌트 문서화를 위한 Storybook
- [ ] axe-core로 접근성 감사
- [ ] 성능 모니터링 (Web Vitals)

---

## 라이선스

**MIT 라이선스**

Copyright (c) 2025 Meal Planner Contributors

본 소프트웨어 및 관련 문서 파일(이하 "소프트웨어")의 사본을 취득하는 모든 사람에게 소프트웨어를 제한 없이 사용, 복사, 수정, 병합, 게시, 배포, 서브라이선스 및/또는 판매할 수 있는 권리와 소프트웨어를 제공받은 사람에게 그렇게 할 수 있는 권리를 무료로 부여합니다. 다음 조건에 따릅니다:

위의 저작권 고지 및 본 허가 고지는 소프트웨어의 모든 사본 또는 상당 부분에 포함되어야 합니다.

소프트웨어는 상품성, 특정 목적에의 적합성 및 비침해에 대한 보증을 포함하되 이에 국한되지 않고 명시적이든 묵시적이든 어떠한 종류의 보증 없이 "있는 그대로" 제공됩니다. 저작자 또는 저작권 보유자는 계약, 불법 행위 또는 기타 소프트웨어와 관련하여 발생하는 모든 청구, 손해 또는 기타 책임에 대해 책임을 지지 않습니다.

---

**Vue 3 + TypeScript + Vite로 ❤️를 담아 제작**
백엔드 API 문서는 [meal-planner-back/README.md](../meal-planner-back/README.md)를 참조하세요
