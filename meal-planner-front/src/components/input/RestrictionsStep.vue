<script setup lang="ts">
import { computed } from 'vue'
import { useProfileStore } from '@/stores/profile'
import { ALLERGIES, DIETARY_PREFERENCES, HEALTH_CONDITIONS } from '@/constants'

const profileStore = useProfileStore()
const profile = computed(() => profileStore.profile)

// Toggle functions
function toggleAllergy(allergy: string) {
  const current = profile.value.allergies
  if (current.includes(allergy)) {
    profileStore.updateProfile({
      allergies: current.filter((a) => a !== allergy)
    })
  } else {
    profileStore.updateProfile({
      allergies: [...current, allergy]
    })
  }
}

function toggleDietaryPreference(pref: string) {
  const current = profile.value.dietary_preferences
  if (current.includes(pref)) {
    profileStore.updateProfile({
      dietary_preferences: current.filter((p) => p !== pref)
    })
  } else {
    profileStore.updateProfile({
      dietary_preferences: [...current, pref]
    })
  }
}

function toggleHealthCondition(condition: string) {
  const current = profile.value.health_conditions
  if (current.includes(condition)) {
    profileStore.updateProfile({
      health_conditions: current.filter((c) => c !== condition)
    })
  } else {
    profileStore.updateProfile({
      health_conditions: [...current, condition]
    })
  }
}

// Always valid (optional step)
const isValid = computed(() => true)

defineExpose({ isValid })
</script>

<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold mb-4">제한 사항</h2>

    <!-- Allergies -->    <div>
      <label class="block text-sm font-medium mb-2">알레르기 (선택 사항)</label>
      <p class="text-xs text-gray-500 mb-3">해당하는 알레르기 항목을 선택해주세요</p>
      <div class="grid grid-cols-3 md:grid-cols-4 gap-2">
        <button
          v-for="allergy in ALLERGIES"
          :key="allergy"
          @click="toggleAllergy(allergy)"
          :class="[
            'py-2 px-3 rounded-lg border transition-all text-sm',
            profile.allergies.includes(allergy)
              ? 'border-red-500 bg-red-50 text-red-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ allergy }}
        </button>
      </div>
    </div>

    <!-- Dietary Preferences -->
    <div>
      <label class="block text-sm font-medium mb-2">식이 선호 (선택 사항)</label>
      <p class="text-xs text-gray-500 mb-3">선호하는 식습관을 선택해주세요</p>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <button
          v-for="pref in DIETARY_PREFERENCES"
          :key="pref"
          @click="toggleDietaryPreference(pref)"
          :class="[
            'py-2 px-3 rounded-lg border transition-all text-sm',
            profile.dietary_preferences.includes(pref)
              ? 'border-green-500 bg-green-50 text-green-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ pref }}
        </button>
      </div>
    </div>

    <!-- Health Conditions -->
    <div>
      <label class="block text-sm font-medium mb-2">건강 상태 (선택 사항)</label>
      <p class="text-xs text-gray-500 mb-3">해당하는 건강 제약이 있다면 선택해주세요</p>
      <div class="space-y-3">
        <button
          v-for="condition in HEALTH_CONDITIONS"
          :key="condition.value"
          @click="toggleHealthCondition(condition.value)"
          :class="[
            'w-full py-3 px-4 rounded-lg border-2 transition-all text-left',
            profile.health_conditions.includes(condition.value)
              ? 'border-orange-500 bg-orange-50'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          <div class="flex items-start justify-between">
            <div>
              <div class="font-medium">{{ condition.value }}</div>
              <div class="text-sm text-gray-600 mt-1">{{ condition.description }}</div>
            </div>
            <div
              v-if="profile.health_conditions.includes(condition.value)"
              class="text-orange-500 font-bold text-xl"
            >
              ✓
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Info Note -->
    <div class="text-sm text-blue-600 bg-blue-50 p-3 rounded-lg">
      ℹ️ 선택하신 제한 사항은 식단 생성 시 자동으로 고려됩니다.
    </div>
  </div>
</template>
