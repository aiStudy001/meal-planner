<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useMealPlanStore } from '@/stores/mealPlan'
import { RECIPE_DB_INFO } from '@/constants'
import { ref } from 'vue'

const router = useRouter()
const mealPlanStore = useMealPlanStore()

// Dummy data for UI preview
const dummyMealPlan = ref({
  days: [
    {
      day: 1,
      meals: [
        {
          meal_type: '아침',
          recipe: {
            name: '닭가슴살 샐러드',
            nutrition: { calories_kcal: 350 },
            cooking_time_min: 15
          },
          budget_allocated: 5000
        },
        {
          meal_type: '점심',
          recipe: {
            name: '현미밥과 구운 연어',
            nutrition: { calories_kcal: 550 },
            cooking_time_min: 25
          },
          budget_allocated: 12000
        },
        {
          meal_type: '저녁',
          recipe: {
            name: '두부 김치찌개',
            nutrition: { calories_kcal: 420 },
            cooking_time_min: 30
          },
          budget_allocated: 8000
        }
      ]
    },
    {
      day: 2,
      meals: [
        {
          meal_type: '아침',
          recipe: {
            name: '그릭 요거트 & 베리',
            nutrition: { calories_kcal: 300 },
            cooking_time_min: 5
          },
          budget_allocated: 6000
        },
        {
          meal_type: '점심',
          recipe: {
            name: '닭가슴살 덮밥',
            nutrition: { calories_kcal: 580 },
            cooking_time_min: 20
          },
          budget_allocated: 9000
        },
        {
          meal_type: '저녁',
          recipe: {
            name: '새우 볶음밥',
            nutrition: { calories_kcal: 490 },
            cooking_time_min: 18
          },
          budget_allocated: 10000
        }
      ]
    },
    {
      day: 3,
      meals: [
        {
          meal_type: '아침',
          recipe: {
            name: '오트밀 & 바나나',
            nutrition: { calories_kcal: 320 },
            cooking_time_min: 10
          },
          budget_allocated: 4000
        },
        {
          meal_type: '점심',
          recipe: {
            name: '소고기 무국',
            nutrition: { calories_kcal: 450 },
            cooking_time_min: 35
          },
          budget_allocated: 11000
        },
        {
          meal_type: '저녁',
          recipe: {
            name: '참치 김밥',
            nutrition: { calories_kcal: 380 },
            cooking_time_min: 15
          },
          budget_allocated: 7000
        }
      ]
    }
  ],
  total_cost: 72000
})

// Use dummy data for preview
const displayMealPlan = mealPlanStore.hasResult ? mealPlanStore.mealPlan : dummyMealPlan.value

function startOver() {
  mealPlanStore.clearMealPlan()
  router.push('/')
}
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <h1 class="text-3xl font-bold text-center mb-8">🎉 식단이 완성되었습니다!</h1>

    <div class="space-y-6">
      <!-- Summary -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold mb-4">요약</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-gray-600 text-sm">총 일수</p>
            <p class="text-2xl font-bold">{{ displayMealPlan.days.length }}일</p>
          </div>
          <div>
            <p class="text-gray-600 text-sm">총 끼니</p>
            <p class="text-2xl font-bold">
              {{ displayMealPlan.days.reduce((sum, day) => sum + day.meals.length, 0) }}끼
            </p>
          </div>
          <div>
            <p class="text-gray-600 text-sm">예상 비용</p>
            <p class="text-2xl font-bold">{{ displayMealPlan.total_cost.toLocaleString() }}원</p>
          </div>
        </div>
      </div>

      <!-- Daily Plans -->
      <div v-for="day in displayMealPlan.days" :key="day.day" class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-xl font-bold mb-4">{{ day.day }}일차</h3>
        <div class="space-y-4">
          <div v-for="meal in day.meals" :key="meal.meal_type" class="border-l-4 border-blue-500 pl-4">
            <h4 class="font-semibold text-lg">{{ meal.meal_type }}: {{ meal.recipe.name }}</h4>
            <p class="text-gray-600 text-sm">
              {{ meal.recipe.nutrition.calories_kcal }}kcal | {{ meal.recipe.cooking_time_min }}분 |
              {{ meal.budget_allocated.toLocaleString() }}원
            </p>
          </div>
        </div>
      </div>

      <!-- Recipe DB Badge -->
      <div class="text-center text-sm text-gray-500 mt-8">
        <div class="inline-block px-4 py-2 bg-gray-100 rounded-full border border-gray-300">
          {{ RECIPE_DB_INFO.total_count.toLocaleString() }}개 {{ RECIPE_DB_INFO.description }}
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-center gap-4">
        <button
          @click="startOver"
          class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          새 식단 만들기
        </button>
      </div>
    </div>
  </div>
</template>
