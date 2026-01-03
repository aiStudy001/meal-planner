<script setup lang="ts">
import { computed } from 'vue'
import { useProfileStore } from '@/stores/profile'
import { GOALS, ACTIVITY_LEVELS } from '@/constants'

const profileStore = useProfileStore()
const profile = computed(() => profileStore.profile)

// Validation
const isValid = computed(() => {
  return (
    profile.value.gender &&
    profile.value.age > 0 &&
    profile.value.age < 120 &&
    profile.value.height > 0 &&
    profile.value.height < 250 &&
    profile.value.weight > 0 &&
    profile.value.weight < 300 &&
    profile.value.goal &&
    profile.value.activity_level
  )
})

defineExpose({ isValid })
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold mb-4">기본 정보</h2>

    <!-- Gender -->
    <div>
      <label class="block text-sm font-medium mb-2">성별</label>
      <div class="flex gap-4">
        <button
          @click="profileStore.updateProfile({ gender: 'male' })"
          :class="[
            'flex-1 py-3 px-4 rounded-lg border-2 transition-all',
            profile.gender === 'male'
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          남성
        </button>
        <button
          @click="profileStore.updateProfile({ gender: 'female' })"
          :class="[
            'flex-1 py-3 px-4 rounded-lg border-2 transition-all',
            profile.gender === 'female'
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          여성
        </button>
      </div>
    </div>

    <!-- Age, Height, Weight -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label class="block text-sm font-medium mb-2">나이 (세)</label>
        <input
          type="number"
          :value="profile.age"
          @input="profileStore.updateProfile({ age: Number(($event.target as HTMLInputElement).value) })"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="25"
          min="1"
          max="120"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-2">키 (cm)</label>
        <input
          type="number"
          :value="profile.height"
          @input="profileStore.updateProfile({ height: Number(($event.target as HTMLInputElement).value) })"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="170"
          min="1"
          max="250"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-2">체중 (kg)</label>
        <input
          type="number"
          :value="profile.weight"
          @input="profileStore.updateProfile({ weight: Number(($event.target as HTMLInputElement).value) })"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="65"
          min="1"
          max="300"
        />
      </div>
    </div>

    <!-- Goal -->
    <div>
      <label class="block text-sm font-medium mb-2">목표</label>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button
          v-for="goal in GOALS"
          :key="goal.value"
          @click="profileStore.updateProfile({ goal: goal.value as typeof profile.goal })"
          :class="[
            'py-3 px-4 rounded-lg border-2 transition-all text-center',
            profile.goal === goal.value
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="text-2xl mb-1">{{ goal.emoji }}</div>
          <div class="text-sm font-medium">{{ goal.value }}</div>
          <div class="text-xs text-gray-500">{{ goal.description }}</div>
        </button>
      </div>
    </div>

    <!-- Activity Level -->
    <div>
      <label class="block text-sm font-medium mb-2">활동 수준</label>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <button
          v-for="level in ACTIVITY_LEVELS"
          :key="level.value"
          @click="profileStore.updateProfile({ activity_level: level.value as typeof profile.activity_level })"
          :class="[
            'py-3 px-4 rounded-lg border-2 transition-all text-left',
            profile.activity_level === level.value
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="font-medium">{{ level.label }} <span class="text-xs text-gray-500">{{ level.multiplier }}</span></div>
          <div class="text-sm text-gray-600">{{ level.description }}</div>
        </button>
      </div>
    </div>

    <!-- Validation Message -->
    <div v-if="!isValid" class="text-sm text-orange-600 bg-orange-50 p-3 rounded-lg">
      모든 필수 항목을 입력해주세요.
    </div>
  </div>
</template>
