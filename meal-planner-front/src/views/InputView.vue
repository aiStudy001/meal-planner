<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { useSSE } from '@/composables/useSSE'
import StepIndicator from '@/components/input/StepIndicator.vue'
import BasicInfoStep from '@/components/input/BasicInfoStep.vue'
import RestrictionsStep from '@/components/input/RestrictionsStep.vue'
import CookingStep from '@/components/input/CookingStep.vue'
import BudgetStep from '@/components/input/BudgetStep.vue'

const router = useRouter()
const profileStore = useProfileStore()
const { startGeneration } = useSSE()

const currentStep = ref(1)
const totalSteps = 4

// Refs for step components
const basicInfoStepRef = ref<InstanceType<typeof BasicInfoStep>>()
const restrictionsStepRef = ref<InstanceType<typeof RestrictionsStep>>()
const cookingStepRef = ref<InstanceType<typeof CookingStep>>()
const budgetStepRef = ref<InstanceType<typeof BudgetStep>>()

// Check if current step is valid
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 1:
      return basicInfoStepRef.value?.isValid ?? false
    case 2:
      return restrictionsStepRef.value?.isValid ?? false
    case 3:
      return cookingStepRef.value?.isValid ?? false
    case 4:
      return budgetStepRef.value?.isValid ?? false
    default:
      return false
  }
})

function nextStep() {
  if (canProceed.value && currentStep.value < totalSteps) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

async function startMealPlanGeneration() {
  if (!canProceed.value) return

  try {
    await startGeneration(profileStore.profile)
    router.push('/processing')
  } catch (error) {
    console.error('Failed to start generation:', error)
    alert('식단 생성을 시작할 수 없습니다. 다시 시도해주세요.')
  }
}
</script>

<template>
  <div class="container mx-auto px-4 py-8 max-w-4xl">
    <h1 class="text-3xl font-bold text-center mb-8">식단 정보 입력</h1>

    <!-- Step Indicator -->
    <StepIndicator :current-step="currentStep" :total-steps="totalSteps" />

    <!-- Step Content -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <BasicInfoStep v-if="currentStep === 1" ref="basicInfoStepRef" />
      <RestrictionsStep v-else-if="currentStep === 2" ref="restrictionsStepRef" />
      <CookingStep v-else-if="currentStep === 3" ref="cookingStepRef" />
      <BudgetStep v-else-if="currentStep === 4" ref="budgetStepRef" />
    </div>

    <!-- Navigation Buttons -->
    <div class="flex justify-between">
      <button
        v-if="currentStep > 1"
        @click="prevStep"
        class="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
      >
        ← 이전
      </button>
      <div v-else></div>

      <button
        v-if="currentStep < totalSteps"
        @click="nextStep"
        :disabled="!canProceed"
        :class="[
          'px-6 py-3 rounded-lg transition-colors',
          canProceed
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        ]"
      >
        다음 →
      </button>

      <button
        v-else
        @click="startMealPlanGeneration"
        :disabled="!canProceed"
        :class="[
          'px-8 py-3 rounded-lg transition-colors font-bold',
          canProceed
            ? 'bg-green-600 text-white hover:bg-green-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        ]"
      >
        🍽️ 식단 생성 시작
      </button>
    </div>
  </div>
</template>
