<script setup lang="ts">
import { useMealPlanStore } from '@/stores/mealPlan'
import { VALIDATORS } from '@/constants'
import { computed } from 'vue'

const mealPlanStore = useMealPlanStore()

const isComplete = computed(() => mealPlanStore.totalProgress >= 100)

function startOver() {
  mealPlanStore.clearMealPlan()
  window.location.href = '/'
}
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <!-- 완료 상태 헤더 -->
    <h1 v-if="isComplete" class="text-3xl font-bold text-center mb-8">
      🎉 식단이 완성되었습니다!
    </h1>
    <h1 v-else class="text-3xl font-bold text-center mb-8">식단 생성 중...</h1>

    <!-- 진행 중 UI (100% 미만) -->
    <div v-if="!isComplete">
      <!-- Progress Bar -->
      <div class="mb-8">
        <div class="flex justify-between mb-2">
          <span class="text-sm font-medium text-gray-700">진행률</span>
          <span class="text-sm font-medium text-gray-700">{{ mealPlanStore.totalProgress }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-4">
          <div
            class="bg-blue-600 h-4 rounded-full transition-all duration-300"
            :style="{ width: mealPlanStore.totalProgress + '%' }"
          ></div>
        </div>
      </div>

      <!-- Validation Status (5 validators) -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">검증 상태</h2>
        <div class="grid grid-cols-5 gap-4">
          <div
            v-for="validator in VALIDATORS"
            :key="validator.key"
            class="text-center"
          >
            <div class="text-3xl mb-2">{{ validator.icon }}</div>
            <div class="text-sm font-medium mb-1">{{ validator.label }}</div>
            <div
              :class="[
                'text-xs px-2 py-1 rounded',
                mealPlanStore.validationState[validator.key as keyof typeof mealPlanStore.validationState] === 'passed'
                  ? 'bg-green-100 text-green-800'
                  : mealPlanStore.validationState[validator.key as keyof typeof mealPlanStore.validationState] === 'failed'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-gray-100 text-gray-600'
              ]"
            >
              {{
                mealPlanStore.validationState[validator.key as keyof typeof mealPlanStore.validationState] === 'passed'
                  ? '통과'
                  : mealPlanStore.validationState[validator.key as keyof typeof mealPlanStore.validationState] === 'failed'
                  ? '실패'
                  : '대기 중'
              }}
            </div>
          </div>
        </div>
      </div>

      <!-- Current Status -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">현재 상태</h2>
        <p class="text-gray-700">
          {{ mealPlanStore.currentDay }}일차 {{ mealPlanStore.currentMealType || '준비 중' }} 생성 중...
        </p>
        <p v-if="mealPlanStore.processingState.retry_count > 0" class="text-orange-600 mt-2">
          재시도 횟수: {{ mealPlanStore.processingState.retry_count }}
        </p>
      </div>

      <!-- Completed Meals (진행 중) -->
      <div v-if="mealPlanStore.completedMeals.length > 0" class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-bold mb-4">완료된 식단</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(meal, index) in mealPlanStore.completedMeals"
            :key="index"
            class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-800">
                  {{ meal.day }}일차 {{ meal.meal_type }}
                </span>
                <span class="text-green-600">✅</span>
              </div>
            </div>
            <p class="text-lg font-medium text-gray-900 mb-2">{{ meal.menu_name }}</p>
            <div class="flex gap-4 text-sm text-gray-600">
              <span>{{ meal.calories }}kcal</span>
              <span>{{ meal.cost.toLocaleString() }}원</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 완료 UI (100%) -->
    <div v-else class="space-y-6">
      <!-- Summary -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold mb-4">요약</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-gray-600 text-sm">총 끼니</p>
            <p class="text-2xl font-bold">{{ mealPlanStore.completedMeals.length }}끼</p>
          </div>
          <div>
            <p class="text-gray-600 text-sm">평균 칼로리</p>
            <p class="text-2xl font-bold">
              {{ Math.round(mealPlanStore.completedMeals.reduce((sum, m) => sum + m.calories, 0) / mealPlanStore.completedMeals.length) }}kcal
            </p>
          </div>
          <div>
            <p class="text-gray-600 text-sm">총 비용</p>
            <p class="text-2xl font-bold">
              {{ mealPlanStore.completedMeals.reduce((sum, m) => sum + m.cost, 0).toLocaleString() }}원
            </p>
          </div>
        </div>
      </div>

      <!-- Completed Meals by Day -->
      <div
        v-for="day in Array.from(new Set(mealPlanStore.completedMeals.map(m => m.day))).sort((a, b) => a - b)"
        :key="day"
        class="bg-white rounded-lg shadow-md p-6"
      >
        <h3 class="text-xl font-bold mb-4">{{ day }}일차</h3>
        <div class="space-y-4">
          <div
            v-for="meal in mealPlanStore.completedMeals.filter(m => m.day === day)"
            :key="meal.meal_type"
            class="border-l-4 border-blue-500 pl-4"
          >
            <div class="flex justify-between items-start">
              <div>
                <h4 class="font-semibold text-lg">{{ meal.meal_type }}: {{ meal.menu_name }}</h4>
                <p class="text-gray-600 text-sm">
                  {{ meal.calories }}kcal | {{ meal.cost.toLocaleString() }}원
                </p>
              </div>
              <span class="text-green-600 text-xl">✅</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-center gap-4 pt-4">
        <button
          @click="startOver"
          class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          새 식단 만들기
        </button>
      </div>
    </div>
  </div>
</template>
