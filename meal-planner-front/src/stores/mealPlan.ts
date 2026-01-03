import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MealPlan, ProcessingState, ValidationState, SSEEvent, AgentStatus } from '@/types'

export const useMealPlanStore = defineStore('mealPlan', () => {
  // State
  const mealPlan = ref<MealPlan | null>(null)
  const processingState = ref<ProcessingState>({
    is_processing: false,
    current_day: 0,
    current_meal: 0,
    total_progress: 0,
    validation_state: {
      nutrition: 'pending',
      allergy: 'pending',
      time: 'pending',
      health: 'pending',
      budget: 'pending',
    },
    retry_count: 0,
    event_log: [],
  })

  const agentStatuses = ref<AgentStatus[]>([
    { name: 'nutritionist', status: 'idle' },
    { name: 'chef', status: 'idle' },
    { name: 'budget_manager', status: 'idle' },
  ])

  interface CompletedMeal {
    day: number
    meal_type: string
    menu_name: string
    calories: number
    cost: number
  }

  const completedMeals = ref<CompletedMeal[]>([])

  // Getters
  const hasResult = computed(() => mealPlan.value !== null)
  const isProcessing = computed(() => processingState.value.is_processing)
  const totalProgress = computed(() => processingState.value.total_progress)
  const currentDay = computed(() => processingState.value.current_day)
  const currentMeal = computed(() => processingState.value.current_meal)
  const currentMealType = computed(() => processingState.value.current_meal_type)
  const validationState = computed(() => processingState.value.validation_state)
  const eventLog = computed(() => processingState.value.event_log)
  const hasError = computed(() => processingState.value.error !== undefined)
  const errorMessage = computed(() => processingState.value.error)

  // Validation status helpers
  const allValidationsPassed = computed(() => {
    const state = processingState.value.validation_state
    return (
      state.nutrition === 'passed' &&
      state.allergy === 'passed' &&
      state.time === 'passed' &&
      state.health === 'passed' &&
      state.budget === 'passed'
    )
  })

  const hasFailedValidation = computed(() => {
    const state = processingState.value.validation_state
    return Object.values(state).some((status) => status === 'failed')
  })

  const passedValidationsCount = computed(() => {
    const state = processingState.value.validation_state
    return Object.values(state).filter((status) => status === 'passed').length
  })

  // Actions
  function startProcessing() {
    const mealTypes = ['아침', '점심', '저녁']
    processingState.value = {
      is_processing: true,
      current_day: 1,
      current_meal: 1,
      current_meal_type: mealTypes[0],  // 첫 끼니 타입으로 초기화
      total_progress: 0,
      validation_state: {
        nutrition: 'pending',
        allergy: 'pending',
        time: 'pending',
        health: 'pending',
        budget: 'pending',
      },
      retry_count: 0,
      event_log: [],
      error: undefined,
    }

    // Reset agent statuses
    agentStatuses.value = [
      { name: 'nutritionist', status: 'idle' },
      { name: 'chef', status: 'idle' },
      { name: 'budget_manager', status: 'idle' },
    ]
  }

  function updateProgress(progress: number) {
    processingState.value.total_progress = Math.min(100, Math.max(0, progress))
  }

  function updateCurrentMeal(day: number, meal: number, mealType?: string) {
    processingState.value.current_day = day
    processingState.value.current_meal = meal
    if (mealType) {
      processingState.value.current_meal_type = mealType
    }
  }

  function updateValidationState(updates: Partial<ValidationState>) {
    processingState.value.validation_state = {
      ...processingState.value.validation_state,
      ...updates,
    }
  }

  function updateAgentStatus(
    agentName: AgentStatus['name'],
    status: AgentStatus['status'],
    task?: string
  ) {
    const agent = agentStatuses.value.find((a) => a.name === agentName)
    if (agent) {
      agent.status = status
      agent.current_task = task
    }
  }

  function addEventLog(event: SSEEvent) {
    processingState.value.event_log.unshift(event)
    // Keep only last 100 events
    if (processingState.value.event_log.length > 100) {
      processingState.value.event_log = processingState.value.event_log.slice(0, 100)
    }
  }

  function incrementRetryCount() {
    processingState.value.retry_count += 1
  }

  function setError(error: string) {
    processingState.value.error = error
    processingState.value.is_processing = false
  }

  function setMealPlan(plan: MealPlan) {
    mealPlan.value = plan
    processingState.value.is_processing = false
    processingState.value.total_progress = 100
  }

  function clearMealPlan() {
    mealPlan.value = null
    completedMeals.value = []
    processingState.value = {
      is_processing: false,
      current_day: 0,
      current_meal: 0,
      total_progress: 0,
      validation_state: {
        nutrition: 'pending',
        allergy: 'pending',
        time: 'pending',
        health: 'pending',
        budget: 'pending',
      },
      retry_count: 0,
      event_log: [],
    }
  }

  function addCompletedMeal(meal: CompletedMeal) {
    completedMeals.value.push(meal)
  }

  function stopProcessing() {
    processingState.value.is_processing = false
  }

  return {
    // State
    mealPlan,
    processingState,
    agentStatuses,
    completedMeals,

    // Getters
    hasResult,
    isProcessing,
    totalProgress,
    currentDay,
    currentMeal,
    currentMealType,
    validationState,
    eventLog,
    hasError,
    errorMessage,
    allValidationsPassed,
    hasFailedValidation,
    passedValidationsCount,

    // Actions
    startProcessing,
    updateProgress,
    updateCurrentMeal,
    updateValidationState,
    updateAgentStatus,
    addEventLog,
    incrementRetryCount,
    setError,
    setMealPlan,
    clearMealPlan,
    addCompletedMeal,
    stopProcessing,
  }
})
