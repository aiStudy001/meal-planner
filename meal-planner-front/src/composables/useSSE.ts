import { ref, onUnmounted } from 'vue'
import type { UserProfile, SSEEvent, MealPlan } from '@/types'
import { useMealPlanStore } from '@/stores/mealPlan'
import { useProfileStore } from '@/stores/profile'

export function useSSE() {
  const mealPlanStore = useMealPlanStore()
  const profileStore = useProfileStore()
  const eventSource = ref<EventSource | null>(null)
  const isConnected = ref(false)

  async function startGeneration(profile: UserProfile) {
    // Reset state
    mealPlanStore.clearMealPlan()
    mealPlanStore.startProcessing()

    // Use relative path for Docker/Nginx proxy (port 80 or default), or full URL for dev
    const API_URL = import.meta.env.VITE_API_URL || (window.location.port === '' || window.location.port === '80' ? '' : 'http://localhost:8000')

    try {
      // Transform UserProfile to match backend MealPlanRequest schema
      const requestBody = {
        ...profile,
        // Combine allergies and dietary_preferences into restrictions
        restrictions: [...profile.allergies, ...profile.dietary_preferences],
      }
      // Remove the original fields that were combined
      delete (requestBody as any).allergies
      delete (requestBody as any).dietary_preferences

      // For SSE, we need to POST the profile and get back a streaming response
      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Get the reader
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      isConnected.value = true

      // Read stream in background (non-blocking)
      readStream(reader, decoder)

      // Return immediately after starting the stream
    } catch (error) {
      console.error('SSE Connection error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      mealPlanStore.setError(errorMessage)
      isConnected.value = false
      throw error // Re-throw to let caller know it failed
    }
  }

  async function readStream(reader: ReadableStreamDefaultReader<Uint8Array>, decoder: TextDecoder) {
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          // Process remaining buffer before closing
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data !== '[DONE]') {
                  try {
                    const event: SSEEvent = JSON.parse(data)
                    handleSSEEvent(event)
                  } catch (error) {
                    console.error('Failed to parse SSE event:', error, data)
                  }
                }
              }
            }
          }
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (data === '[DONE]') {
              isConnected.value = false
              break
            }

            try {
              const event: SSEEvent = JSON.parse(data)
              handleSSEEvent(event)
            } catch (error) {
              console.error('Failed to parse SSE event:', error, data)
            }
          }
        }
      }
    } catch (error) {
      console.error('SSE Stream reading error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      mealPlanStore.setError(errorMessage)
      isConnected.value = false
    }
  }

  function handleSSEEvent(event: SSEEvent) {
    console.log('SSE Event:', event)
    mealPlanStore.addEventLog(event)

    const { type, node, status, data, message } = event

    // Handle different event types
    switch (type) {
      case 'progress':
        handleProgressEvent(node, status, data)
        break

      case 'validation':
        handleValidationEvent(node, status, data)
        break

      case 'retry':
        mealPlanStore.incrementRetryCount()
        if (message) {
          console.warn('Retry:', message)
        }
        break

      case 'meal_complete':
        handleMealComplete(data)
        break

      case 'day_complete':
        handleDayComplete(data)
        break

      case 'complete':
        handleComplete(data)
        break

      case 'error':
        mealPlanStore.setError(message || 'Unknown error occurred')
        break
    }
  }

  function handleProgressEvent(node?: string, status?: string, data?: any) {
    if (!node) return

    // Update agent status
    if (node.includes('nutritionist')) {
      mealPlanStore.updateAgentStatus('nutritionist', status === 'completed' ? 'completed' : 'working', data?.task)
    } else if (node.includes('chef')) {
      mealPlanStore.updateAgentStatus('chef', status === 'completed' ? 'completed' : 'working', data?.task)
    } else if (node.includes('budget')) {
      mealPlanStore.updateAgentStatus('budget_manager', status === 'completed' ? 'completed' : 'working', data?.task)
    }

    // Update current meal info with meal_type
    if (data?.day && data?.meal) {
      mealPlanStore.updateCurrentMeal(data.day, data.meal, data.meal_type)
    }

    // Calculate progress
    if (data?.total_meals && data?.completed_meals !== undefined) {
      const progress = Math.round((data.completed_meals / data.total_meals) * 100)
      mealPlanStore.updateProgress(progress)
    }
  }

  function handleValidationEvent(node?: string, status?: string, data?: any) {
    if (!node) return

    // Handle 5 validators: nutrition_checker, allergy_checker, time_checker, health_checker, budget_checker
    const validatorMap: Record<string, keyof typeof mealPlanStore.validationState> = {
      nutrition_checker: 'nutrition',
      allergy_checker: 'allergy',
      time_checker: 'time',
      health_checker: 'health',
      budget_checker: 'budget',
    }

    const validatorKey = validatorMap[node]
    if (validatorKey) {
      const validationStatus = status === 'completed'
        ? (data?.passed ? 'passed' : 'failed')
        : 'pending'

      mealPlanStore.updateValidationState({
        [validatorKey]: validationStatus as 'pending' | 'passed' | 'failed',
      })
    }
  }

  function handleMealComplete(data: any) {
    console.log('Meal completed:', data)

    // Add to completed meals list
    if (data?.day && data?.meal_type && data?.menu) {
      mealPlanStore.addCompletedMeal({
        day: data.day,
        meal_type: data.meal_type,
        menu_name: data.menu,
        calories: data.calories || 0,
        cost: data.cost || 0,
      })
    }

    // Reset validation states for next meal
    mealPlanStore.updateValidationState({
      nutrition: 'pending',
      allergy: 'pending',
      time: 'pending',
      health: 'pending',
      budget: 'pending',
    })

    // Reset retry count for next meal
    mealPlanStore.resetRetryCount()

    // NOTE: Do NOT update current_meal here
    // day_iterator will send a progress event with the NEXT meal info
    // If we update current_meal here with completed meal info, UI won't advance

    // Update progress percentage
    if (data?.total_meals && data?.completed_meals !== undefined) {
      const progress = Math.round((data.completed_meals / data.total_meals) * 100)
      mealPlanStore.updateProgress(progress)
    }
  }

  function handleDayComplete(data: any) {
    console.log('Day completed:', data)
    // Day completion handling
  }

  function handleComplete(data: any) {
    console.log('Complete:', data)

    if (data?.meal_plan && Array.isArray(data.meal_plan)) {
      // Backend sends weekly_plan as array, construct MealPlan object
      const mealPlan: MealPlan = {
        days: data.meal_plan,
        profile: profileStore.profile,  // Get profile from store
        total_budget: profileStore.profile.budget,  // Get budget from profile
        total_cost: data.meal_plan.reduce((sum: number, day: any) => sum + (day.total_cost || 0), 0),
        avg_daily_nutrition: data.avg_daily_nutrition || {} as any,  // Use from backend if available
        created_at: new Date().toISOString(),
      }
      mealPlanStore.setMealPlan(mealPlan)
      // ProcessingView will display completion UI automatically
    } else {
      mealPlanStore.stopProcessing()
    }
  }

  function stopGeneration() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    isConnected.value = false
    mealPlanStore.stopProcessing()
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopGeneration()
  })

  return {
    isConnected,
    startGeneration,
    stopGeneration,
  }
}
