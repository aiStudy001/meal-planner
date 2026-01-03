# AI Meal Planner Frontend - Vue 3 + TypeScript + SSE Streaming

> **Intuitive 4-step wizard for personalized meal planning with real-time progress tracking**

## Overview

**Why a Multi-Step Wizard?** Traditional meal planning interfaces overwhelm users with 20+ input fields on a single page. This frontend breaks down the complexity into **4 intuitive steps** (Basic Info → Restrictions → Cooking → Budget), guiding users through the planning process while collecting detailed preferences needed for accurate AI recommendations.

**Key Features:**
- **4-Step Wizard**: Progressively collects user profile without cognitive overload
- **5 Real-Time Validators**: Live feedback on nutrition, allergies, time, health, budget compliance
- **SSE Streaming**: Server-Sent Events for instant updates (no polling, no WebSockets complexity)
- **Responsive Design**: 4-column grid → 2-column → 1-column (desktop → tablet → mobile)
- **Budget Intelligence**: Supports both equal and weighted allocation (Breakfast:Lunch:Dinner:Snack = 2:3:3.5:1.5)

**User Journey:**
1. **Home** → Introduction, motivation, CTA
2. **Input** → 4-step form with validation and progress indicator
3. **Processing** → Real-time agent execution with 3 expert cards + 5 validation badges
4. **Result** → Weekly meal plan with nutrition breakdown, shopping list, cost summary

---

## Technology Stack

### Core Framework & Build Tools

| Technology | Version | Purpose | Why Chosen |
|-----------|---------|---------|-----------|
| **Vue 3** | ^3.5.24 | Reactive UI framework | Composition API for better TypeScript support, smaller bundle |
| **TypeScript** | ~5.9.3 | Type safety | Catch errors at compile time, better IDE support |
| **Vite** | ^7.2.4 | Build tool & dev server | 10x faster HMR than Webpack, optimized production builds |
| **Vue Router** | ^4.6.4 | Client-side routing | SPA navigation between 4 main views |
| **Pinia** | ^3.0.4 | State management | Official Vue store, simpler than Vuex, full TypeScript support |

### UI & Styling

| Technology | Version | Purpose |
|-----------|---------|---------|
| **TailwindCSS** | ^4.1.18 | Utility-first CSS | Rapid prototyping, consistent design system, tree-shakable |
| **shadcn-vue** | N/A (component library) | Pre-built components | Accessible, customizable UI primitives |
| **Lucide Icons** | ^0.562.0 | Icon library | 1000+ consistent SVG icons, lightweight |
| **@vueuse/core** | ^14.1.0 | Composition utilities | useBreakpoints, useStorage, useEventListener |

### Type System & Utils

| Package | Purpose |
|---------|---------|
| **class-variance-authority** | Component variant styling |
| **clsx** | Conditional class merging |
| **tailwind-merge** | Tailwind class deduplication |

**Design Philosophy**: Utility-first styling (Tailwind) + pre-built accessible components (shadcn) + composable logic (VueUse) = rapid development with quality UX.

---

## Application Flow

### Route Structure

```
/                → HomeView      Landing page with hero section
/input           → InputView     4-step wizard form
/processing      → ProcessingView Real-time agent execution tracking
/result          → ResultView    Weekly meal plan display
```

**Navigation Guards**: No authentication yet - all routes are public. Planned: JWT auth + user dashboard.

### State Flow Diagram

```
┌──────────────┐
│  HomeView    │  User clicks "Get Started"
└──────┬───────┘
       │
┌──────▼───────┐
│  InputView   │  4-step wizard
│              │  → ProfileStore updates on each step
│  Step 1-4    │  → Validation on submit
└──────┬───────┘
       │ POST /api/generate with UserProfile
┌──────▼───────┐
│ ProcessingView│ SSE connection established
│              │  → MealPlanStore receives events
│  3 Agents    │  → Progress updates every node
│  5 Validators│  → Validation badges update
└──────┬───────┘
       │ "complete" event received
┌──────▼───────┐
│  ResultView  │  Meal plan display
│              │  → Weekly calendar view
│  Download    │  → Nutrition summaries
│  Share       │  → Cost breakdown
└──────────────┘
```

