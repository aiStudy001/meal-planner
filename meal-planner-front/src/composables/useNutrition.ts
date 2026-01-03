import type { NutritionInfo, UserProfile } from '@/types'

export function useNutrition() {
  /**
   * Calculate BMR (Basal Metabolic Rate) using Mifflin-St Jeor Formula
   */
  function calculateBMR(profile: UserProfile): number {
    const { gender, age, height, weight } = profile

    if (gender === 'male') {
      return 10 * weight + 6.25 * height - 5 * age + 5
    } else {
      return 10 * weight + 6.25 * height - 5 * age - 161
    }
  }

  /**
   * Calculate TDEE (Total Daily Energy Expenditure)
   */
  function calculateTDEE(profile: UserProfile): number {
    const bmr = calculateBMR(profile)

    const multipliers: Record<UserProfile['activity_level'], number> = {
      low: 1.2,
      moderate: 1.375,
      high: 1.55,
      very_high: 1.725,
    }

    return Math.round(bmr * multipliers[profile.activity_level])
  }

  /**
   * Calculate target calories based on goal
   */
  function calculateTargetCalories(profile: UserProfile): number {
    const tdee = calculateTDEE(profile)

    switch (profile.goal) {
      case '다이어트':
        return Math.round(tdee - 500)
      case '벌크업':
        return Math.round(tdee + 500)
      case '유지':
        return tdee
      case '질병관리':
        return tdee // 질병관리는 TDEE 기준
      default:
        return tdee
    }
  }

  /**
   * Calculate macronutrient targets
   */
  function calculateMacroTargets(targetCalories: number, goal: UserProfile['goal']) {
    let proteinRatio = 0.3
    let fatRatio = 0.25
    let carbRatio = 0.45

    // Adjust ratios based on goal
    if (goal === '다이어트') {
      proteinRatio = 0.35
      fatRatio = 0.25
      carbRatio = 0.4
    } else if (goal === '벌크업') {
      proteinRatio = 0.3
      fatRatio = 0.25
      carbRatio = 0.45
    }

    return {
      protein_g: Math.round((targetCalories * proteinRatio) / 4),
      fat_g: Math.round((targetCalories * fatRatio) / 9),
      carbs_g: Math.round((targetCalories * carbRatio) / 4),
    }
  }

  /**
   * Format nutrition info for display
   */
  function formatNutrition(nutrition: NutritionInfo): string[] {
    const lines: string[] = []

    lines.push(`칼로리: ${nutrition.calories_kcal}kcal`)
    lines.push(`단백질: ${nutrition.protein_g}g`)
    lines.push(`지방: ${nutrition.fat_g}g`)
    lines.push(`탄수화물: ${nutrition.carbs_g}g`)

    if (nutrition.sodium_mg !== undefined) {
      lines.push(`나트륨: ${nutrition.sodium_mg}mg`)
    }

    if (nutrition.sugar_g !== undefined) {
      lines.push(`당류: ${nutrition.sugar_g}g`)
    }

    if (nutrition.saturated_fat_g !== undefined) {
      lines.push(`포화지방: ${nutrition.saturated_fat_g}g`)
    }

    if (nutrition.fiber_g !== undefined) {
      lines.push(`식이섬유: ${nutrition.fiber_g}g`)
    }

    return lines
  }

  /**
   * Check if nutrition meets health conditions
   */
  function checkHealthConstraints(
    nutrition: NutritionInfo,
    healthConditions: string[]
  ): { passed: boolean; violations: string[] } {
    const violations: string[] = []

    if (healthConditions.includes('당뇨') && nutrition.sugar_g && nutrition.sugar_g > 30) {
      violations.push(`당류 ${nutrition.sugar_g}g (권장: ≤30g)`)
    }

    if (healthConditions.includes('고혈압') && nutrition.sodium_mg && nutrition.sodium_mg > 2000) {
      violations.push(`나트륨 ${nutrition.sodium_mg}mg (권장: ≤2000mg)`)
    }

    if (
      healthConditions.includes('고지혈증') &&
      nutrition.saturated_fat_g &&
      nutrition.saturated_fat_g > 15
    ) {
      violations.push(`포화지방 ${nutrition.saturated_fat_g}g (권장: ≤15g)`)
    }

    return {
      passed: violations.length === 0,
      violations,
    }
  }

  /**
   * Sum nutrition info from multiple meals
   */
  function sumNutrition(nutritions: NutritionInfo[]): NutritionInfo {
    return nutritions.reduce(
      (sum, current) => ({
        calories_kcal: sum.calories_kcal + current.calories_kcal,
        protein_g: sum.protein_g + current.protein_g,
        fat_g: sum.fat_g + current.fat_g,
        carbs_g: sum.carbs_g + current.carbs_g,
        sodium_mg: (sum.sodium_mg || 0) + (current.sodium_mg || 0),
        sugar_g: (sum.sugar_g || 0) + (current.sugar_g || 0),
        saturated_fat_g: (sum.saturated_fat_g || 0) + (current.saturated_fat_g || 0),
        cholesterol_mg: (sum.cholesterol_mg || 0) + (current.cholesterol_mg || 0),
        fiber_g: (sum.fiber_g || 0) + (current.fiber_g || 0),
        potassium_mg: (sum.potassium_mg || 0) + (current.potassium_mg || 0),
      }),
      {
        calories_kcal: 0,
        protein_g: 0,
        fat_g: 0,
        carbs_g: 0,
        sodium_mg: 0,
        sugar_g: 0,
        saturated_fat_g: 0,
        cholesterol_mg: 0,
        fiber_g: 0,
        potassium_mg: 0,
      }
    )
  }

  return {
    calculateBMR,
    calculateTDEE,
    calculateTargetCalories,
    calculateMacroTargets,
    formatNutrition,
    checkHealthConstraints,
    sumNutrition,
  }
}
