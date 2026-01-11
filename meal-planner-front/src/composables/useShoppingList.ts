// ============================================
// Shopping List Composable
// ============================================

import type { MealPlan } from '@/types'

export interface ShoppingItem {
  name: string
  quantity: number
  unit: string
  category: string
}

// Category keywords for ingredient classification
const CATEGORY_KEYWORDS: Record<string, string[]> = {
  '육류': ['닭', '소고기', '돼지고기', '쇠고기', '삼겹살', '목살', '등심', '안심', '가슴살'],
  '해산물': ['생선', '고등어', '연어', '참치', '새우', '오징어', '조개', '굴', '게', '낙지', '문어'],
  '채소': ['배추', '양배추', '상추', '시금치', '브로콜리', '당근', '양파', '파', '마늘', '고추', '피망', '가지', '호박', '무', '콩나물', '숙주', '버섯'],
  '유제품': ['우유', '치즈', '요구르트', '요거트', '버터', '크림'],
  '곡물': ['쌀', '현미', '보리', '귀리', '밀가루', '빵', '면', '국수', '파스타'],
  '조미료': ['소금', '설탕', '간장', '된장', '고추장', '식초', '참기름', '깨', '후추', '고춧가루', '다진마늘'],
  '기타': []
}

export function useShoppingList() {
  /**
   * Parse ingredient string or object to extract name, quantity, and unit
   * Example: "닭가슴살 150g" -> { name: "닭가슴살", quantity: 150, unit: "g" }
   * Example: {name: "닭가슴살", amount: "150g"} -> { name: "닭가슴살", quantity: 150, unit: "g" }
   */
  function parseIngredient(ingredient: string | { name: string; amount: string }): { name: string; quantity: number; unit: string } {
    // Handle object format from backend
    if (typeof ingredient === 'object' && ingredient.name && ingredient.amount) {
      const amountStr = ingredient.amount

      // Parse amount string like "150g" or "6개 (약 72g)"
      // Remove parentheses and extra text
      const cleaned = amountStr.replace(/\([^)]+\)/g, '').trim()

      // Pattern 1: "quantity+unit" (e.g., "150g", "10ml")
      const pattern1 = /(\d+(?:\.\d+)?)\s*([a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣]+)/
      const match1 = cleaned.match(pattern1)

      if (match1) {
        return {
          name: ingredient.name,
          quantity: parseFloat(match1[1]!),
          unit: match1[2]!
        }
      }

      // Pattern 2: just quantity (e.g., "3")
      const pattern2 = /(\d+(?:\.\d+)?)/
      const match2 = cleaned.match(pattern2)

      if (match2) {
        return {
          name: ingredient.name,
          quantity: parseFloat(match2[1]!),
          unit: '개'
        }
      }

      // No quantity found
      return {
        name: ingredient.name,
        quantity: 1,
        unit: '개'
      }
    }

    // Handle string format (legacy)
    const cleaned = (ingredient as string).replace(/[()]/g, '').trim()

    // Pattern 1: "name quantity+unit" (e.g., "닭가슴살 150g", "양파 1개")
    const pattern1 = /^(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣]+)$/
    const match1 = cleaned.match(pattern1)

    if (match1) {
      return {
        name: match1[1]!.trim(),
        quantity: parseFloat(match1[2]!),
        unit: match1[3]!
      }
    }

    // Pattern 2: "name quantity" without unit (e.g., "달걀 3")
    const pattern2 = /^(.+?)\s+(\d+(?:\.\d+)?)$/
    const match2 = cleaned.match(pattern2)

    if (match2) {
      return {
        name: match2[1]!.trim(),
        quantity: parseFloat(match2[2]!),
        unit: '개'
      }
    }

    // Pattern 3: No quantity specified (default to 1)
    return {
      name: cleaned,
      quantity: 1,
      unit: '개'
    }
  }

  /**
   * Categorize ingredient based on name keywords
   */
  function categorizeIngredient(name: string): string {
    const lowerName = name.toLowerCase()

    for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
      if (category === '기타') continue

      for (const keyword of keywords) {
        if (lowerName.includes(keyword.toLowerCase())) {
          return category
        }
      }
    }

    return '기타'
  }

  /**
   * Normalize units for aggregation
   * Convert similar units to standard form (e.g., "큰술", "큰스푼" -> "큰술")
   */
  function normalizeUnit(unit: string): string {
    const unitMap: Record<string, string> = {
      '큰술': '큰술',
      '큰스푼': '큰술',
      'tbsp': '큰술',
      '작은술': '작은술',
      '작은스푼': '작은술',
      'tsp': '작은술',
      '컵': '컵',
      'cup': '컵',
      '개': '개',
      '마리': '마리',
      '장': '장',
      '조각': '조각',
      'g': 'g',
      'kg': 'kg',
      'ml': 'ml',
      'l': 'l'
    }

    return unitMap[unit.toLowerCase()] || unit
  }

  /**
   * Generate shopping list from meal plan
   */
  function generateShoppingList(mealPlan: MealPlan): ShoppingItem[] {
    const itemMap = new Map<string, ShoppingItem>()

    // Iterate through all meals to collect ingredients
    mealPlan.days.forEach(day => {
      day.meals.forEach(meal => {
        meal.recipe.ingredients.forEach(ingredientStr => {
          const parsed = parseIngredient(ingredientStr)
          const normalizedUnit = normalizeUnit(parsed.unit)

          // Create unique key: name + unit
          const key = `${parsed.name.toLowerCase()}|${normalizedUnit}`

          if (itemMap.has(key)) {
            // Aggregate quantity for duplicate ingredients
            const existing = itemMap.get(key)!
            existing.quantity += parsed.quantity
          } else {
            // Add new ingredient
            itemMap.set(key, {
              name: parsed.name,
              quantity: parsed.quantity,
              unit: normalizedUnit,
              category: categorizeIngredient(parsed.name)
            })
          }
        })
      })
    })

    // Convert map to array and sort by category and name
    const items = Array.from(itemMap.values())

    // Category order for sorting
    const categoryOrder = ['육류', '해산물', '채소', '유제품', '곡물', '조미료', '기타']

    items.sort((a, b) => {
      // Sort by category first
      const categoryCompare = categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category)
      if (categoryCompare !== 0) return categoryCompare

      // Then sort by name alphabetically
      return a.name.localeCompare(b.name, 'ko-KR')
    })

    return items
  }

  return {
    generateShoppingList
  }
}