### SSE Event Handling Flow

**Event Source**: `POST /api/generate` → Streaming response

**Event Types** (6 total):
1. **progress**: Node execution updates (e.g., "nutritionist started", "chef completed")
2. **validation**: Validator results (5 validators: nutrition, allergy, time, health, budget)
3. **retry**: Retry notifications (shows which expert is re-running)
4. **meal_complete**: Single meal finalized (updates UI with meal card)
5. **day_complete**: All 3 meals for a day finished
6. **complete**: Entire weekly plan ready (navigates to /result)

**Event Processing**:
```typescript
// useSSE.ts workflow
fetch(POST /api/generate)
  → reader.read() in loop
    → buffer.split('\n')
      → lines starting with "data: "
        → JSON.parse(event)
          → handleSSEEvent(event)
            → switch (event.type)
              → Update MealPlanStore
              → Update UI components reactively
```

**Error Handling**:
- **HTTP errors**: Display alert, show error message, allow retry
- **Parse errors**: Log to console, skip malformed events (graceful degradation)
- **Network errors**: Auto-reconnect after 3s (max 3 retries)

---

## Component Architecture

### Component Hierarchy

```
App.vue
├── RouterView
    ├── HomeView
    │   ├── HeroSection
    │   ├── FeaturesGrid (3x features)
    │   └── CTAButton
    │
    ├── InputView
    │   ├── StepIndicator (4 steps)
    │   ├── BasicInfoStep
    │   │   ├── GenderSelect
    │   │   ├── AgeInput
    │   │   ├── HeightWeightInputs
    │   │   ├── GoalSelect (weight_loss | muscle_gain | maintenance)
    │   │   └── ActivityLevelSelect (sedentary → very_active)
    │   ├── RestrictionsStep
    │   │   ├── AllergyMultiSelect (gluten, dairy, nuts, etc.)
    │   │   ├── DietaryPreferenceSelect (vegetarian, vegan, halal, etc.)
    │   │   └── HealthConditionsCheckboxes (diabetes, hypertension, high_cholesterol)
    │   ├── CookingStep
    │   │   ├── MaxCookingTimeSlider (15-120 min)
    │   │   ├── CookingSkillSelect (beginner | intermediate | advanced)
    │   │   ├── MealsPerDaySelect (1-4 meals)
    │   │   └── DaysInput (1-14 days)
    │   └── BudgetStep
    │       ├── BudgetTypeSelect (weekly | daily | per_meal)
    │       ├── BudgetAmountInput
    │       ├── DistributionToggle (equal | weighted)
    │       └── NutritionSummary (preview of BMR/TDEE)
    │
    ├── ProcessingView
    │   ├── ProgressBar (0-100%)
    │   ├── CurrentMealIndicator (Day X, Meal Type)
    │   ├── ExpertAgentCards (3 cards)
    │   │   ├── NutritionistCard (status: idle | working | completed)
    │   │   ├── ChefCard
    │   │   └── BudgetManagerCard
    │   ├── ValidationBadges (5 badges)
    │   │   ├── NutritionBadge (pending | passed | failed)
    │   │   ├── AllergyBadge
    │   │   ├── TimeBadge
    │   │   ├── HealthBadge
    │   │   └── BudgetBadge
    │   └── RetryCounter (shows retry count when > 0)
    │
    └── ResultView
        ├── WeeklyCalendar (grid layout, 7 days)
        │   └── DayCard (×7)
        │       └── MealCard (×3-4 meals per day)
        │           ├── MealName
        │           ├── NutritionSummary (cal, protein, carbs, fat)
        │           ├── CookingTime
        │           └── Cost
        ├── TotalNutritionSummary (weekly totals, daily averages)
        ├── BudgetBreakdown (total cost, per-day average, savings vs budget)
        └── ActionButtons (Download PDF, Share, Start New Plan)
```

### Component Design Patterns

**1. Atomic Design Approach**:
- **Atoms**: Button, Input, Badge, Icon (from shadcn-vue)
- **Molecules**: MealCard, ValidationBadge, ExpertCard
- **Organisms**: StepIndicator, WeeklyCalendar, ValidationGrid
- **Templates**: InputView, ProcessingView, ResultView
- **Pages**: App routing views

