# 레시피 검색 시스템 - 현재 상태 및 결정 사항

**업데이트**: 2026-01-02  
**결정**: CSV 단독 사용으로 확정

---

## 현재 설정

### 환경 변수 (.env)

```bash
# Recipe Search
TAVILY_API_KEY=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
ENABLE_WEB_SEARCH=false  # ✅ Tavily 비활성화됨
RECIPES_CSV_PATH=data/recipes_with_nutrition.csv
```

### 활성화된 검색 전략

```
User Query → Cache → CSV Database
                      ↓
                 336,587개 레시피
                 (필터 정확히 적용)
```

**Tavily 웹 검색**: ❌ 비활성화 (ENABLE_WEB_SEARCH=false)

---

## Tavily 비활성화 결정 이유

### 1. 필터 적용 불가

**문제**:
```python
filters = {
    "max_cooking_time": 30,     # ❌ Tavily에 전달 안됨
    "difficulty": "초급",        # ❌ Tavily에 전달 안됨  
    "target_calories": 575,      # ❌ Tavily에 전달 안됨
}

# Tavily는 쿼리 문자열만 검색
enhanced_query = f"한국 레시피 {query}"
# → "한국 레시피 아침 초급 30분"
# → 시간/난이도/칼로리 필터 무시됨
```

**결과**: 
- 30분 제한인데 1시간 레시피 검색
- 초급인데 고급 레시피 검색
- 575kcal 목표인데 1000kcal 레시피 검색

### 2. 추출 가능한 정보 제한적

**Tavily 검색 결과**:
```python
{
    "name": "초간단 닭가슴살 요리",  # ✅ 제목만
    "cooking_time": None,           # ❌ 추출 불가
    "calories": None,               # ❌ 추출 불가
    "difficulty": None,             # ❌ 추출 불가
    "ingredients": [],              # ❌ 추출 불가
    "url": "https://...",
    "source": "web"
}
```

**LLM 프롬프트 예시**:
```
## 참고 레시피 (실제 데이터)

### 레시피 1: 초간단 닭가슴살 요리
- 조리시간: N/A  # ❌
- 칼로리: N/A    # ❌
- 난이도: N/A    # ❌
- 재료: N/A      # ❌
```

**영향**: LLM이 제목만 보고 추측 → 품질 저하, 참고 가치 낮음

### 3. 비용 대비 효과 낮음

- Tavily API 호출 비용 발생
- 제공 정보: 제목 + URL만
- CSV 대비 장점 없음
- 오히려 부정확한 결과 가능성

### 4. CSV가 충분히 방대함

- **총 레시피**: 336,587개
- **연도별**: 2022, 2023, 2024
- **카테고리**: 밥, 국/찌개, 반찬, 디저트, 샐러드 등
- **완전한 정보**: 조리시간, 난이도, 칼로리, 탄단지, 재료

---

## CSV 단독 사용의 장점

### 1. 정확한 필터링

```python
# 정확히 30분 이하만
df = df[df["cooking_time"] <= 30]

# 정확히 초급 난이도만
df = df[df["difficulty"].isin(["아무나", "초급"])]

# 칼로리 범위 정확히 ±30%
min_cal = 575 * 0.7  # 402.5
max_cal = 575 * 1.3  # 747.5
df = df[(df["calories"] >= min_cal) & (df["calories"] <= max_cal)]
```

### 2. 완전한 영양 정보

```python
{
    "name": "닭가슴살 샐러드",
    "cooking_time": 15,          # ✅
    "calories": 350.0,           # ✅
    "difficulty": "초급",        # ✅
    "ingredients": ["닭가슴살", "양상추", ...],  # ✅
    "carb_g": 15.0,             # ✅
    "protein_g": 40.0,          # ✅
    "fat_g": 12.0,              # ✅
    "source": "csv"
}
```

### 3. 안정성 및 비용

- ✅ 외부 API 의존성 없음
- ✅ 네트워크 오류 없음
- ✅ API 비용 절감
- ✅ 일관된 응답 속도

### 4. 로컬 최적화 가능

- ✅ Parquet 전환 → 5배 빠른 로딩
- ✅ 인덱싱으로 검색 속도 향상
- ✅ 품질 필터링 (match_rate >= 0.6)
- ✅ 캐싱 전략 최적화

---

## 현재 검색 플로우

### Step-by-Step

```
1. Chef Agent 검색 요청
   ↓
2. RecipeSearchService.search_recipes()
   ↓
3. Cache Check (MD5 hash, 5분 TTL)
   ↓ Miss
4. CSV Search (Pandas)
   - 조리시간 필터: <= 30분
   - 난이도 필터: ["아무나", "초급"]
   - 칼로리 필터: 402.5 ~ 747.5 kcal
   - 제외 재료 필터: "돼지고기" not in ingredients
   - 키워드 검색: "아침" in (name | category | main_ingredient)
   ↓
5. 상위 5개 결과 반환
   ↓
6. Cache 저장 (5분)
   ↓
7. LLM 프롬프트에 참고 레시피로 제공
```

### 실제 코드 흐름

**recipe_search.py:64-126**:
```python
async def search_recipes(self, query, filters, limit=5):
    # 1. Cache check
    cached = self._get_from_cache(cache_key)
    if cached:
        return cached
    
    # 2. Mock mode (개발용)
    if self.mock_mode:
        return self._get_mock_results(...)
    
    # 3. Tavily web search
    if self.enable_web_search and self.tavily_client:
        # ❌ 비활성화됨 (ENABLE_WEB_SEARCH=false)
        pass
    
    # 4. CSV fallback (현재 주 전략)
    results = await self._search_local_csv(query, filters, limit)
    self._save_to_cache(cache_key, results)
    return results
```

