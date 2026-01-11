import { ref, onUnmounted } from 'vue'
import type { MealPlan, SSEEvent, Meal } from '@/types'
import { useMealPlanStore } from '@/stores/mealPlan'

export function useRegenerateMeal() {
  const mealPlanStore = useMealPlanStore()
  const isRegenerating = ref(false)
  const regenerationError = ref<string | null>(null)

  /**
   * Build regeneration context from current meal plan
   */
  function buildRegenerationContext(
    mealPlan: MealPlan,
    targetDay: number,
    targetMealType: '아침' | '점심' | '저녁' | '간식'
  ) {
    const profile = mealPlan.profile

    // Calculate daily nutrition targets (simple average from completed days)
    const completedDays = mealPlan.days.filter(d => d.meals.length === profile.meals_per_day)
    const dailyNutritionTargets = completedDays.length > 0
      ? {
          calories: Math.round(completedDays.reduce((sum, d) => sum + d.total_nutrition.calories_kcal, 0) / completedDays.length),
          carb_g: Math.round(completedDays.reduce((sum, d) => sum + d.total_nutrition.carbs_g, 0) / completedDays.length),
          protein_g: Math.round(completedDays.reduce((sum, d) => sum + d.total_nutrition.protein_g, 0) / completedDays.length),
          fat_g: Math.round(completedDays.reduce((sum, d) => sum + d.total_nutrition.fat_g, 0) / completedDays.length)
        }
      : {
          calories: 1800,
          carb_g: 225,
          protein_g: 135,
          fat_g: 40
        }

    // Calculate per-meal budget
    const totalMeals = profile.days * profile.meals_per_day
    let perMealBudget = 0

    if (profile.budget_type === 'weekly') {
      perMealBudget = Math.round(profile.budget / totalMeals)
    } else if (profile.budget_type === 'daily') {
      perMealBudget = Math.round(profile.budget / profile.meals_per_day)
    } else {
      perMealBudget = profile.budget
    }

    // Extract completed meals context (other meals from same day and previous days)
    const completedMealsContext = mealPlan.days
      .filter(d => d.day !== targetDay || d.day < targetDay)
      .flatMap(d => d.meals.map(m => ({
        day: d.day,
        meal_type: m.meal_type,
        menu_name: m.recipe.name,
        calories: m.recipe.nutrition.calories_kcal,
        cost: m.recipe.estimated_cost
      })))

    // Extract recently used recipes (last 10)
    const recentlyUsedRecipes = mealPlan.days
      .flatMap(d => d.meals.map(m => m.recipe.name))
      .slice(-10)

    // Extract used ingredients (main ingredients from recent meals)
    const usedIngredients = mealPlan.days
      .slice(-3) // Last 3 days
      .flatMap(d => d.meals.flatMap(m =>
        m.recipe.ingredients.slice(0, 2).map(ing =>
          typeof ing === 'string' ? ing : (ing.name || String(ing))
        )
      ))

    return {
      profile: {
        goal: profile.goal,
        weight: profile.weight,
        height: profile.height,
        age: profile.age,
        gender: profile.gender,
        activity_level: profile.activity_level,
        restrictions: [...profile.allergies, ...profile.dietary_preferences],
        health_conditions: profile.health_conditions,
        calorie_adjustment: null,
        budget: profile.budget,
        budget_type: profile.budget_type,
        budget_distribution: profile.budget_distribution,
        cooking_time: profile.cooking_time,
        skill_level: profile.skill_level,
        meals_per_day: profile.meals_per_day,
        days: profile.days
      },
      target_day: targetDay,
      target_meal_type: targetMealType,
      daily_nutrition_targets: dailyNutritionTargets,
      per_meal_budget: perMealBudget,
      completed_meals_context: completedMealsContext,
      recently_used_recipes: recentlyUsedRecipes,
      used_ingredients: usedIngredients
    }
  }

  /**
   * Regenerate a specific meal via SSE streaming
   */
  async function regenerateMeal(
    mealPlan: MealPlan,
    targetDay: number,
    targetMealType: '아침' | '점심' | '저녁' | '간식'
  ) {
    isRegenerating.value = true
    regenerationError.value = null

    const API_URL = import.meta.env.VITE_API_URL || (window.location.port === '' || window.location.port === '80' ? '' : 'http://localhost:8000')

    try {
      // Build regeneration context
      const requestBody = buildRegenerationContext(mealPlan, targetDay, targetMealType)

      // POST to /api/regenerate-meal with SSE
      const response = await fetch(`${API_URL}/api/regenerate-meal`, {
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

      // Read stream
      await readRegenerationStream(reader, decoder, targetDay, targetMealType)

    } catch (error) {
      console.error('Regeneration error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      regenerationError.value = errorMessage
      isRegenerating.value = false
      throw error
    }
  }

  /**
   * Read SSE stream for meal regeneration
   */
  async function readRegenerationStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    decoder: TextDecoder,
    targetDay: number,
    targetMealType: string
  ) {
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          // Process remaining buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data !== '[DONE]') {
                  try {
                    const event: SSEEvent = JSON.parse(data)
                    handleRegenerationEvent(event, targetDay, targetMealType)
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
              isRegenerating.value = false
              break
            }

            try {
              const event: SSEEvent = JSON.parse(data)
              handleRegenerationEvent(event, targetDay, targetMealType)
            } catch (error) {
              console.error('Failed to parse SSE event:', error, data)
            }
          }
        }
      }
    } catch (error) {
      console.error('SSE Stream reading error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      regenerationError.value = errorMessage
      isRegenerating.value = false
    }
  }

  /**
   * Handle SSE events for meal regeneration
   */
  function handleRegenerationEvent(event: SSEEvent, targetDay: number, targetMealType: string) {
    console.log('Regeneration Event:', event)

    const { type, data } = event

    switch (type) {
      case 'meal_regenerate_progress':
        console.log('Regeneration progress:', data)
        // Could update UI with progress indicator
        break

      case 'validation':
        console.log('Validation event:', data)
        // Could show validation feedback
        break

      case 'meal_regenerate_complete':
        handleRegenerationComplete(data, targetDay, targetMealType)
        break

      case 'error':
        regenerationError.value = event.message || 'Regeneration failed'
        isRegenerating.value = false
        break
    }
  }

  /**
   * Handle regeneration completion - update meal plan with new meal
   */
  function handleRegenerationComplete(data: any, targetDay: number, targetMealType: string) {
    console.log('Regeneration completed:', data)

    if (data?.meal && mealPlanStore.mealPlan) {
      const newMeal: Meal = {
        meal_type: data.meal.meal_type,
        recipe: {
          name: data.meal.recipe.name,
          ingredients: data.meal.recipe.ingredients,
          instructions: data.meal.recipe.instructions,
          cooking_time_min: data.meal.recipe.cooking_time_min,
          difficulty: data.meal.recipe.difficulty,
          estimated_cost: data.meal.recipe.estimated_cost,
          nutrition: data.meal.recipe.nutrition,
          source: data.meal.recipe.source,
        },
        budget_allocated: data.meal.budget_allocated,
        validation_status: {
          nutrition: 'passed',
          allergy: 'passed',
          time: 'passed',
          health: 'passed',
          budget: 'passed',
        },
      }

      // Find and replace the specific meal in meal plan
      const dayIndex = mealPlanStore.mealPlan.days.findIndex(d => d.day === targetDay)
      if (dayIndex !== -1) {
        const mealIndex = mealPlanStore.mealPlan.days[dayIndex].meals.findIndex(m => m.meal_type === targetMealType)

        if (mealIndex !== -1) {
          // Replace the meal
          mealPlanStore.mealPlan.days[dayIndex].meals[mealIndex] = newMeal

          // Recalculate daily totals
          const dayMeals = mealPlanStore.mealPlan.days[dayIndex].meals
          const totalNutrition = {
            calories_kcal: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.calories_kcal, 0),
            protein_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.protein_g, 0),
            carbs_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.carbs_g, 0),
            fat_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.fat_g, 0),
            sodium_mg: dayMeals.reduce((sum, m) => sum + (m.recipe.nutrition.sodium_mg || 0), 0),
          }
          const totalCost = dayMeals.reduce((sum, m) => sum + m.recipe.estimated_cost, 0)

          mealPlanStore.mealPlan.days[dayIndex].total_nutrition = totalNutrition
          mealPlanStore.mealPlan.days[dayIndex].total_cost = totalCost

          // Recalculate total cost
          mealPlanStore.mealPlan.total_cost = mealPlanStore.mealPlan.days.reduce((sum, d) => sum + d.total_cost, 0)

          console.log('Meal plan updated with regenerated meal')
        }
      }
    }

    isRegenerating.value = false
  }

  // Cleanup on unmount
  onUnmounted(() => {
    isRegenerating.value = false
  })

  return {
    isRegenerating,
    regenerationError,
    regenerateMeal,
  }
}
