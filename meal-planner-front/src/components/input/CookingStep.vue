<script setup lang="ts">
import { computed } from 'vue'
import { useProfileStore } from '@/stores/profile'

const profileStore = useProfileStore()
const profile = computed(() => profileStore.profile)

const cookingTimeOptions = ['15분 이내', '30분 이내', '제한 없음']
const skillLevelOptions = ['초급', '중급', '고급']

// Validation
const isValid = computed(() => {
  return (
    profile.value.cooking_time &&
    profile.value.skill_level &&
    profile.value.meals_per_day > 0 &&
    profile.value.days > 0
  )
})

defineExpose({ isValid })
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold mb-4">조리 설정</h2>

    <!-- Cooking Time -->
    <div>
      <label class="block text-sm font-medium mb-2">조리 시간</label>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="time in cookingTimeOptions"
          :key="time"
          @click="profileStore.updateProfile({ cooking_time: time as typeof profile.cooking_time })"
          :class="[
            'py-3 px-4 rounded-lg border-2 transition-all text-center',
            profile.cooking_time === time
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ time }}
        </button>
      </div>
    </div>

    <!-- Skill Level -->
    <div>
      <label class="block text-sm font-medium mb-2">조리 난이도</label>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="skill in skillLevelOptions"
          :key="skill"
          @click="profileStore.updateProfile({ skill_level: skill as typeof profile.skill_level })"
          :class="[
            'py-3 px-4 rounded-lg border-2 transition-all text-center',
            profile.skill_level === skill
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ skill }}
        </button>
      </div>
    </div>

    <!-- Meals Per Day -->
    <div>
      <label class="block text-sm font-medium mb-2">하루 끼니 수</label>
      <div class="flex items-center gap-4">
        <input
          type="range"
          :value="profile.meals_per_day"
          @input="profileStore.updateProfile({ meals_per_day: Number(($event.target as HTMLInputElement).value) })"
          min="1"
          max="4"
          step="1"
          class="flex-1"
        />
        <div class="text-2xl font-bold text-blue-600 w-16 text-center">
          {{ profile.meals_per_day }}끼
        </div>
      </div>
      <div class="text-xs text-gray-500 mt-2">
        {{ profile.meals_per_day === 1 ? '점심' :
           profile.meals_per_day === 2 ? '아침 + 저녁' :
           profile.meals_per_day === 3 ? '아침 + 점심 + 저녁' :
           '아침 + 점심 + 저녁 + 간식' }}
      </div>
    </div>

    <!-- Days -->
    <div>
      <label class="block text-sm font-medium mb-2">식단 기간 (일)</label>
      <div class="flex items-center gap-4">
        <input
          type="range"
          :value="profile.days"
          @input="profileStore.updateProfile({ days: Number(($event.target as HTMLInputElement).value) })"
          min="1"
          max="7"
          step="1"
          class="flex-1"
        />
        <div class="text-2xl font-bold text-blue-600 w-16 text-center">
          {{ profile.days }}일
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div class="bg-blue-50 p-4 rounded-lg">
      <div class="text-sm text-blue-800">
        <div class="font-medium mb-2">📋 요약</div>
        <div>총 <span class="font-bold">{{ profile.days * profile.meals_per_day }}끼</span>의 식단이 생성됩니다</div>
      </div>
    </div>

    <!-- Validation Message -->
    <div v-if="!isValid" class="text-sm text-orange-600 bg-orange-50 p-3 rounded-lg">
      모든 항목을 선택해주세요.
    </div>
  </div>
</template>