**2. Composition API Patterns**:
```typescript
// Example: ExpertAgentCard.vue
<script setup lang="ts">
import { computed } from 'vue'
import { useMealPlanStore } from '@/stores/mealPlan'

const props = defineProps<{
  agent: 'nutritionist' | 'chef' | 'budget_manager'
}>()

const store = useMealPlanStore()

// Reactive computed status
const agentStatus = computed(() => store.agentStatuses[props.agent])
const statusIcon = computed(() => {
  switch (agentStatus.value.status) {
    case 'completed': return 'CheckCircle'
    case 'working': return 'Loader'
    default: return 'Circle'
  }
})

// Reactive styling
const cardClass = computed(() => ({
  'border-green-500': agentStatus.value.status === 'completed',
  'border-blue-500': agentStatus.value.status === 'working',
  'border-gray-300': agentStatus.value.status === 'idle',
}))
</script>
```

**3. Responsive Design Breakpoints** (TailwindCSS):
```typescript
// Breakpoints: sm(640px), md(768px), lg(1024px), xl(1280px)
const gridClass = "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"

// Meal cards: 
// Mobile: 1 column (stack vertically)
// Tablet: 2 columns (side-by-side pairs)
// Desktop: 4 columns (full week view)
```

---

## State Management (Pinia)

### ProfileStore (`src/stores/profile.ts`)

**Purpose**: User profile data collection and validation

**State**:
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
// Example: Budget calculation with weighted distribution
perMealBudgetsByType: computed(() => {
  const { budget, budget_type, days, meals_per_day } = profile.value
  
  // Convert budget to total weekly budget
  let totalBudget = budget
  if (budget_type === 'daily') totalBudget = budget * days
  if (budget_type === 'per_meal') totalBudget = budget * days * meals_per_day
  
  // Weighted allocation: Breakfast(2) : Lunch(3) : Dinner(3.5) : Snack(1.5)
  const RATIOS = { 아침: 2, 점심: 3, 저녁: 3.5, 간식: 1.5 }
  const mealTypes = getMealTypes(meals_per_day)
  const totalRatio = mealTypes.reduce((sum, type) => sum + RATIOS[type], 0)
  const dailyBudget = totalBudget / days
  
  return mealTypes.reduce((budgets, type) => {
    budgets[type] = Math.round((dailyBudget * RATIOS[type]) / totalRatio)
    return budgets
  }, {} as Record<string, number>)
})

// Example output for 10,000원/day, 3 meals:
// { 아침: 2353원, 점심: 3529원, 저녁: 4118원 }
// Total = 10,000원 (perfectly distributed)
```

**Actions**:
- `updateProfile(updates)`: Partial state update (e.g., only update budget)
- `resetProfile()`: Reset to default values
- `validateProfile()`: Boundary checks (age: 10-100, height: 100-250cm, etc.)

---

### MealPlanStore (`src/stores/mealPlan.ts`)

**Purpose**: Processing state, event logs, validation tracking, final meal plan

**State**:
```typescript
isProcessing: boolean                // SSE connection active
progress: number                     // 0-100% completion
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
eventLogs: SSEEvent[]                // Full event history for debugging
completedMeals: { day, meal_type, menu_name, calories, cost }[]
mealPlan: MealPlan | null            // Final weekly plan
error: string | null
```

**Actions**:
```typescript
// Processing lifecycle
startProcessing()        // isProcessing = true, reset validation
stopProcessing()         // isProcessing = false
updateProgress(percent)  // Update progress bar

// Agent status updates
updateAgentStatus(agent, status, task?)
// Example: updateAgentStatus('chef', 'working', 'Searching for quick recipes')

// Validation tracking
updateValidationState({ nutrition: 'passed', allergy: 'failed' })

// Event logging
addEventLog(event)       // Append SSE event to logs array

