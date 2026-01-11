<script setup lang="ts">
import { useRouter } from 'vue-router'
import ScenarioSelector from '@/components/ScenarioSelector.vue'

const router = useRouter()

function startPlanning() {
  router.push('/input')
}
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-screen px-4 py-20">
    <div class="max-w-4xl w-full text-center">
      <h1 class="text-5xl font-bold text-gray-900 mb-4">
        🍽️ AI 맞춤 식단 플래너
      </h1>
      <p class="text-xl text-gray-600 mb-8">
        나만의 건강한 식단을 AI가 만들어드립니다
      </p>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="text-4xl mb-3">🥗</div>
          <h3 class="text-lg font-semibold mb-2">영양 균형</h3>
          <p class="text-gray-600 text-sm">
            칼로리, 단백질, 탄수화물, 지방을 맞춤 설정
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="text-4xl mb-3">⏱️</div>
          <h3 class="text-lg font-semibold mb-2">조리 시간 고려</h3>
          <p class="text-gray-600 text-sm">
            바쁜 일상에 맞는 간편한 레시피
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow-md">
          <div class="text-4xl mb-3">💰</div>
          <h3 class="text-lg font-semibold mb-2">예산 관리</h3>
          <p class="text-gray-600 text-sm">
            설정한 예산 내에서 최적의 식단
          </p>
        </div>
      </div>

      <button
        @click="startPlanning"
        class="px-8 py-4 bg-blue-600 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors mb-8"
      >
        직접 입력하기
      </button>

      <div class="flex items-center gap-4 my-6">
        <div class="flex-1 h-px bg-gray-300"></div>
        <span class="text-gray-500 font-medium">또는</span>
        <div class="flex-1 h-px bg-gray-300"></div>
      </div>

      <ScenarioSelector />

      <div class="mt-12 text-sm text-gray-500">
        <p>336,588개 한국 레시피 데이터베이스 기반</p>
      </div>
    </div>
  </div>
</template>
