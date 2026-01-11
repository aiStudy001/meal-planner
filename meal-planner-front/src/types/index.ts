// ============================================
// Type Definitions for AI Meal Planner
// ============================================

// User Profile Types
export interface UserProfile {
  // Basic Information
  gender: 'male' | 'female'
  age: number
  height: number
  weight: number
  goal: '다이어트' | '벌크업' | '유지' | '질병관리'
  activity_level: 'low' | 'moderate' | 'high' | 'very_high'

  // Restrictions
  allergies: string[]
  dietary_preferences: string[]
  health_conditions: string[]

  // Cooking Settings
  cooking_time: '15분 이내' | '30분 이내' | '제한 없음'
  skill_level: '초급' | '중급' | '고급'
  meals_per_day: number  // 1-4
  days: number          // 1-7

  // Budget (updated with distribution)
  budget: number
  budget_type: 'weekly' | 'daily' | 'per_meal'
  budget_distribution: 'equal' | 'weighted'  // ⭐ Added
}

// Validation State (expanded to 5 validators)
export interface ValidationState {
  nutrition: 'pending' | 'passed' | 'failed'
  allergy: 'pending' | 'passed' | 'failed'
  time: 'pending' | 'passed' | 'failed'
  health: 'pending' | 'passed' | 'failed'      // ⭐ Added
  budget: 'pending' | 'passed' | 'failed'      // ⭐ Added
}

// SSE Event Types (matches backend exactly)
export interface SSEEvent {
  type:
    | 'progress'
    | 'validation'
    | 'retry'
    | 'meal_complete'
    | 'meal_regenerate_progress'
    | 'meal_regenerate_complete'
    | 'day_complete'
    | 'complete'
    | 'error'
    | 'warning'
  node?: string
  status?: 'started' | 'completed' | 'failed'
  data?: any
  message?: string
  timestamp?: string
}

// Nutrition Information
export interface NutritionInfo {
  calories_kcal: number
  protein_g: number
  fat_g: number
  carbs_g: number
  sodium_mg?: number
  sugar_g?: number
  saturated_fat_g?: number
  cholesterol_mg?: number
  fiber_g?: number
  potassium_mg?: number
}

// Recipe Structure
export interface Recipe {
  name: string
  ingredients: string[]
  instructions: string[]
  cooking_time_min: number
  difficulty: '쉬움' | '보통' | '어려움'
  estimated_cost: number
  nutrition: NutritionInfo
  source?: string
  image_url?: string
}

// Meal Structure
export interface Meal {
  meal_type: '아침' | '점심' | '저녁' | '간식'
  recipe: Recipe
  budget_allocated: number
  validation_status: ValidationState
}

// Daily Plan
export interface DailyPlan {
  day: number
  date?: string
  meals: Meal[]
  total_nutrition: NutritionInfo
  total_cost: number
}

// Complete Meal Plan
export interface MealPlan {
  profile: UserProfile
  days: DailyPlan[]
  total_budget: number
  total_cost: number
  avg_daily_nutrition: NutritionInfo
  created_at: string
}

// Processing State for UI
export interface ProcessingState {
  is_processing: boolean
  current_day: number
  current_meal: number
  current_meal_type?: string  // '아침' | '점심' | '저녁' | '간식'
  total_progress: number  // 0-100
  validation_state: ValidationState
  retry_count: number
  event_log: SSEEvent[]
  error?: string
}

// Agent Status
export interface AgentStatus {
  name: 'nutritionist' | 'chef' | 'budget_manager'
  status: 'idle' | 'working' | 'completed' | 'error'
  current_task?: string
}

// Meal Regeneration Request (for API)
export interface RegenerateMealRequest {
  profile: {
    goal: string
    weight: number
    height: number
    age: number
    gender: 'male' | 'female'
    activity_level: string
    restrictions: string[]
    health_conditions: string[]
    calorie_adjustment: number | null
    macro_ratio: any | null
    budget: number
    budget_type: string
    budget_distribution: string
    cooking_time: string
    skill_level: string
    meals_per_day: number
    days: number
  }
  target_day: number
  target_meal_type: '아침' | '점심' | '저녁' | '간식'
  daily_nutrition_targets: {
    calories: number
    carb_g: number
    protein_g: number
    fat_g: number
  }
  per_meal_budget: number
  completed_meals_context: Array<{
    day: number
    meal_type: string
    menu_name: string
    calories: number
    cost: number
  }>
  recently_used_recipes: string[]
  used_ingredients: string[]
}