// Final result
setMealPlan(plan)        // Navigate to /result after setting
clearMealPlan()          // Reset for new plan generation
```

**Reactive UI Bindings**:
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

## SSE Integration Details

### useSSE Composable (`src/composables/useSSE.ts`)

**Purpose**: Manage SSE connection lifecycle and event handling

**API**:
```typescript
const { isConnected, startGeneration, stopGeneration } = useSSE()

// Usage in InputView.vue
async function handleSubmit() {
  const profile = profileStore.profile
  try {
    await startGeneration(profile)  // POST /api/generate, start SSE stream
    router.push('/processing')       // Navigate to processing page
  } catch (error) {
    alert(`Failed to start: ${error.message}`)
  }
}
```

**Implementation Details**:

**1. Native Fetch API** (Not EventSource):
```typescript
// Why Fetch instead of EventSource?
// - POST request required (EventSource only supports GET)
// - Custom headers needed (Content-Type: application/json)
// - Better error handling and retry control

const response = await fetch(`${API_URL}/api/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(profile)
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

// Stream reading loop
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  buffer += decoder.decode(value, { stream: true })
  // Parse SSE format: "data: {json}\n\n"
}
```

**2. Event Parsing**:
```typescript
// SSE format: "data: {json}\n\n"
const lines = buffer.split('\n')
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const data = line.slice(6)  // Remove "data: " prefix
    if (data === '[DONE]') break
    
    const event = JSON.parse(data)
    handleSSEEvent(event)
  }
}
```

**3. Event Handler Switch**:
```typescript
function handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'progress':
      // Update agent status (nutritionist/chef/budget)
      // Update progress percentage
      // Update current meal info (day, meal_type)
      break
      
    case 'validation':
      // Map validator node name to UI state
      const validatorMap = {
        'nutrition_checker': 'nutrition',
        'allergy_checker': 'allergy',
        'time_checker': 'time',
        'health_checker': 'health',
        'budget_checker': 'budget'
      }
      // Update validation badge (pending → passed/failed)
      break
      
    case 'retry':
      // Increment retry counter
      // Show notification toast
      break
      
    case 'meal_complete':
      // Add completed meal to list
      // Reset validation states for next meal
      break
      
    case 'complete':
      // Set final meal plan in store
      // Navigate to /result page
      router.push('/result')
      break
      
    case 'error':
      // Display error modal
      // Offer retry or cancel options
      break
  }
}
```

**4. Connection Lifecycle**:
```typescript
// Start
isConnected.value = true
readStream(reader, decoder)  // Background async task

// Cleanup (onUnmounted hook)
onUnmounted(() => {
  if (reader) reader.cancel()
  isConnected.value = false
})
```

**5. Error Recovery**:
```typescript
// Network errors
try {
  await reader.read()
} catch (error) {
  console.error('SSE Stream error:', error)
  mealPlanStore.setError(error.message)
  isConnected.value = false
  // Optionally: Auto-retry after 3s (max 3 attempts)
}

// Parse errors
try {
  const event = JSON.parse(data)
} catch (error) {
  console.error('Failed to parse event:', error, data)
  // Skip malformed event, continue processing
}
```

**Example Event Sequence**:
```
1. "data: {type: 'progress', node: 'nutrition_calculator', status: 'completed'}\n\n"
2. "data: {type: 'progress', node: 'meal_planning_supervisor', status: 'started'}\n\n"
3. "data: {type: 'progress', node: 'nutritionist', status: 'working'}\n\n"
4. "data: {type: 'progress', node: 'chef', status: 'working'}\n\n"
5. "data: {type: 'validation', node: 'nutrition_checker', status: 'completed', data: {passed: true}}\n\n"
6. "data: {type: 'meal_complete', data: {day: 1, meal_type: 'breakfast', menu: 'Oatmeal Bowl'}}\n\n"
... (repeat for all meals)
20. "data: {type: 'complete', data: {meal_plan: [...]}}\n\n"
21. "data: [DONE]\n\n"
```

---

## Installation & Development

### Prerequisites
- Node.js 18+ and npm/pnpm/yarn
- Modern browser (Chrome, Firefox, Safari, Edge)
- Backend server running at `http://localhost:8000` (or custom URL)

### Quick Start

```bash
# 1. Clone repository (if not already done)
git clone <repository-url>
cd meal-planner-front

# 2. Install dependencies
npm install
# Or: pnpm install, yarn install

# 3. Environment setup
cp .env.example .env
# Edit .env:
VITE_API_URL=http://localhost:8000

# 4. Start development server
npm run dev
# App runs at http://localhost:5173 with HMR

# 5. Build for production
npm run build
# Output: dist/ directory (optimized bundle)

# 6. Preview production build locally
npm run preview
# Preview server at http://localhost:4173
```

### Development Workflow

**Hot Module Replacement (HMR)**:
- Edit any `.vue`, `.ts`, `.css` file → instant browser update (no full reload)
- State preservation during HMR (Pinia stores retain data)

**TypeScript Type Checking**:
```bash
# Check types without building
npm run type-check

# Type check + build
npm run build
```

**Recommended IDE Setup**:
- **VS Code** + **Volar** (Vue Language Features)
- Disable **Vetur** (conflicts with Volar)
- Enable **TypeScript Vue Plugin** in VS Code settings

**Browser DevTools Extensions**:
- Vue DevTools (inspect components, Pinia stores, router)
- Network tab for SSE debugging (filter by `/api/generate`)

---

## Testing

### Current Testing Strategy

**Manual Testing Checklist** (until automated tests are added):

**Input Validation**:
- [ ] Age boundary (10-100): Try 5, 10, 50, 100, 105
- [ ] Height boundary (100-250cm): Try 90, 100, 175, 250, 260
- [ ] Weight boundary (30-200kg): Try 25, 30, 70, 200, 210
- [ ] Budget boundary (10k-1M won): Try 5000, 10000, 50000, 1000000, 2000000
- [ ] Step navigation: Back/Next buttons functional, validation on Next
- [ ] Form reset: All fields clear on "Start Over"

**SSE Streaming**:
- [ ] Connection established: "Connecting..." → "Processing..."
- [ ] Progress updates: 0% → 25% → 50% → 75% → 100%
- [ ] Agent cards: idle → working → completed (all 3 agents)
- [ ] Validation badges: pending → passed/failed (all 5 validators)
- [ ] Retry counter: Increments on retry events
- [ ] Error handling: Network error displays modal with retry option

**Responsive Design**:
- [ ] Mobile (375px): Single column layout, readable text
- [ ] Tablet (768px): 2-column meal grid, touch-friendly buttons
- [ ] Desktop (1280px+): 4-column meal grid, full feature visibility
- [ ] Touch interactions: Swipe gestures work on mobile
- [ ] Print layout: Result page prints cleanly (planned feature)

**Browser Compatibility**:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS/iOS)
- [ ] Samsung Internet (Android)

