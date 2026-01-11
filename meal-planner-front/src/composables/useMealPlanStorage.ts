import { ref } from 'vue'
import type { MealPlan } from '@/types'

const STORAGE_KEY = 'meal-planner:saved-plans'
const MAX_SAVED_PLANS = 5

export interface SavedPlanMetadata {
  id: string
  saved_at: string // ISO timestamp
  profile_summary: string // e.g., "28세 남성, 다이어트 목표"
  total_cost: number
  days: number
  meal_plan: MealPlan
}

// Singleton state - shared across all component instances
const savedPlans = ref<SavedPlanMetadata[]>([])
const error = ref<string | null>(null)

export function useMealPlanStorage() {

  /**
   * Load all saved plans from LocalStorage
   */
  function loadSavedPlans(): SavedPlanMetadata[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) {
        savedPlans.value = []
        return []
      }

      const plans: SavedPlanMetadata[] = JSON.parse(stored)
      savedPlans.value = plans
      return plans
    } catch (err) {
      console.error('Failed to load saved plans:', err)
      error.value = err instanceof Error ? err.message : 'Failed to load saved plans'
      savedPlans.value = []
      return []
    }
  }

  /**
   * Save a meal plan to LocalStorage
   *
   * - Generates unique ID (timestamp-based)
   * - Adds metadata (saved_at, profile summary, total_cost, days)
   * - Enforces FIFO limit (max 5 plans, removes oldest if exceeded)
   */
  function saveMealPlan(mealPlan: MealPlan): boolean {
    try {
      // Load existing plans
      const existingPlans = loadSavedPlans()

      // Generate unique ID
      const id = `plan-${Date.now()}`

      // Create profile summary
      const profile = mealPlan.profile
      const profileSummary = `${profile.age}세 ${profile.gender === 'male' ? '남성' : '여성'}, ${profile.goal}`

      // Create metadata
      const metadata: SavedPlanMetadata = {
        id,
        saved_at: new Date().toISOString(),
        profile_summary: profileSummary,
        total_cost: mealPlan.total_cost,
        days: mealPlan.days.length,
        meal_plan: mealPlan,
      }

      // Add to list
      const updatedPlans = [...existingPlans, metadata]

      // Enforce FIFO limit (max 5)
      if (updatedPlans.length > MAX_SAVED_PLANS) {
        // Remove oldest (first item)
        updatedPlans.shift()
        console.log(`Removed oldest plan to maintain ${MAX_SAVED_PLANS} plan limit`)
      }

      // Save to LocalStorage
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedPlans))
      savedPlans.value = updatedPlans

      console.log('Meal plan saved successfully:', { id, profile_summary: profileSummary })
      return true
    } catch (err) {
      console.error('Failed to save meal plan:', err)
      error.value = err instanceof Error ? err.message : 'Failed to save meal plan'

      // Check if quota exceeded
      if (err instanceof DOMException && err.name === 'QuotaExceededError') {
        error.value = 'LocalStorage quota exceeded. Please delete old plans.'
      }

      return false
    }
  }

  /**
   * Load a specific meal plan by ID
   */
  function loadMealPlan(id: string): MealPlan | null {
    try {
      const plans = loadSavedPlans()
      const plan = plans.find(p => p.id === id)

      if (!plan) {
        console.warn(`Meal plan with ID ${id} not found`)
        return null
      }

      console.log('Meal plan loaded:', { id, profile_summary: plan.profile_summary })
      return plan.meal_plan
    } catch (err) {
      console.error('Failed to load meal plan:', err)
      error.value = err instanceof Error ? err.message : 'Failed to load meal plan'
      return null
    }
  }

  /**
   * Delete a specific meal plan by ID
   */
  function deleteMealPlan(id: string): boolean {
    try {
      const existingPlans = loadSavedPlans()
      const filteredPlans = existingPlans.filter(p => p.id !== id)

      if (filteredPlans.length === existingPlans.length) {
        console.warn(`Meal plan with ID ${id} not found`)
        return false
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(filteredPlans))
      savedPlans.value = filteredPlans

      console.log('Meal plan deleted:', id)
      return true
    } catch (err) {
      console.error('Failed to delete meal plan:', err)
      error.value = err instanceof Error ? err.message : 'Failed to delete meal plan'
      return false
    }
  }

  /**
   * Clear all saved plans (for testing or reset)
   */
  function clearAllPlans(): boolean {
    try {
      localStorage.removeItem(STORAGE_KEY)
      savedPlans.value = []
      console.log('All saved plans cleared')
      return true
    } catch (err) {
      console.error('Failed to clear saved plans:', err)
      error.value = err instanceof Error ? err.message : 'Failed to clear saved plans'
      return false
    }
  }

  /**
   * Get storage usage summary
   */
  function getStorageInfo(): { count: number; maxCount: number; usageBytes: number } {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      const plans = loadSavedPlans()

      return {
        count: plans.length,
        maxCount: MAX_SAVED_PLANS,
        usageBytes: stored ? new Blob([stored]).size : 0,
      }
    } catch (err) {
      console.error('Failed to get storage info:', err)
      return { count: 0, maxCount: MAX_SAVED_PLANS, usageBytes: 0 }
    }
  }

  return {
    savedPlans,
    error,
    loadSavedPlans,
    saveMealPlan,
    loadMealPlan,
    deleteMealPlan,
    clearAllPlans,
    getStorageInfo,
  }
}
