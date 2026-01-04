// ============================================
// Constants for AI Meal Planner
// ============================================

// Allergies List
export const ALLERGIES = [
  '우유',
  '계란',
  '밀',
  '땅콩',
  '대두',
  '새우',
  '게',
  '고등어',
  '돼지고기',
  '닭고기',
  '쇠고기',
  '복숭아',
  '토마토',
  '아황산류',
]

// Dietary Preferences
export const DIETARY_PREFERENCES = [
  '채식',
  '비건',
  '페스코',
  '저염식',
  '저당식',
  '저지방',
  '글루텐프리',
  '할랄',
  '코셔',
]

// Health Conditions with Criteria (⭐ Updated values from medical guidelines)
export const HEALTH_CONDITIONS = [
  {
    value: '당뇨',
    label: '당뇨병',
    description: '당류 ≤30g/일, 저GI 식품 선호',
    emoji: '🩺',
    criteria: {
      sugar_g: 30,  // 대한당뇨병학회: 에너지의 6% 기준
    },
  },
  {
    value: '고혈압',
    label: '고혈압',
    description: '나트륨 ≤2000mg/일, 고칼륨 식품 권장',
    emoji: '❤️',
    criteria: {
      sodium_mg: 2000,  // 대한고혈압학회 + WHO 권장
    },
  },
  {
    value: '고지혈증',
    label: '고지혈증',
    description: '포화지방 ≤15g/일, 콜레스테롤 ≤300mg/일',
    emoji: '💊',
    criteria: {
      saturated_fat_g: 15,     // 한국지질동맥경화학회: 칼로리의 7%
      cholesterol_mg: 300,
    },
  },
]

// Goals with Descriptions
export const GOALS = [
  {
    value: '다이어트',
    label: '체중 감량',
    emoji: '🏃',
    description: '체중 감량을 위한 칼로리 제한 (-500kcal)',
    color: 'text-blue-600',
  },
  {
    value: '벌크업',
    label: '근육 증가',
    emoji: '💪',
    description: '근육 증가를 위한 칼로리 증가 (+500kcal)',
    color: 'text-red-600',
  },
  {
    value: '유지',
    label: '체중 유지',
    emoji: '⚖️',
    description: '현재 체중 유지 (±0kcal)',
    color: 'text-green-600',
  },
  {
    value: '질병관리',
    label: '질병 관리',
    emoji: '🏥',
    description: '건강 상태에 맞춘 맞춤형 식단',
    color: 'text-purple-600',
  },
]

// Activity Levels
export const ACTIVITY_LEVELS = [
  {
    value: 'low',
    label: '낮음',
    description: '거의 운동 안함 (주 0-1회)',
    multiplier: 'x1.2',
    emoji: '🛋️',
  },
  {
    value: 'moderate',
    label: '보통',
    description: '가벼운 운동 (주 1-3회)',
    multiplier: 'x1.375',
    emoji: '🚶',
  },
  {
    value: 'high',
    label: '높음',
    description: '규칙적인 운동 (주 3-5회)',
    multiplier: 'x1.55',
    emoji: '🏃',
  },
  {
    value: 'very_high',
    label: '매우 높음',
    description: '매일 강도 높은 운동',
    multiplier: 'x1.725',
    emoji: '🏋️',
  },
]

// Cooking Time Options
export const COOKING_TIME_OPTIONS = [
  { value: '15분 이내', label: '15분 이내', emoji: '⚡' },
  { value: '30분 이내', label: '30분 이내', emoji: '⏱️' },
  { value: '제한 없음', label: '제한 없음', emoji: '🕐' },
]

// Skill Level Options
export const SKILL_LEVEL_OPTIONS = [
  { value: '초급', label: '초급', description: '간단한 조리', emoji: '👶' },
  { value: '중급', label: '중급', description: '보통 난이도', emoji: '👨‍🍳' },
  { value: '고급', label: '고급', description: '복잡한 조리', emoji: '⭐' },
]

// Meals Per Day Options
export const MEALS_PER_DAY_OPTIONS = [
  { value: 1, label: '1끼', description: '점심' },
  { value: 2, label: '2끼', description: '아침 + 저녁' },
  { value: 3, label: '3끼', description: '아침 + 점심 + 저녁' },
  { value: 4, label: '4끼', description: '아침 + 점심 + 저녁 + 간식' },
]

// Days Options
export const DAYS_OPTIONS = [1, 2, 3, 4, 5, 6, 7]

// Budget Type Options
export const BUDGET_TYPE_OPTIONS = [
  { value: 'weekly', label: '주간 총액', description: '1주일 전체 예산' },
  { value: 'daily', label: '일일 총액', description: '하루 예산 x 일수' },
  { value: 'per_meal', label: '끼니당 금액', description: '끼니당 예산 x 총 끼니수' },
]

// Budget Distribution Options (⭐ Added)
export const BUDGET_DISTRIBUTION_OPTIONS = [
  {
    value: 'equal',
    label: '균등 배분',
    description: '모든 끼니에 동일한 예산 배정',
  },
  {
    value: 'weighted',
    label: '차등 배분',
    description: '아침 < 점심 < 저녁 (2:3:3.5 비율)',
  },
]

// Budget Distribution Ratios (⭐ Added)
export const BUDGET_RATIOS = {
  아침: 2,
  점심: 3,
  저녁: 3.5,
  간식: 1.5,
}

// Recipe Database Info
export const RECIPE_DB_INFO = {
  total_count: 336_588,
  description: '한국 레시피 데이터베이스 기반',
}

// API Endpoints
export const API_ENDPOINTS = {
  HEALTH: '/api/health',
  GENERATE: '/api/generate',
}

// Default Profile Values
export const DEFAULT_PROFILE = {
  gender: 'male' as const,
  age: 30,
  height: 170,
  weight: 70,
  goal: '유지' as const,
  activity_level: 'moderate' as const,
  allergies: [],
  dietary_preferences: [],
  health_conditions: [],
  cooking_time: '30분 이내' as const,
  skill_level: '중급' as const,
  meals_per_day: 3,
  days: 7,
  budget: 100_000,
  budget_type: 'weekly' as const,
  budget_distribution: 'equal' as const,
}