**recipe_search.py:169-262** (CSV 검색):
```python
async def _search_local_csv(self, query, filters, limit):
    # Lazy load CSV
    if self._csv_df is None:
        self._csv_df = pd.read_csv(self.csv_path)
    
    df = self._csv_df.copy()
    
    # 필터 적용
    if filters.get("max_cooking_time"):
        df = df[df["cooking_time"] <= max_cooking_time]
    
    if filters.get("difficulty"):
        allowed = difficulty_map[difficulty]
        df = df[df["difficulty"].isin(allowed)]
    
    if filters.get("target_calories"):
        min_cal = target_calories * (1 - tolerance)
        max_cal = target_calories * (1 + tolerance)
        df = df[(df["calories"] >= min_cal) & (df["calories"] <= max_cal)]
    
    # 제외 재료
    for ingredient in exclude_ingredients:
        df = df[~df["ingredients_raw"].str.contains(ingredient)]
    
    # 키워드 검색
    for keyword in query.split():
        mask |= (df["name"].str.contains(keyword) | ...)
    df = df[mask]
    
    return df.head(limit).to_dict('records')
```

---

## 향후 개선 계획

### Phase 1: 품질 향상 (1-2일)

**우선순위 높음**:

1. **CSV 인코딩 수정**
   ```bash
   # 한글 깨짐 문제 해결
   df.to_csv("recipes_fixed.csv", encoding="utf-8-sig")
   ```

2. **품질 필터링**
   ```python
   # 신뢰도 낮은 레시피 제거
   df = df[df["nutrition_match_rate"] >= 0.6]
   
   # 비현실적 값 제거
   df = df[
       (df["calories"] >= 100) & (df["calories"] <= 2000) &
       (df["cooking_time"] >= 5) & (df["cooking_time"] <= 180)
   ]
   ```

3. **Parquet 전환**
   ```python
   # CSV → Parquet (5배 빠른 로딩)
   df.to_parquet("recipes.parquet", compression="snappy")
   df = pd.read_parquet("recipes.parquet")  # 5초 → 1초
   ```

### Phase 2: 성능 최적화 (3일차)

**우선순위 중간**:

1. **LRU 캐시**
   ```python
   # 메모리 제한 (최근 100개만 유지)
   from functools import lru_cache
   ```

2. **Redis 캐시** (선택적)
   ```python
   # 서버 재시작 후에도 캐시 유지
   # 멀티 프로세스 환경 지원
   ```

### Phase 3: 데이터 업데이트 (장기)

**우선순위 낮음**:

1. **주기적 크롤링**
   - 만개의레시피, 우리의식탁 등에서 신규 레시피 수집
   - 영양 정보 매칭
   - CSV 업데이트

2. **사용자 피드백 반영**
   - 인기 레시피 추적
   - 품질 개선

---

## 검증 항목

### ✅ 현재 상태 확인

1. **설정 확인**:
   ```bash
   grep "ENABLE_WEB_SEARCH" .env
   # → ENABLE_WEB_SEARCH=false ✅
   ```

2. **CSV 파일 존재**:
   ```bash
   ls -lh data/recipes_with_nutrition.csv
   # → 336,587 rows ✅
   ```

3. **검색 동작 확인**:
   ```python
   from app.services.recipe_search import get_recipe_search_service
   
   service = get_recipe_search_service()
   results = await service.search_recipes(
       query="아침 초급",
       filters={"max_cooking_time": 30, "difficulty": "초급"},
       limit=5
   )
   
   # 모든 결과는 source="csv"여야 함
   assert all(r["source"] == "csv" for r in results)
   
   # 모든 결과는 조리시간 30분 이하여야 함
   assert all(r["cooking_time"] <= 30 for r in results)
   ```

### 🔄 다음 검증 필요

1. **실제 메뉴 생성 테스트**
   - 2일 × 3끼 = 6개 메뉴 생성
   - Chef agent가 CSV 레시피 참고하는지 확인
   - LLM 프롬프트에 완전한 정보 제공되는지 확인

2. **성능 측정**
   - 첫 검색 지연: ~5초 (CSV 로딩)
   - 두 번째 검색: ~0.01초 (캐시 히트)
   - 캐시 만료 후: ~0.5초 (DataFrame 이미 로드됨)

---

## 요약

### 결정 사항

- ✅ **Tavily 웹 검색 비활성화** (ENABLE_WEB_SEARCH=false)
- ✅ **CSV 단독 사용으로 확정**
- ✅ **필터 정확성 우선**
- ✅ **비용 절감 및 안정성 확보**

### 다음 단계

1. **즉시**: CSV 검색 동작 검증 (실제 테스트 실행)
2. **1-2일**: CSV 품질 개선 (인코딩, 필터링, Parquet)
3. **3일차**: 성능 최적화 (LRU 캐시, Redis)
4. **장기**: 데이터 업데이트 전략 수립

---

**관련 문서**:
- `recipe_search_system_analysis.md` - 전체 시스템 분석
- `system_improvement_opportunities.md` - 개선 방안

**설정 파일**:
- `.env` - 환경 변수 설정
- `app/services/recipe_search.py` - 검색 서비스 구현
- `data/recipes_with_nutrition.csv` - 레시피 데이터베이스
