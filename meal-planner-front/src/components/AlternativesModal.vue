<script setup lang="ts">
import type { Meal, MealPlan } from '@/types'
import { useAlternativeRecipes, type AlternativeRecipe } from '@/composables/useAlternativeRecipes'

interface Props {
  meal: Meal
  day: number
  mealPlan: MealPlan
  alternatives: AlternativeRecipe[]
  isLoading: boolean
  error: string | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

// Composables (only for applyAlternative function)
const { applyAlternative } = useAlternativeRecipes()

/**
 * Apply selected alternative recipe
 */
function handleApplyAlternative(recipe: AlternativeRecipe) {
  applyAlternative(props.day, props.meal.meal_type, recipe)
  emit('close')
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-container">
      <!-- Header -->
      <div class="modal-header">
        <h2 class="modal-title">비슷한 레시피 찾기</h2>
        <button class="close-button" @click="emit('close')">✕</button>
      </div>

      <!-- Current Recipe Reference -->
      <div class="current-recipe">
        <h3 class="section-title">현재 레시피 (참고)</h3>
        <div class="current-recipe-card">
          <div class="recipe-name">{{ meal.recipe.name }}</div>
          <div class="recipe-stats">
            <span>{{ meal.recipe.nutrition.calories_kcal }}kcal</span>
            <span>{{ meal.recipe.estimated_cost.toLocaleString() }}원</span>
            <span>{{ meal.recipe.cooking_time_min }}분</span>
          </div>
        </div>
      </div>

      <!-- Alternative Recipes -->
      <div class="alternatives-section">
        <h3 class="section-title">대체 레시피 후보</h3>

        <!-- Loading State -->
        <div v-if="props.isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>비슷한 레시피를 검색하는 중...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="props.error" class="error-state">
          <p>⚠️ {{ props.error }}</p>
        </div>

        <!-- Empty State -->
        <div v-else-if="props.alternatives.length === 0" class="empty-state">
          <p>😕 비슷한 레시피를 찾지 못했습니다</p>
          <p class="hint">다른 조건으로 다시 시도해보세요</p>
        </div>

        <!-- Alternatives List -->
        <div v-else class="alternatives-list">
          <div
            v-for="(recipe, index) in props.alternatives"
            :key="index"
            class="alternative-card"
          >
            <div class="card-header">
              <div class="recipe-name">{{ recipe.name }}</div>
              <div class="recipe-difficulty">{{ recipe.difficulty }}</div>
            </div>

            <div class="recipe-stats">
              <div v-if="recipe.calories" class="stat-item">
                <span class="label">칼로리</span>
                <span class="value">{{ recipe.calories }}kcal</span>
              </div>
              <div v-if="recipe.cost" class="stat-item">
                <span class="label">비용</span>
                <span class="value">{{ recipe.cost.toLocaleString() }}원</span>
              </div>
              <div v-if="recipe.cooking_time" class="stat-item">
                <span class="label">조리시간</span>
                <span class="value">{{ recipe.cooking_time }}분</span>
              </div>
            </div>

            <div v-if="recipe.ingredients.length > 0" class="recipe-ingredients">
              <span class="label">재료:</span>
              <span class="ingredients-text">
                {{ recipe.ingredients.slice(0, 3).join(', ') }}
                <span v-if="recipe.ingredients.length > 3" class="more">
                  외 {{ recipe.ingredients.length - 3 }}개
                </span>
              </span>
            </div>

            <div v-if="recipe.content_preview" class="recipe-preview">
              {{ recipe.content_preview.slice(0, 100) }}...
            </div>

            <a
              v-if="recipe.url"
              :href="recipe.url"
              target="_blank"
              rel="noopener noreferrer"
              class="recipe-link"
            >
              원본 레시피 보기 →
            </a>

            <button class="apply-button" @click="handleApplyAlternative(recipe)">
              ✅ 이 레시피로 변경
            </button>
          </div>
        </div>
      </div>

      <!-- Footer Note -->
      <div class="modal-footer">
        <p class="disclaimer">
          ℹ️ 영양 정보는 추정치이며 실제와 다를 수 있습니다
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
  max-width: 800px;
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

.current-recipe {
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.current-recipe-card {
  background: #f9fafb;
  border-radius: 12px;
  padding: 16px;
}

.recipe-name {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.recipe-stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #6b7280;
}

.alternatives-section {
  padding: 24px;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.loading-state .spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-state p,
.error-state p,
.empty-state p {
  margin: 8px 0;
  color: #6b7280;
  font-size: 16px;
}

.empty-state .hint {
  font-size: 14px;
  color: #9ca3af;
}

.error-state p {
  color: #ef4444;
}

.alternatives-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alternative-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s ease;
}

.alternative-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.alternative-card .recipe-name {
  flex: 1;
  margin-bottom: 0;
}

.recipe-difficulty {
  padding: 4px 12px;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.alternative-card .recipe-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
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
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

.recipe-ingredients {
  margin-bottom: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.recipe-ingredients .label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
  margin-right: 8px;
}

.ingredients-text {
  font-size: 14px;
  color: #374151;
}

.ingredients-text .more {
  color: #6b7280;
  font-style: italic;
  margin-left: 4px;
}

.recipe-preview {
  margin-bottom: 12px;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
}

.recipe-link {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 14px;
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.recipe-link:hover {
  text-decoration: underline;
}

.apply-button {
  width: 100%;
  padding: 12px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.apply-button:hover {
  background: #059669;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.disclaimer {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  text-align: center;
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

  .alternative-card .recipe-stats {
    grid-template-columns: 1fr;
  }
}
</style>
