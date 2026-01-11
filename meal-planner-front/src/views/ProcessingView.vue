<script setup lang="ts">
import { useMealPlanStore } from '@/stores/mealPlan'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePDFExport } from '@/composables/usePDFExport'
import { useMealPlanStorage } from '@/composables/useMealPlanStorage'
import ShoppingListModal from '@/components/ShoppingListModal.vue'
import SavedPlansModal from '@/components/SavedPlansModal.vue'
import MealCard from '@/components/MealCard.vue'

const mealPlanStore = useMealPlanStore()
const router = useRouter()
const { exportToPDF } = usePDFExport()
const { saveMealPlan } = useMealPlanStorage()

const isComplete = computed(() => mealPlanStore.totalProgress >= 100)
const hasError = computed(() => mealPlanStore.hasError)
const errorMessage = computed(() => mealPlanStore.errorMessage)
const showErrorBanner = ref(true)
const showShoppingList = ref(false)
const showSavedPlans = ref(false)

function startOver() {
  mealPlanStore.clearMealPlan()
  window.location.href = '/'
}

function retryGeneration() {
  mealPlanStore.clearMealPlan()
  router.push('/input')
}

function goHome() {
  mealPlanStore.clearMealPlan()
  router.push('/')
}

function dismissError() {
  showErrorBanner.value = false
}

function exportToJSON() {
  if (!mealPlanStore.mealPlan) return

  const jsonStr = JSON.stringify(mealPlanStore.mealPlan, null, 2)
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `meal-plan-${new Date().toISOString().split('T')[0]}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function handleSavePlan() {
  if (!mealPlanStore.mealPlan) return
  const success = saveMealPlan(mealPlanStore.mealPlan)
  if (success) {
    alert('✅ 식단이 저장되었습니다!')
  } else {
    alert('❌ 식단 저장에 실패했습니다.')
  }
}
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <!-- 헤더 -->
    <h1 v-if="isComplete" class="text-3xl font-bold text-center mb-8">
      🎉 식단이 완성되었습니다!
    </h1>
    <h1 v-else class="text-3xl font-bold text-center mb-8">식단 생성 중...</h1>

    <!-- 에러 배너 (진행 중일 때만 표시) -->
    <div v-if="hasError && !isComplete && showErrorBanner" class="bg-red-50 border-l-4 border-red-500 rounded-lg p-6 mb-6">
      <div class="flex justify-between items-start">
        <div class="flex items-start gap-3 flex-1">
          <div class="text-2xl">🚨</div>
          <div class="flex-1">
            <h3 class="font-bold text-red-700 mb-2">오류가 발생했습니다</h3>
            <p class="text-sm text-red-600 mb-4">{{ errorMessage }}</p>
            <div class="flex gap-2">
              <button
                @click="retryGeneration"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                다시 시도
              </button>
              <button
                @click="goHome"
                class="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm font-medium"
              >
                처음으로
              </button>
            </div>
          </div>
        </div>
        <button
          @click="dismissError"
          class="text-red-400 hover:text-red-600 text-xl font-bold ml-4"
          title="닫기"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- 완료 UI (100%) -->
    <div v-if="isComplete" class="space-y-6">
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
        v-for="day in mealPlanStore.mealPlan?.days || []"
        :key="day.day"
        class="bg-white rounded-lg shadow-md p-6"
      >
        <h3 class="text-xl font-bold mb-4">{{ day.day }}일차</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MealCard
            v-for="meal in day.meals"
            :key="`${day.day}-${meal.meal_type}`"
            :meal="meal"
            :day="day.day"
            :meal-plan="mealPlanStore.mealPlan!"
            :is-complete="isComplete"
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="flex flex-col items-center gap-4 pt-4">
        <div class="flex flex-wrap justify-center gap-3">
          <button
            @click="() => exportToPDF(mealPlanStore.mealPlan!)"
            class="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center gap-2"
          >
            📄 PDF
          </button>
<!--           <button -->
<!--             @click="exportToJSON" -->
<!--             class="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center gap-2" -->
<!--           > -->
<!--             💾 JSON -->
<!--           </button> -->
          <button
            @click="showShoppingList = true"
            class="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium flex items-center gap-2"
          >
            🛒 장보기 리스트
          </button>
          <button
            @click="handleSavePlan"
            class="px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium flex items-center gap-2"
          >
            💾 식단 저장
          </button>
          <button
            @click="showSavedPlans = true"
            class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium flex items-center gap-2"
          >
            📂 저장된 식단
          </button>
        </div>
        <button
          @click="startOver"
          class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          새 식단 만들기
        </button>
      </div>
    </div>

    <!-- 진행 중 UI -->
    <div v-else>
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
      <div v-if="mealPlanStore.mealPlan?.days.length > 0" class="space-y-6">
        <div
          v-for="day in mealPlanStore.mealPlan.days"
          :key="day.day"
          class="bg-white rounded-lg shadow-md p-6"
        >
          <h3 class="text-xl font-bold mb-4">{{ day.day }}일차</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MealCard
              v-for="meal in day.meals"
              :key="`${day.day}-${meal.meal_type}`"
              :meal="meal"
              :day="day.day"
              :meal-plan="mealPlanStore.mealPlan"
              :is-complete="false"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Shopping List Modal -->
    <ShoppingListModal
      v-if="mealPlanStore.mealPlan"
      :meal-plan="mealPlanStore.mealPlan"
      :show="showShoppingList"
      @close="showShoppingList = false"
    />

    <!-- Saved Plans Modal -->
    <SavedPlansModal
      :show="showSavedPlans"
      @close="showSavedPlans = false"
    />
  </div>
</template>
