import { ref } from 'vue'
import type { Meal, MealPlan } from '@/types'
import { useMealPlanStore } from '@/stores/mealPlan'

export interface AlternativeRecipe {
  name: string
  url: string
  content_preview: string
  calories: number | null
  cost: number | null
  cooking_time: number | null
  difficulty: string
  ingredients: string[]
}

export function useAlternativeRecipes() {
  const mealPlanStore = useMealPlanStore()
  const alternatives = ref<AlternativeRecipe[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch alternative recipes for a specific meal
   */
  async function fetchAlternatives(
    meal: Meal,
    mealPlan: MealPlan,
    calorieTolerance = 50,
    costTolerance = 1000
  ) {
    isLoading.value = true
    error.value = null
    alternatives.value = []

    const API_URL = import.meta.env.VITE_API_URL || (window.location.port === '' || window.location.port === '80' ? '' : 'http://localhost:8000')

    try {
      // Build query parameters
      const params = new URLSearchParams({
        current_menu: meal.recipe.name,
        target_calories: meal.recipe.nutrition.calories_kcal.toString(),
        target_cost: meal.recipe.estimated_cost.toString(),
        calorie_tolerance: calorieTolerance.toString(),
        cost_tolerance: costTolerance.toString(),
      })

      // Add macro parameters (탄단지 비율 매칭)
      if (meal.recipe.nutrition.carbs_g !== undefined && meal.recipe.nutrition.carbs_g !== null) {
        params.append('target_carb_g', meal.recipe.nutrition.carbs_g.toString())
      }
      if (meal.recipe.nutrition.protein_g !== undefined && meal.recipe.nutrition.protein_g !== null) {
        params.append('target_protein_g', meal.recipe.nutrition.protein_g.toString())
      }
      if (meal.recipe.nutrition.fat_g !== undefined && meal.recipe.nutrition.fat_g !== null) {
        params.append('target_fat_g', meal.recipe.nutrition.fat_g.toString())
      }

      // Add restrictions (allergies + dietary preferences)
      const profile = mealPlan.profile
      const restrictions = [...profile.allergies, ...profile.dietary_preferences]
      if (restrictions.length > 0) {
        params.append('restrictions', restrictions.join(','))
      }

      // Add exclude_recipes (all current recipes to avoid duplication)
      const currentRecipes = mealPlan.days.flatMap(d => d.meals.map(m => m.recipe.name))
      if (currentRecipes.length > 0) {
        params.append('exclude_recipes', currentRecipes.join(','))
      }

      // GET request
      const response = await fetch(`${API_URL}/api/alternative-recipes?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      alternatives.value = data.alternatives || []

      console.log('Alternative recipes fetched:', alternatives.value)
    } catch (err) {
      console.error('Failed to fetch alternative recipes:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      error.value = errorMessage
      alternatives.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Apply alternative recipe to meal plan
   *
   * This replaces the specified meal with the selected alternative recipe
   * and recalculates daily totals
   */
  function applyAlternative(
    targetDay: number,
    targetMealType: '아침' | '점심' | '저녁' | '간식',
    alternativeRecipe: AlternativeRecipe
  ) {
    const mealPlan = mealPlanStore.mealPlan
    if (!mealPlan) {
      console.error('No meal plan available to apply alternative')
      return
    }

    // Find day and meal indexes
    const dayIndex = mealPlan.days.findIndex(d => d.day === targetDay)
    if (dayIndex === -1) {
      console.error(`Day ${targetDay} not found in meal plan`)
      return
    }

    const dayData = mealPlan.days[dayIndex]!
    const mealIndex = dayData.meals.findIndex(
      m => m.meal_type === targetMealType
    )
    if (mealIndex === -1) {
      console.error(`Meal type ${targetMealType} not found in day ${targetDay}`)
      return
    }

    // Get current meal for fallback values
    const currentMeal = dayData.meals[mealIndex]!

    // Create updated meal with alternative recipe
    // Note: Alternative recipe might have null nutrition values from Tavily
    // Use current meal's values as fallback
    const updatedMeal: Meal = {
      meal_type: targetMealType,
      recipe: {
        name: alternativeRecipe.name,
        ingredients: (alternativeRecipe.ingredients.length > 0
          ? alternativeRecipe.ingredients
          : currentMeal.recipe.ingredients) as string[], // Fallback to current ingredients
        instructions: [`원본 레시피: ${alternativeRecipe.url}`],
        cooking_time_min: alternativeRecipe.cooking_time || currentMeal.recipe.cooking_time_min,
        difficulty: (alternativeRecipe.difficulty || currentMeal.recipe.difficulty) as '쉬움' | '보통' | '어려움',
        estimated_cost: alternativeRecipe.cost || currentMeal.recipe.estimated_cost,
        nutrition: {
          calories_kcal: alternativeRecipe.calories || currentMeal.recipe.nutrition.calories_kcal,
          protein_g: currentMeal.recipe.nutrition.protein_g, // Keep current (not provided by Tavily)
          carbs_g: currentMeal.recipe.nutrition.carbs_g, // Keep current
          fat_g: currentMeal.recipe.nutrition.fat_g, // Keep current
          sodium_mg: currentMeal.recipe.nutrition.sodium_mg, // Keep current
        },
        source: alternativeRecipe.url,
      },
      budget_allocated: alternativeRecipe.cost || currentMeal.budget_allocated,
      validation_status: {
        nutrition: 'passed',
        allergy: 'passed',
        time: 'passed',
        health: 'passed',
        budget: 'passed',
      },
    }

    // Replace the meal
    dayData.meals[mealIndex] = updatedMeal

    // Recalculate daily totals
    const dayMeals = dayData.meals
    const totalNutrition = {
      calories_kcal: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.calories_kcal, 0),
      protein_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.protein_g, 0),
      carbs_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.carbs_g, 0),
      fat_g: dayMeals.reduce((sum, m) => sum + m.recipe.nutrition.fat_g, 0),
      sodium_mg: dayMeals.reduce((sum, m) => sum + (m.recipe.nutrition.sodium_mg || 0), 0),
    }
    const totalCost = dayMeals.reduce((sum, m) => sum + m.recipe.estimated_cost, 0)

    dayData.total_nutrition = totalNutrition
    dayData.total_cost = totalCost

    // Recalculate total cost
    mealPlan.total_cost = mealPlan.days.reduce((sum, d) => sum + d.total_cost, 0)

    console.log('Alternative recipe applied:', {
      day: targetDay,
      meal_type: targetMealType,
      new_recipe: alternativeRecipe.name,
      new_cost: totalCost,
    })

    // Clear alternatives list after applying
    alternatives.value = []
  }

  return {
    alternatives,
    isLoading,
    error,
    fetchAlternatives,
    applyAlternative,
  }
}
