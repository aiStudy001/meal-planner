<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { scenarios } from '@/data/scenarios'

const router = useRouter()
const profileStore = useProfileStore()
const selectedScenarioId = ref<string>('')

function loadScenario() {
  if (!selectedScenarioId.value) {
    return
  }

  const scenario = scenarios.find(s => s.id === selectedScenarioId.value)
  if (scenario) {
    // Update profile store with scenario data
    profileStore.updateProfile(scenario.profile)

    // Navigate to input page
    router.push('/input')
  }
}
</script>

<template>
  <div class="bg-gradient-to-r from-blue-50 to-indigo-50 p-8 rounded-lg shadow-md">
    <div class="text-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-2">
        🎯 빠른 시작
      </h2>
      <p class="text-gray-600">
        미리 준비된 시나리오로 바로 시작해보세요
      </p>
    </div>

    <div class="flex flex-col sm:flex-row gap-4 items-center justify-center">
      <select
        v-model="selectedScenarioId"
        class="w-full sm:w-auto px-4 py-3 text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        <option value="" disabled>시나리오 선택</option>
        <option
          v-for="scenario in scenarios"
          :key="scenario.id"
          :value="scenario.id"
        >
          {{ scenario.name }} - {{ scenario.description }}
        </option>
      </select>

      <button
        @click="loadScenario"
        :disabled="!selectedScenarioId"
        class="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed whitespace-nowrap"
      >
        불러오기
      </button>
    </div>

    <div class="mt-4 text-center">
      <p class="text-sm text-gray-500">
        4가지 다양한 시나리오: 체중 감량, 체중 증가, 알레르기, 건강 제약
      </p>
    </div>
  </div>
</template>