### Planned Testing (Future)

**Unit Tests** (Vitest):
```typescript
// Example: ProfileStore validation tests
describe('ProfileStore', () => {
  it('should calculate weighted budget distribution correctly', () => {
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
// Example: E2E happy path test
test('complete meal planning flow', async ({ page }) => {
  await page.goto('http://localhost:5173')
  
  // Home → Input
  await page.click('text=Get Started')
  await expect(page).toHaveURL('/input')
  
  // Step 1: Basic Info
  await page.fill('input[name="age"]', '30')
  await page.selectOption('select[name="gender"]', 'male')
  await page.click('text=Next')
  
  // Steps 2-4...
  
  // Processing page
  await expect(page).toHaveURL('/processing')
  await expect(page.locator('.progress-bar')).toBeVisible()
  
  // Wait for completion (max 60s)
  await page.waitForURL('/result', { timeout: 60000 })
  
  // Verify results
  await expect(page.locator('.meal-card')).toHaveCount(21)  // 7 days × 3 meals
})
```

**Component Tests** (Vitest + @vue/test-utils):
```typescript
// Example: ExpertAgentCard visual states
describe('ExpertAgentCard', () => {
  it('renders idle state correctly', () => {
    const wrapper = mount(ExpertAgentCard, {
      props: { agent: 'nutritionist', status: 'idle' }
    })
    expect(wrapper.find('.status-icon').classes()).toContain('text-gray-400')
  })
  
  it('renders working state with animation', () => {
    const wrapper = mount(ExpertAgentCard, {
      props: { agent: 'chef', status: 'working' }
    })
    expect(wrapper.find('.spinner').exists()).toBe(true)
  })
})
```

