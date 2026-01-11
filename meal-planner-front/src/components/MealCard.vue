<script setup lang="ts">
import { ref } from 'vue'
import type { Meal, MealPlan } from '@/types'
import { useRegenerateMeal } from '@/composables/useRegenerateMeal'
import { useAlternativeRecipes } from '@/composables/useAlternativeRecipes'
import AlternativesModal from './AlternativesModal.vue'

interface Props {
  meal: Meal
  day: number
  mealPlan: MealPlan
  isComplete: boolean
}

const props = defineProps<Props>()

// Composables
const { isRegenerating, regenerationError, regenerateMeal } = useRegenerateMeal()
const { alternatives, isLoading, error, fetchAlternatives } = useAlternativeRecipes()

// Local state
const showAlternativesModal = ref(false)
const confirmRegenerate = ref(false)

/**
 * Handle meal regeneration with confirmation
 */
async function handleRegenerate() {
  console.log('[MealCard] handleRegenerate called!', { day: props.day, mealType: props.meal.meal_type })

  if (!confirmRegenerate.value) {
    console.log('[MealCard] First click - showing confirmation')
    confirmRegenerate.value = true
    // Reset confirmation after 3 seconds
    setTimeout(() => {
      confirmRegenerate.value = false
    }, 3000)
    return
  }

  console.log('[MealCard] Confirmed - starting regeneration')
  try {
    await regenerateMeal(props.mealPlan, props.day, props.meal.meal_type)
    confirmRegenerate.value = false
  } catch (error) {
    console.error('Failed to regenerate meal:', error)
  }
}

/**
 * Show alternatives modal and fetch recipes
 */
async function handleShowAlternatives() {
  showAlternativesModal.value = true
  await fetchAlternatives(props.meal, props.mealPlan)
}
</script>

<template>
  <div
    class="meal-card"
    :class="{
      'meal-card--regenerating': isRegenerating,
      'meal-card--error': regenerationError,
    }"
  >
    <!-- Meal Type Badge -->
    <div class="meal-type-badge" :class="`meal-type-badge--${meal.meal_type}`">
      {{ meal.meal_type }}
    </div>

    <!-- Recipe Name -->
    <h3 class="recipe-name">{{ meal.recipe.name }}</h3>

    <!-- Nutrition Summary -->
    <div class="nutrition-summary">
      <div class="nutrition-item">
        <span class="label">칼로리</span>
        <span class="value">{{ meal.recipe.nutrition.calories_kcal }}kcal</span>
      </div>
      <div class="nutrition-item">
        <span class="label">단백질</span>
        <span class="value">{{ meal.recipe.nutrition.protein_g }}g</span>
      </div>
      <div class="nutrition-item">
        <span class="label">비용</span>
        <span class="value">{{ meal.recipe.estimated_cost.toLocaleString() }}원</span>
      </div>
      <div class="nutrition-item">
        <span class="label">조리시간</span>
        <span class="value">{{ meal.recipe.cooking_time_min }}분</span>
      </div>
    </div>

    <!-- Ingredients Preview (first 3) -->
    <div class="ingredients-preview">
      <span class="label">주재료:</span>
      <span class="ingredients-list">
        {{ meal.recipe.ingredients.map(ing => typeof ing === 'string' ? ing : (ing as any).name).join(', ') }}
<!--         <span v-if="meal.recipe.ingredients.length > 3" class="more-indicator"> -->
<!--           외 {{ meal.recipe.ingredients.length - 3 }}개 -->
<!--         </span> -->
      </span>
    </div>

    <!-- Validation Status -->
<!--     <div class="validation-status"> -->
<!--       <span -->
<!--         v-for="(status, validator) in meal.validation_status" -->
<!--         :key="validator" -->
<!--         class="validation-badge" -->
<!--         :class="`validation-badge&#45;&#45;${status}`" -->
<!--       > -->
<!--         {{ validator }} -->
<!--       </span> -->
<!--     </div> -->

    <!-- Action Buttons -->
    <div v-if="isComplete" class="action-buttons">
      <!-- Regenerate Button -->
      <button
        class="btn btn-regenerate"
        :class="{ 'btn-confirm': confirmRegenerate }"
        :disabled="isRegenerating"
        @click="handleRegenerate"
      >
        <span v-if="isRegenerating">🔄 재생성 중...</span>
        <span v-else-if="confirmRegenerate">✅ 확인: 다시 생성</span>
        <span v-else>🔄 다시 생성</span>
      </button>

      <!-- Alternative Recipes Button -->
      <button
        class="btn btn-alternatives"
        :disabled="isRegenerating"
        @click="handleShowAlternatives"
      >
        🔀 비슷한 레시피
      </button>
    </div>

    <!-- Regeneration Error -->
    <div v-if="regenerationError" class="error-message">
      ⚠️ {{ regenerationError }}
    </div>

    <!-- Alternatives Modal -->
    <AlternativesModal
      v-if="showAlternativesModal"
      :meal="meal"
      :day="day"
      :meal-plan="mealPlan"
      :alternatives="alternatives"
      :is-loading="isLoading"
      :error="error"
      @close="showAlternativesModal = false"
    />
  </div>
</template>

<style scoped>
.meal-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  position: relative;
	display: flex;
	flex-direction: column;
}

.meal-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.meal-card--regenerating {
  opacity: 0.6;
  pointer-events: none;
}

.meal-card--error {
  border: 2px solid #ef4444;
}

.meal-type-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
	width: fit-content;
}

.meal-type-badge--아침 {
  background: #fef3c7;
  color: #92400e;
}

.meal-type-badge--점심 {
  background: #dbeafe;
  color: #1e40af;
}

.meal-type-badge--저녁 {
  background: #e0e7ff;
  color: #4338ca;
}

.meal-type-badge--간식 {
  background: #fce7f3;
  color: #9f1239;
}

.recipe-name {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: auto;
	padding-bottom: 16px;
}

.nutrition-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.nutrition-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nutrition-item .label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.nutrition-item .value {
  font-size: 16px;
  color: #1f2937;
  font-weight: 600;
}

.ingredients-preview {
  margin-bottom: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.ingredients-preview .label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
  margin-right: 8px;
}

.ingredients-list {
  font-size: 14px;
  color: #374151;
}

.more-indicator {
  color: #6b7280;
  font-style: italic;
}

.validation-status {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.validation-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.validation-badge--passed {
  background: #d1fae5;
  color: #065f46;
}

.validation-badge--failed {
  background: #fee2e2;
  color: #991b1b;
}

.validation-badge--pending {
  background: #e5e7eb;
  color: #4b5563;
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

.btn-regenerate {
  background: #3b82f6;
  color: white;
}

.btn-regenerate:hover:not(:disabled) {
  background: #2563eb;
}

.btn-regenerate.btn-confirm {
  background: #10b981;
  animation: pulse 0.5s ease-in-out;
}

.btn-alternatives {
  background: #8b5cf6;
  color: white;
}

.btn-alternatives:hover:not(:disabled) {
  background: #7c3aed;
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background: #fee2e2;
  border-radius: 8px;
  color: #991b1b;
  font-size: 14px;
  font-weight: 500;
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
  .nutrition-summary {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
