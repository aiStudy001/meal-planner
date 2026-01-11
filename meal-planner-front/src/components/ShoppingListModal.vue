<script setup lang="ts">
import { computed } from 'vue'
import type { MealPlan } from '@/types'
import { useShoppingList, type ShoppingItem } from '@/composables/useShoppingList'

interface Props {
  mealPlan: MealPlan
  show: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

const { generateShoppingList } = useShoppingList()

const shoppingItems = computed<ShoppingItem[]>(() => {
  return generateShoppingList(props.mealPlan)
})

const itemsByCategory = computed(() => {
  const grouped = new Map<string, ShoppingItem[]>()

  shoppingItems.value.forEach(item => {
    if (!grouped.has(item.category)) {
      grouped.set(item.category, [])
    }
    grouped.get(item.category)!.push(item)
  })

  return grouped
})

function closeModal() {
  emit('close')
}
</script>

<template>
  <Transition name="modal">
    <div v-if="show" class="fixed inset-0 z-50 overflow-y-auto">
      <!-- Overlay -->
      <div
        class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        @click="closeModal"
      ></div>

      <!-- Modal -->
      <div class="flex min-h-screen items-center justify-center p-4">
        <div
          class="relative w-full max-w-2xl bg-white rounded-lg shadow-xl transform transition-all"
          @click.stop
        >
          <!-- Header -->
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h3 class="text-2xl font-bold text-gray-900">
                🛒 장보기 리스트
              </h3>
              <button
                @click="closeModal"
                class="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p class="text-sm text-gray-600 mt-2">
              {{ mealPlan.days.length }}일 식단에 필요한 재료 목록
            </p>
          </div>

          <!-- Content -->
          <div class="px-6 py-4 max-h-[60vh] overflow-y-auto">
            <div v-for="[category, items] in itemsByCategory" :key="category" class="mb-6">
              <h4 class="text-lg font-semibold text-gray-800 mb-3 pb-2 border-b-2 border-blue-500">
                {{ category }} ({{ items.length }})
              </h4>

              <ul class="space-y-2">
                <li
                  v-for="(item, index) in items"
                  :key="index"
                  class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
                >
                  <span class="font-medium text-gray-900">
                    {{ item.name }}
                  </span>
                  <span class="text-gray-600 bg-white px-3 py-1 rounded-full text-sm font-semibold">
                    {{ item.quantity % 1 === 0 ? item.quantity : item.quantity.toFixed(1) }} {{ item.unit }}
                  </span>
                </li>
              </ul>
            </div>

            <div v-if="shoppingItems.length === 0" class="text-center py-8 text-gray-500">
              재료 정보를 찾을 수 없습니다.
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div class="flex items-center justify-between">
              <div class="text-sm text-gray-600">
                총 <span class="font-semibold text-blue-600">{{ shoppingItems.length }}</span>개 항목
              </div>
              <button
                @click="closeModal"
                class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
