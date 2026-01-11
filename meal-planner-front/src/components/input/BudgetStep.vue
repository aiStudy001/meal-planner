<script setup lang="ts">
import { computed } from 'vue'
import { useProfileStore } from '@/stores/profile'
import { useNutrition } from '@/composables/useNutrition'

const profileStore = useProfileStore()
const profile = computed(() => profileStore.profile)
const { calculateTargetCalories } = useNutrition()

const budgetTypeOptions = [
  { value: 'weekly', label: '주간 총액', desc: '일주일 전체 예산' },
  { value: 'daily', label: '일일 총액', desc: '하루 전체 예산' },
  { value: 'per_meal', label: '끼니당', desc: '끼니당 예산' }
]

// Nutrition calculation for display
const targetCalories = computed(() => calculateTargetCalories(profile.value))

// Validation
const isValid = computed(() => {
  return (
    profile.value.budget > 0 &&
    profile.value.budget_type &&
    profile.value.budget_distribution
  )
})

defineExpose({ isValid })
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold mb-4">예산 및 최종 확인</h2>

    <!-- Budget Amount -->
    <div>
      <label class="block text-sm font-medium mb-2">예산 금액 (원)</label>
      <input
        type="number"
        :value="profile.budget"
        @input="profileStore.updateProfile({ budget: Number(($event.target as HTMLInputElement).value) })"
        class="w-full px-4 py-3 border border-gray-300 rounded-lg text-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="300000"
        min="10000"
        max="1000000"
        step="10000"
      />
    </div>

    <!-- Budget Type -->
    <div>
      <label class="block text-sm font-medium mb-2">예산 기준</label>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="type in budgetTypeOptions"
          :key="type.value"
          @click="profileStore.updateProfile({ budget_type: type.value as typeof profile.budget_type })"
          :class="[
            'py-3 px-4 rounded-lg border-2 transition-all text-center',
            profile.budget_type === type.value
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="font-medium">{{ type.label }}</div>
          <div class="text-xs text-gray-500">{{ type.desc }}</div>
        </button>
      </div>
    </div>

    <!-- Budget Distribution -->
    <div>
      <label class="block text-sm font-medium mb-2">예산 배분 방식</label>
      <div class="space-y-3">
        <button
          @click="profileStore.updateProfile({ budget_distribution: 'equal' })"
          :class="[
            'w-full py-3 px-4 rounded-lg border-2 transition-all text-left',
            profile.budget_distribution === 'equal'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="font-medium">균등 배분</div>
          <div class="text-sm text-gray-600">모든 끼니에 동일한 예산 배정</div>
        </button>

        <button
          @click="profileStore.updateProfile({ budget_distribution: 'weighted' })"
          :class="[
            'w-full py-3 px-4 rounded-lg border-2 transition-all text-left',
            profile.budget_distribution === 'weighted'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="font-medium">차등 배분</div>
          <div class="text-sm text-gray-600">아침 < 점심 < 저녁 (비율: 2:3:3.5:1.5)</div>
        </button>
      </div>
    </div>

    <!-- Per-Meal Budget Preview -->
    <div class="bg-gray-50 p-4 rounded-lg">
      <div class="text-sm font-medium mb-3">끼니당 예산 환산</div>
      <div class="grid grid-cols-2 gap-3">
        <div
          v-for="(budget, mealType) in profileStore.perMealBudgetsByType"
          :key="mealType"
          class="bg-white p-3 rounded-lg"
        >
          <div class="text-xs text-gray-600">{{ mealType }}</div>
          <div class="text-lg font-bold text-blue-600">{{ budget.toLocaleString() }}원</div>
        </div>
      </div>
    </div>

    <!-- Final Review -->
    <div class="bg-blue-50 p-4 rounded-lg space-y-3">
      <div class="font-medium text-blue-900">📋 최종 확인</div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">기본 정보</div>
          <div class="font-medium">
            {{ profile.gender === 'male' ? '남성' : '여성' }} / {{ profile.age }}세 / 
            {{ profile.height }}cm / {{ profile.weight }}kg
          </div>
        </div>

        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">목표 및 활동량</div>
          <div class="font-medium">{{ profile.goal }} / {{ profile.activity_level }}</div>
        </div>

        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">예상 칼로리</div>
          <div class="font-medium text-blue-600">{{ targetCalories.toLocaleString() }} kcal/일</div>
        </div>

        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">식단 구성</div>
          <div class="font-medium">{{ profile.days }}일 / {{ profile.meals_per_day }}끼 (총 {{ profile.days * profile.meals_per_day }}끼)</div>
        </div>

        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">제한 사항</div>
          <div class="font-medium">
            알레르기 {{ profile.allergies.length }}개 / 
            건강 제약 {{ profile.health_conditions.length }}개
          </div>
        </div>

        <div class="bg-white p-3 rounded">
          <div class="text-gray-600">총 예산</div>
          <div class="font-medium text-green-600">
            {{ profile.budget.toLocaleString() }}원
            <span class="text-xs text-gray-500">
              ({{ profile.budget_type === 'weekly' ? '주간' : profile.budget_type === 'daily' ? '일간' : '끼니당' }})
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Validation Message -->
    <div v-if="!isValid" class="text-sm text-orange-600 bg-orange-50 p-3 rounded-lg">
      예산 정보를 입력해주세요.
    </div>
  </div>
</template>
