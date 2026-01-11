<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMealPlanStorage, type SavedPlanMetadata } from '@/composables/useMealPlanStorage'
import { useMealPlanStore } from '@/stores/mealPlan'

interface Props {
  show: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

// Composables
const { savedPlans, loadSavedPlans, loadMealPlan, deleteMealPlan, getStorageInfo } = useMealPlanStorage()
const mealPlanStore = useMealPlanStore()

// Local state
const confirmDelete = ref<string | null>(null)
const storageInfo = ref({ count: 0, maxCount: 5, usageBytes: 0 })

/**
 * Load saved plans on mount
 */
onMounted(() => {
  loadSavedPlans()
  storageInfo.value = getStorageInfo()
})

/**
 * Format timestamp for display
 */
function formatDate(isoString: string): string {
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * Load a saved meal plan
 */
function handleLoad(id: string) {
  const plan = loadMealPlan(id)
  if (plan) {
    mealPlanStore.mealPlan = plan
    console.log('Meal plan loaded from storage:', id)
    emit('close')
  }
}

/**
 * Delete a saved meal plan with confirmation
 */
function handleDelete(id: string) {
  if (confirmDelete.value !== id) {
    confirmDelete.value = id
    // Reset confirmation after 3 seconds
    setTimeout(() => {
      confirmDelete.value = null
    }, 3000)
    return
  }

  const success = deleteMealPlan(id)
  if (success) {
    confirmDelete.value = null
    storageInfo.value = getStorageInfo()
  }
}

/**
 * Cancel delete confirmation
 */
function cancelDelete() {
  confirmDelete.value = null
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-container">
      <!-- Header -->
      <div class="modal-header">
        <h2 class="modal-title">저장된 식단</h2>
        <button class="close-button" @click="emit('close')">✕</button>
      </div>

      <!-- Storage Info -->
      <div class="storage-info">
        <div class="info-item">
          <span class="label">저장된 식단:</span>
          <span class="value">{{ storageInfo.count }} / {{ storageInfo.maxCount }}</span>
        </div>
<!--         <div class="info-item"> -->
<!--           <span class="label">사용 용량:</span> -->
<!--           <span class="value">{{ (storageInfo.usageBytes / 1024).toFixed(1) }} KB</span> -->
<!--         </div> -->
      </div>

      <!-- Plans List -->
      <div class="plans-section">
        <!-- Empty State -->
        <div v-if="savedPlans.length === 0" class="empty-state">
          <p class="empty-icon">📂</p>
          <p class="empty-text">저장된 식단이 없습니다</p>
          <p class="empty-hint">식단 생성 후 "💾 식단 저장" 버튼을 눌러 저장하세요</p>
        </div>

        <!-- Plans List -->
        <div v-else class="plans-list">
          <div
            v-for="plan in savedPlans"
            :key="plan.id"
            class="plan-card"
            :class="{ 'plan-card--deleting': confirmDelete === plan.id }"
          >
            <div class="card-header">
              <div class="plan-title">
                <span class="profile-summary">{{ plan.profile_summary }}</span>
                <span class="plan-date">{{ formatDate(plan.saved_at) }}</span>
              </div>
            </div>

            <div class="plan-stats">
              <div class="stat-item">
                <span class="label">기간</span>
                <span class="value">{{ plan.days }}일</span>
              </div>
              <div class="stat-item">
                <span class="label">총 비용</span>
                <span class="value">{{ plan.total_cost.toLocaleString() }}원</span>
              </div>
              <div class="stat-item">
                <span class="label">일평균</span>
                <span class="value">{{ Math.round(plan.total_cost / plan.days).toLocaleString() }}원</span>
              </div>
            </div>

            <div class="action-buttons">
              <!-- Load Button -->
              <button
                class="btn btn-load"
                :disabled="confirmDelete === plan.id"
                @click="handleLoad(plan.id)"
              >
                📂 불러오기
              </button>

              <!-- Delete Button -->
              <button
                v-if="confirmDelete !== plan.id"
                class="btn btn-delete"
                @click="handleDelete(plan.id)"
              >
                🗑️ 삭제
              </button>

              <!-- Confirm Delete Buttons -->
              <button
                v-else
                class="btn btn-delete-confirm"
                @click="handleDelete(plan.id)"
              >
                ✅ 확인: 삭제
              </button>
              <button
                v-if="confirmDelete === plan.id"
                class="btn btn-cancel"
                @click="cancelDelete"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer Note -->
      <div class="modal-footer">
        <p class="footer-note">
          ℹ️ 최대 {{ storageInfo.maxCount }}개 식단 저장 가능 (초과 시 가장 오래된 식단 자동 삭제)
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: white;
  border-radius: 16px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.close-button {
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  border-radius: 8px;
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: #e5e7eb;
}

.storage-info {
  display: flex;
  gap: 24px;
  padding: 16px 24px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.info-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.info-item .label {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.info-item .value {
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

.plans-section {
  padding: 24px;
  min-height: 200px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  margin: 0 0 16px 0;
}

.empty-text {
  font-size: 18px;
  color: #6b7280;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.empty-hint {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

.plans-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s ease;
}

.plan-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.plan-card--deleting {
  border-color: #ef4444;
  background: #fef2f2;
}

.card-header {
  margin-bottom: 16px;
}

.plan-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.profile-summary {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.plan-date {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.plan-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item .label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.stat-item .value {
  font-size: 16px;
  color: #1f2937;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-load {
  background: #3b82f6;
  color: white;
}

.btn-load:hover:not(:disabled) {
  background: #2563eb;
}

.btn-delete {
  background: #ef4444;
  color: white;
}

.btn-delete:hover:not(:disabled) {
  background: #dc2626;
}

.btn-delete-confirm {
  background: #dc2626;
  color: white;
  animation: pulse 0.5s ease-in-out;
}

.btn-cancel {
  background: #6b7280;
  color: white;
}

.btn-cancel:hover {
  background: #4b5563;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.footer-note {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  text-align: center;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@media (max-width: 640px) {
  .modal-overlay {
    padding: 0;
    align-items: flex-end;
  }

  .modal-container {
    max-height: 95vh;
    border-radius: 16px 16px 0 0;
  }

  .storage-info {
    flex-direction: column;
    gap: 8px;
  }

  .plan-stats {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
