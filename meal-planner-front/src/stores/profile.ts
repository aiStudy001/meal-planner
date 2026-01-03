import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserProfile } from '@/types'
import { DEFAULT_PROFILE, BUDGET_RATIOS } from '@/constants'

export const useProfileStore = defineStore('profile', () => {
  // State
  const profile = ref<UserProfile>({ ...DEFAULT_PROFILE })

  // Getters
  const perMealBudget = computed(() => {
    const { budget, budget_type, budget_distribution, days, meals_per_day } = profile.value

    const totalMeals = days * meals_per_day
    let totalBudget = 0

    // Calculate total budget based on budget type
    switch (budget_type) {
      case 'weekly':
        totalBudget = budget
        break
      case 'daily':
        totalBudget = budget * days
        break
      case 'per_meal':
        totalBudget = budget * totalMeals
        break
    }

    // Equal distribution
    if (budget_distribution === 'equal') {
      return Math.round(totalBudget / totalMeals)
    }

    // Weighted distribution: 아침:점심:저녁:간식 = 2:3:3.5:1.5
    const mealTypes = getMealTypes(meals_per_day)
    const totalRatio = mealTypes.reduce((sum, type) => sum + BUDGET_RATIOS[type], 0)
    const dailyBudget = totalBudget / days

    // Calculate per-meal budgets for weighted distribution
    const perMealBudgets: Record<string, number> = {}
    mealTypes.forEach((type) => {
      perMealBudgets[type] = Math.round((dailyBudget * BUDGET_RATIOS[type]) / totalRatio)
    })

    // Return average for display (actual allocation happens per meal type)
    const avgBudget =
      Object.values(perMealBudgets).reduce((sum, val) => sum + val, 0) / mealTypes.length
    return Math.round(avgBudget)
  })

  const perMealBudgetsByType = computed(() => {
    const { budget, budget_type, budget_distribution, days, meals_per_day } = profile.value

    const totalMeals = days * meals_per_day
    let totalBudget = 0

    switch (budget_type) {
      case 'weekly':
        totalBudget = budget
        break
      case 'daily':
        totalBudget = budget * days
        break
      case 'per_meal':
        totalBudget = budget * totalMeals
        break
    }

    const mealTypes = getMealTypes(meals_per_day)

    if (budget_distribution === 'equal') {
      const equalBudget = Math.round(totalBudget / totalMeals)
      const budgets: Record<string, number> = {}
      mealTypes.forEach((type) => {
        budgets[type] = equalBudget
      })
      return budgets
    }

    // Weighted distribution
    const totalRatio = mealTypes.reduce((sum, type) => sum + BUDGET_RATIOS[type], 0)
    const dailyBudget = totalBudget / days

    const budgets: Record<string, number> = {}
    mealTypes.forEach((type) => {
      budgets[type] = Math.round((dailyBudget * BUDGET_RATIOS[type]) / totalRatio)
    })

    return budgets
  })

  // Helper function to get meal types based on meals per day
  function getMealTypes(meals: number): Array<keyof typeof BUDGET_RATIOS> {
    switch (meals) {
      case 1:
        return ['점심']
      case 2:
        return ['아침', '저녁']
      case 3:
        return ['아침', '점심', '저녁']
      case 4:
      default:
        return ['아침', '점심', '저녁', '간식']
    }
  }

  // Actions
  function updateProfile(updates: Partial<UserProfile>) {
    profile.value = { ...profile.value, ...updates }
  }

  function resetProfile() {
    profile.value = { ...DEFAULT_PROFILE }
  }

  function validateProfile(): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (profile.value.age < 10 || profile.value.age > 100) {
      errors.push('나이는 10세에서 100세 사이여야 합니다')
    }

    if (profile.value.height < 100 || profile.value.height > 250) {
      errors.push('키는 100cm에서 250cm 사이여야 합니다')
    }

    if (profile.value.weight < 30 || profile.value.weight > 200) {
      errors.push('체중은 30kg에서 200kg 사이여야 합니다')
    }

    if (profile.value.budget < 10_000 || profile.value.budget > 1_000_000) {
      errors.push('예산은 1만원에서 100만원 사이여야 합니다')
    }

    return {
      valid: errors.length === 0,
      errors,
    }
  }

  return {
    profile,
    perMealBudget,
    perMealBudgetsByType,
    updateProfile,
    resetProfile,
    validateProfile,
  }
})
