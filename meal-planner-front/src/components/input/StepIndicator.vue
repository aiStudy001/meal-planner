<script setup lang="ts">
interface Props {
  currentStep: number
  totalSteps: number
}

const props = defineProps<Props>()

const steps = [
  { number: 1, title: '기본 정보' },
  { number: 2, title: '제한 사항' },
  { number: 3, title: '조리 설정' },
  { number: 4, title: '예산 확인' }
]
</script>

<template>
  <div class="mb-8">
    <div class="flex items-center justify-between">
      <div
        v-for="(step, index) in steps"
        :key="step.number"
        class="flex items-center flex-1"
      >
        <!-- Step Circle -->
        <div class="flex flex-col items-center">
          <div
            :class="[
              'w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all',
              currentStep >= step.number
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-500'
            ]"
          >
            {{ step.number }}
          </div>
          <div
            :class="[
              'text-xs mt-2 font-medium',
              currentStep >= step.number ? 'text-blue-600' : 'text-gray-500'
            ]"
          >
            {{ step.title }}
          </div>
        </div>

        <!-- Connector Line -->
        <div
          v-if="index < steps.length - 1"
          :class="[
            'flex-1 h-1 mx-2 transition-all',
            currentStep > step.number ? 'bg-blue-600' : 'bg-gray-200'
          ]"
        ></div>
      </div>
    </div>
  </div>
</template>