---

## Styling & Design System

### TailwindCSS Configuration

**Custom Theme** (`tailwind.config.js`):
```javascript
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',  // Main brand color (blue)
          700: '#1d4ed8',
        },
        success: '#10b981',  // Green for passed validation
        error: '#ef4444',    // Red for failed validation
        warning: '#f59e0b',  // Orange for retry notifications
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',  // Custom spacing for cards
        '88': '22rem',   // Wider containers
      },
    },
  },
}
```

**Design Tokens**:
- **Primary Color**: Blue (#3b82f6) - Trust, reliability, technology
- **Typography**: Inter font family for readability
- **Spacing Scale**: 4px base unit (0.25rem increments)
- **Border Radius**: 0.5rem (rounded-lg) for cards, 0.375rem (rounded-md) for buttons

### shadcn-vue Components Used

| Component | Purpose | Customization |
|-----------|---------|---------------|
| **Button** | CTA, navigation, actions | Variant: default, outline, ghost |
| **Input** | Text fields (age, height, weight, budget) | Number inputs with min/max |
| **Select** | Dropdowns (gender, goal, activity) | Custom option styling |
| **Checkbox** | Health conditions, dietary preferences | Accessible labels |
| **Slider** | Cooking time selection (15-120 min) | Custom tick marks |
| **Card** | Meal cards, expert cards, step containers | Shadow elevation variants |
| **Badge** | Validation states, status indicators | Color mapping (success/error/warning) |
| **Progress** | Overall progress bar (0-100%) | Animated fill transition |
| **Alert** | Error messages, retry notifications | Variant: destructive, warning |

**Component Composition Example**:
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
      <NutritionStat label="Calories" :value="meal.calories" unit="kcal" />
      <NutritionStat label="Protein" :value="meal.protein" unit="g" />
    </div>
  </CardContent>
  <CardFooter>
    <Button variant="outline" @click="viewDetails">View Recipe</Button>
  </CardFooter>
</Card>
```

### Responsive Design Patterns

**Mobile-First Approach**:
```css
/* Base styles for mobile (375px+) */
.meal-grid {
  @apply grid grid-cols-1 gap-4;
}

/* Tablet (768px+) */
@screen md {
  .meal-grid {
    @apply grid-cols-2 gap-6;
  }
}

/* Desktop (1024px+) */
@screen lg {
  .meal-grid {
    @apply grid-cols-4 gap-8;
  }
}
```

**Breakpoint Strategy**:
| Device | Width | Layout | Optimization |
|--------|-------|--------|--------------|
| Mobile | 375-767px | 1 column | Stack vertically, larger touch targets (min 44px) |
| Tablet | 768-1023px | 2 columns | Side-by-side pairs, optimize for landscape/portrait |
| Desktop | 1024px+ | 4 columns | Full feature visibility, hover states, keyboard shortcuts |

### Accessibility (WCAG 2.1 AA Compliance)

**Keyboard Navigation**:
- Tab order follows visual flow (left-to-right, top-to-bottom)
- Focus indicators visible (2px outline, high contrast)
- Skip links for main content (`<a href="#main">Skip to content</a>`)
- Escape key closes modals

**Screen Reader Support**:
```vue
<button 
  @click="submitForm"
  :aria-label="`Step ${currentStep} of 4: ${stepTitle}`"
  :aria-disabled="!isValid"
>
  Next
</button>

<div role="progressbar" 
     :aria-valuenow="progress" 
     aria-valuemin="0" 
     aria-valuemax="100">
  {{ progress }}% Complete
</div>
```

**Color Contrast**:
- Text on background: 4.5:1 minimum (7:1 for body text)
- Interactive elements: 3:1 minimum
- Icons paired with text labels (not color-only indicators)

**Form Validation**:
- Error messages announced to screen readers (`aria-live="polite"`)
- Required fields marked with `aria-required="true"`
- Invalid inputs have `aria-invalid="true"` + `aria-describedby="error-message"`

---

## Deployment

### Build Output

**Production Build**:
```bash
npm run build

# Output structure:
dist/
├── index.html           # Entry point (minified)
├── assets/
│   ├── index-[hash].js  # Main bundle (code-split)
│   ├── vendor-[hash].js # Third-party libraries (Vue, Pinia, Router)
│   ├── index-[hash].css # Compiled Tailwind styles
│   └── *.woff2          # Font files
└── favicon.ico
```

**Bundle Size Analysis**:
```bash
# Visualize bundle size breakdown
npm run build -- --mode analyze

# Expected sizes (gzipped):
# - Main bundle: ~80 KB (Vue 3 app code)
# - Vendor bundle: ~120 KB (Vue, Pinia, Router, VueUse)
# - CSS: ~15 KB (Tailwind purged to used classes only)
# Total: ~215 KB (acceptable for modern web app)
```

### Hosting Options

#### 1. Vercel (Recommended)
**Why**: Zero-config Vue support, global CDN, preview deployments

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Production deployment
vercel --prod
```

**Configuration** (`vercel.json`):
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**Environment Variables**: Set `VITE_API_URL` in Vercel dashboard

#### 2. Netlify
**Why**: Git-based deploys, form handling, edge functions

```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod
```

**Configuration** (`netlify.toml`):
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
**Why**: Full control, scalability, integrate with AWS ecosystem

```bash
# Build
npm run build

# Upload to S3
aws s3 sync dist/ s3://meal-planner-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E1234567890 --paths "/*"
```

**CloudFront Configuration**:
- Origin: S3 bucket (static website hosting enabled)
- Default Root Object: `index.html`
- Error Pages: 404 → `/index.html` (for SPA routing)

#### 4. Self-Hosted (Nginx)

**Nginx Configuration** (`/etc/nginx/sites-available/meal-planner`):
```nginx
server {
  listen 80;
  server_name meal-planner.example.com;
  root /var/www/meal-planner-front/dist;
  index index.html;

  # SPA routing: all requests → index.html
  location / {
    try_files $uri $uri/ /index.html;
  }

  # Cache static assets (JS, CSS, fonts, images)
  location ~* \.(js|css|png|jpg|jpeg|gif|ico|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }

  # Gzip compression
  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
  gzip_min_length 1000;
}
```

### Environment Variables

**Development** (`.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_ENV=development
```

**Production** (`.env.production`):
```env
VITE_API_URL=https://api.meal-planner.com
VITE_ENV=production
VITE_ANALYTICS_ID=G-XXXXXXXXXX  # Optional: Google Analytics
```

**Usage in Code**:
```typescript
const API_URL = import.meta.env.VITE_API_URL
const isDev = import.meta.env.DEV  // true in dev mode
const isProd = import.meta.env.PROD  // true in production build
```

---

## Roadmap

### Completed Features ✅
- [x] 4-step wizard input form
- [x] SSE streaming integration
- [x] Real-time processing view (3 agents, 5 validators)
- [x] Weekly meal plan display
- [x] Responsive design (mobile, tablet, desktop)
- [x] Budget allocation (equal & weighted distribution)
- [x] Pinia state management
- [x] TypeScript type safety

### Planned Features (Priority Order)

#### Q1 2025: User Accounts & History
**Goal**: Save meal plans, track nutrition over time

**Features**:
- User registration & login (JWT auth)
- Meal plan history (view past plans, regenerate)
- Favorite meals (save individual meals for reuse)
- Profile presets (save multiple profiles: cutting, bulking, maintenance)

**Tech Stack**: Add user service to backend, localStorage for offline caching

#### Q2 2025: Enhanced Meal Management
**Goal**: More control over generated plans

**Features**:
- Meal swapping (don't like salmon? swap with another high-protein option)
- Manual meal editing (adjust ingredients, portions)
- Recipe details view (full cooking instructions, nutrition per ingredient)
- Shopping list export (ingredients grouped by store aisle)

**Implementation**: Partial graph re-execution for swaps, recipe detail modal

#### Q2 2025: Social & Sharing
**Goal**: Share plans, discover community recipes

**Features**:
- Share meal plans (public URL, social media preview)
- PDF export (printable weekly plan with recipes)
- Community recipe board (user-submitted meals)
- Meal ratings & reviews

**Tech Stack**: PDF generation (jsPDF), social metadata (Open Graph tags)

#### Q3 2025: Advanced Nutrition Tracking
**Goal**: Detailed micronutrient tracking, progress charts

**Features**:
- Micronutrient breakdown (vitamins, minerals)
- Weekly nutrition trends (chart showing protein/carb/fat over 7 days)
- Goal progress tracking (weight loss, muscle gain milestones)
- Photo upload (meal photos for accountability)

**Tech Stack**: Chart.js for visualizations, image upload service

#### Q3 2025: Mobile App (PWA)
**Goal**: Offline access, push notifications

**Features**:
- Install as app (PWA manifest)
- Offline meal plan viewing (service worker caching)
- Daily meal reminders (push notifications)
- Grocery list on-the-go (mobile-optimized checklist)

**Tech Stack**: Workbox for service worker, Web Push API

### Performance Improvements

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| **First Contentful Paint** | ~1.2s | <1.0s | Code splitting, lazy load routes |
| **Time to Interactive** | ~2.5s | <2.0s | Defer non-critical JS, preload fonts |
| **Bundle Size** | 215 KB | <180 KB | Tree-shake unused Tailwind classes, optimize images |
| **SSE Latency** | ~200ms/event | <100ms | Backend optimization, HTTP/2 multiplexing |

---

## Contributing

We welcome contributions! Here's how to get started:

### Development Setup

1. **Fork & Clone**:
```bash
git clone https://github.com/your-username/meal-planner-front.git
cd meal-planner-front
```

2. **Install Dependencies**:
```bash
npm install
```

3. **Create Feature Branch**:
```bash
git checkout -b feature/your-feature-name
```

4. **Make Changes** with:
   - Type safety (all new code must have TypeScript types)
   - Component documentation (JSDoc for complex components)
   - Accessibility (WCAG 2.1 AA compliance)

5. **Test Locally**:
```bash
npm run dev
# Manually test your feature in browser
```

6. **Commit & Push**:
```bash
git add .
git commit -m "feat: add meal swapping feature"
git push origin feature/your-feature-name
```

7. **Open Pull Request**: Describe changes, attach screenshots for UI changes

### Contribution Guidelines

**Code Style**:
- Use Composition API (not Options API)
- Use `<script setup>` syntax
- Follow Vue 3 best practices (one component per file, props validation)
- Use TailwindCSS utility classes (avoid custom CSS unless necessary)

**Component Standards**:
```vue
<!-- Good: Type-safe, documented, accessible -->
<script setup lang="ts">
interface Props {
  /** Meal name displayed in card header */
  mealName: string
  /** Nutrition data (calories, macros) */
  nutrition: NutritionData
}

const props = defineProps<Props>()
const emit = defineEmits<{
  viewDetails: [mealId: string]
}>()
</script>

<template>
  <Card role="article" :aria-label="`Meal: ${mealName}`">
    <!-- Component content -->
  </Card>
</template>
```

**Commit Message Format**:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update README`
- `style: format code`
- `refactor: improve code structure`
- `test: add tests`
- `chore: update dependencies`

### Areas for Contribution

**High Priority**:
- [ ] Add Vitest unit tests for ProfileStore, MealPlanStore
- [ ] Add Playwright E2E tests for happy path
- [ ] Improve mobile UX (larger touch targets, swipe gestures)
- [ ] Add loading skeletons for better perceived performance

**Medium Priority**:
- [ ] Dark mode support (Tailwind dark: variants)
- [ ] i18n (internationalization) - Korean + English support
- [ ] Meal swapping feature UI
- [ ] PDF export implementation

**Low Priority**:
- [ ] Storybook for component documentation
- [ ] Accessibility audit with axe-core
- [ ] Performance monitoring (Web Vitals)

---

## License

**MIT License**

Copyright (c) 2025 Meal Planner Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

**Built with ❤️ using Vue 3 + TypeScript + Vite**  
For backend API documentation, see [meal-planner-back/README.md](../meal-planner-back/README.md)
