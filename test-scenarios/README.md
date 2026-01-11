# Meal Planner Test Scenarios

본 디렉토리는 AI Meal Planner 시스템의 성능 검증 및 데모를 위한 5가지 테스트 시나리오를 포함합니다.

## 시나리오 개요

각 시나리오는 실제 사용자의 다양한 요구사항을 대표하며, 시스템의 적응성과 정확성을 평가하기 위해 설계되었습니다.

### 1. 체중 감량 남성 (`scenario-1-weight-loss-male.json`)
- **대상**: 32세 남성, 체중 85kg, 키 175cm
- **목표**: 다이어트 (체지방 감소, 근육 유지)
- **특징**: 고단백 저칼로리 식단
- **활동량**: 중간 (주 3-4회 운동)
- **예상 칼로리**: 1800-2000 kcal/일
- **단백질**: 120-140g/일 (고단백)

### 2. 체중 증가 여성 (`scenario-2-weight-gain-female.json`)
- **대상**: 25세 여성, 체중 48kg, 키 162cm
- **목표**: 벌크업 (건강한 체중 증가)
- **특징**: 고칼로리 균형 잡힌 영양소
- **활동량**: 높음 (근력 운동 빈번)
- **예상 칼로리**: 2200-2500 kcal/일
- **단백질**: 80-100g/일

### 3. 다중 알레르기 (`scenario-3-multi-allergy.json`)
- **대상**: 28세 남성, 체중 70kg, 키 172cm
- **목표**: 체중 유지
- **특징**: **알레르기 3종** (견과류, 해산물, 우유)
- **제약사항**: 알레르기 식재료 완전 제외
- **대체 단백질**: 닭고기, 돼지고기, 두부
- **예상 칼로리**: 2000-2200 kcal/일

### 4. 건강 제약 (`scenario-4-health-constraints.json`)
- **대상**: 55세 남성, 체중 75kg, 키 168cm
- **목표**: 질병관리 (당뇨병 + 고혈압)
- **특징**: **저염, 저당, 혈당 조절** 식단
- **제약사항**:
  - 나트륨 제한 (하루 2000mg 이하)
  - 저GI 식품 위주
  - 복합 탄수화물 선호
- **예상 칼로리**: 1700-1900 kcal/일

### 5. 저예산 (`scenario-5-low-budget.json`)
- **대상**: 22세 대학생, 체중 68kg, 키 178cm
- **목표**: 체중 유지
- **특징**: **경제적 식단** (일일 1만원)
- **제약사항**: 주간 예산 30,000원
- **전략**: 저가 단백질원, 제철 채소, 간단 조리
- **예상 칼로리**: 2000-2300 kcal/일

## 사용 방법

### 1. 프론트엔드 UI에서 시나리오 선택
홈 화면에서 드롭다운 메뉴를 통해 원하는 시나리오를 선택하면, 자동으로 프로필 데이터가 로드되어 입력 페이지로 이동합니다.

```
홈 화면 → 시나리오 선택 드롭다운 → "불러오기" → 입력 페이지 (자동 완성)
```

### 2. API를 통한 직접 테스트

각 시나리오 JSON 파일을 직접 API에 전송하여 테스트할 수 있습니다.

```bash
# 시나리오 1 테스트
curl -X POST http://localhost:8000/api/generate-plan \
  -H "Content-Type: application/json" \
  -d @test-scenarios/scenario-1-weight-loss-male.json

# 시나리오 3 테스트 (다중 알레르기)
curl -X POST http://localhost:8000/api/generate-plan \
  -H "Content-Type: application/json" \
  -d @test-scenarios/scenario-3-multi-allergy.json
```

### 3. 자동화된 테스트 스크립트

모든 시나리오를 순차적으로 테스트:

```bash
for scenario in test-scenarios/scenario-*.json; do
  echo "Testing: $scenario"
  curl -X POST http://localhost:8000/api/generate-plan \
    -H "Content-Type: application/json" \
    -d @"$scenario" \
    --silent | jq '.success'
  echo "---"
done
```

## 검증 항목

각 시나리오 실행 시 다음 항목을 확인합니다:

### ✅ 기본 검증
- [ ] 3일 식단 정상 생성
- [ ] 일일 3끼 구성 (아침, 점심, 저녁)
- [ ] 영양 정보 정확성 (칼로리, 단백질, 탄수화물, 지방)
- [ ] 예산 범위 준수

### ✅ 시나리오별 특수 검증

**시나리오 1 (체중 감량)**
- [ ] 단백질 비율 25-30%
- [ ] 칼로리 1800-2000 범위
- [ ] 저칼로리 고단백 식재료 사용

**시나리오 2 (체중 증가)**
- [ ] 칼로리 2200-2500 범위
- [ ] 균형 잡힌 영양소 비율
- [ ] 에너지 밀도 높은 식재료

**시나리오 3 (다중 알레르기)**
- [ ] 견과류 완전 제외
- [ ] 해산물 완전 제외
- [ ] 유제품 완전 제외
- [ ] 대체 단백질원 활용 (닭고기, 두부)

**시나리오 4 (건강 제약)**
- [ ] 나트륨 제한 준수
- [ ] 저GI 식품 위주
- [ ] 복합 탄수화물 선호
- [ ] 정제 당류 최소화

**시나리오 5 (저예산)**
- [ ] 일일 예산 10,000원 준수
- [ ] 경제적 식재료 선택
- [ ] 영양 기준 충족 (최소 단백질 70g)

## 예상 결과

### 성공 기준
- **생성 성공률**: 100% (모든 시나리오 완료)
- **검증 통과율**: 100% (영양, 예산, 제약사항)
- **재시도 횟수**: 평균 0-2회
- **생성 시간**: 시나리오당 30-90초

### 실패 시나리오
- 알레르기 식재료 포함 → **Critical 검증 실패**
- 예산 초과 (±10% 이상) → **Budget 검증 실패**
- 칼로리 목표 미달성 (±20% 이상) → **Nutrition 검증 실패**

## 개발자 노트

### 시나리오 추가 방법

새로운 테스트 시나리오를 추가하려면:

1. 기존 시나리오 JSON 파일을 복사하여 템플릿으로 사용
2. `profile` 섹션의 값을 수정
3. `expected` 섹션에 예상 결과 명시
4. 본 README에 시나리오 설명 추가
5. 프론트엔드 `scenarios.ts`에 데이터 추가

### JSON 스키마

```typescript
interface TestScenario {
  name: string              // 시나리오 이름
  description: string       // 간단한 설명
  profile: UserProfile      // 사용자 프로필 (types/index.ts 참조)
  expected: {
    daily_calories: string  // 예상 칼로리 범위
    protein_target?: string // 예상 단백질량
    validation_notes: string // 검증 시 주의사항
  }
}
```

## 문제 해결

### 시나리오가 실패하는 경우

1. **알레르기 검증 실패**
   - 레시피 DB에서 알레르기 필터링 확인
   - `recipe_searcher.py`의 `exclude_allergens` 로직 점검

2. **예산 초과**
   - Progressive relaxation 전략 동작 확인
   - `budget_validator.py`의 tolerance 설정 검토

3. **영양 목표 미달성**
   - 목표 칼로리 계산 로직 확인 (`profile_analyzer.py`)
   - 레시피 영양 정보 정확성 검증

## 참고 자료

- [USAGE.md](../USAGE.md) - 전체 사용 가이드
- [IMPROVEMENT_PLAN.md](../IMPROVEMENT_PLAN.md) - 구현 계획
- [README.md](../README.md) - 프로젝트 개요
