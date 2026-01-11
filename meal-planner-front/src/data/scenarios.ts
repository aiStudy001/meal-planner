// ============================================
// Pre-configured Test Scenarios
// ============================================

import type { UserProfile } from '@/types'

export interface Scenario {
  id: string
  name: string
  description: string
  profile: UserProfile
}

export const scenarios: Scenario[] = [
  {
    id: 'weight-loss-male',
    name: '체중 감량 남성',
    description: '고단백 저칼로리 식단으로 근육 유지하며 체지방 감소',
    profile: {
      gender: 'male',
      age: 32,
      height: 175,
      weight: 85,
      goal: '다이어트',
      activity_level: 'moderate',
      allergies: [],
      dietary_preferences: [],
      health_conditions: [],
      cooking_time: '30분 이내',
      skill_level: '중급',
      meals_per_day: 3,
      days: 3,
      budget: 90000,
      budget_type: 'weekly',
      budget_distribution: 'equal'
    }
  },
  {
    id: 'weight-gain-female',
    name: '체중 증가 여성',
    description: '균형잡힌 영양소 비율로 건강한 체중 증가',
    profile: {
      gender: 'female',
      age: 25,
      height: 162,
      weight: 48,
      goal: '벌크업',
      activity_level: 'high',
      allergies: [],
      dietary_preferences: [],
      health_conditions: [],
      cooking_time: '30분 이내',
      skill_level: '초급',
      meals_per_day: 3,
      days: 3,
      budget: 100000,
      budget_type: 'weekly',
      budget_distribution: 'equal'
    }
  },
  {
    id: 'multi-allergy',
    name: '다중 알레르기',
    description: '견과류, 해산물, 유제품 제외 - 대체 단백질원 활용',
    profile: {
      gender: 'male',
      age: 28,
      height: 172,
      weight: 70,
      goal: '유지',
      activity_level: 'moderate',
      allergies: ['견과류', '해산물', '우유'],
      dietary_preferences: [],
      health_conditions: [],
      cooking_time: '15분 이내',
      skill_level: '초급',
      meals_per_day: 3,
      days: 3,
      budget: 95000,
      budget_type: 'weekly',
      budget_distribution: 'equal'
    }
  },
  {
    id: 'health-constraints',
    name: '건강 제약 (당뇨+고혈압)',
    description: '저염, 저당, 혈당 조절 식단으로 질병 관리',
    profile: {
      gender: 'male',
      age: 55,
      height: 168,
      weight: 75,
      goal: '질병관리',
      activity_level: 'low',
      allergies: [],
      dietary_preferences: [],
      health_conditions: ['당뇨병', '고혈압'],
      cooking_time: '제한 없음',
      skill_level: '고급',
      meals_per_day: 3,
      days: 3,
      budget: 105000,
      budget_type: 'weekly',
      budget_distribution: 'equal'
    }
  }
]
