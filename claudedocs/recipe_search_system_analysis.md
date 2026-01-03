# 레시피 검색 시스템 상세 분석

**작성일**: 2026-01-02  
**목적**: 현재 레시피 검색 구현 방식 및 데이터 소스 파악  
**범위**: RecipeSearchService, CSV 데이터베이스, Tavily 웹 검색 통합

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [검색 전략 (Fallback Chain)](#2-검색-전략-fallback-chain)
3. [데이터 소스](#3-데이터-소스)
4. [검색 필터링](#4-검색-필터링)
5. [캐싱 전략](#5-캐싱-전략)
6. [문제점 및 개선 방안](#6-문제점-및-개선-방안)

---

## 1. 시스템 개요

### 핵심 파일

| 파일                                | 역할         | 라인 수         |
| --------------------------------- | ---------- | ------------ |
| `app/services/recipe_search.py`   | 레시피 검색 서비스 | 361          |
| `data/recipes_with_nutrition.csv` | 로컬 레시피 DB  | 336,587개 레시피 |
| `app/utils/constants.py`          | 검색 설정 상수   | 86           |

### 주요 기능

```python
class RecipeSearchService:
    """레시피 검색 서비스 (Tavily API + 로컬 CSV Fallback)"""

    async def search_recipes(
        query: str,           # "아침 초급 30분"
        filters: dict,        # 필터 조건
        limit: int = 5        # 최대 결과 수
    ) -> list[dict]:
        """
        Fallback Chain:
        1. Cache (메모리)
        2. Mock (개발/테스트)
        3. Tavily (웹 검색)
        4. CSV (로컬 DB)
        """
```

### 환경 변수 설정

```bash
# .env
MOCK_MODE=false                          # Mock 데이터 사용 여부
TAVILY_API_KEY=tvly-xxx                  # Tavily API 키 (웹 검색)
RECIPES_CSV_PATH=data/recipes_with_nutrition.csv
ENABLE_WEB_SEARCH=true                   # 웹 검색 활성화 여부
ENABLE_RECIPE_SEARCH=true                # 레시피 검색 기능 전체 활성화
RECIPE_SEARCH_LIMIT=5                    # 검색 결과 최대 수
RECIPE_CACHE_TTL_SECONDS=300             # 캐시 유효 시간 (5분)
```

---

## 2. 검색 전략 (Fallback Chain)

### 2.1 우선순위별 검색 흐름

```
User Query: "아침 초급 30분"
    ↓
┌─────────────────────────────────────┐
│ Step 1: Cache Check                 │
│ - MD5 hash 키 생성                  │
│ - 만료 시간 확인 (5분)             │
│ - Hit → 즉시 반환                  │
└─────────────────────────────────────┘
    ↓ Cache Miss
┌─────────────────────────────────────┐
│ Step 2: Mock Mode Check             │
│ - MOCK_MODE=true?                   │
│ - Yes → 3개 하드코딩 레시피 반환   │
└─────────────────────────────────────┘
    ↓ Not Mock
┌─────────────────────────────────────┐
│ Step 3: Tavily Web Search           │
│ - ENABLE_WEB_SEARCH=true?           │
│ - TAVILY_API_KEY 존재?              │
│ - 검색 쿼리: "한국 레시피 {query}"  │
│ - 도메인 필터링:                    │
│   * 10000recipe.com                 │
│   * wtable.co.kr                    │
│   * haemukja.com                    │
│ - 결과 정규화 (제한적)              │
└─────────────────────────────────────┘
    ↓ Tavily Fail or Disabled
┌─────────────────────────────────────┐
│ Step 4: Local CSV Search            │
│ - pandas DataFrame 로드 (lazy)      │
│ - 필터 적용 (시간, 난이도, 칼로리)  │
│ - 키워드 검색 (name, category)      │
│ - 상위 N개 반환                     │
└─────────────────────────────────────┘
    ↓
Result: list[dict] (레시피 정보)
```

### 2.2 각 단계 상세

#### Step 1: Cache (메모리)

**파일**: `recipe_search.py:324-338`

```python
def _get_from_cache(self, cache_key: str) -> Optional[list[dict]]:
    """캐시에서 결과 가져오기"""
    if cache_key in self._cache:
        results, expiry = self._cache[cache_key]
        if datetime.now() < expiry:
            return results
        else:
            # 만료된 캐시 삭제
            del self._cache[cache_key]
    return None
```

**캐시 키 생성**:

```python
cache_key = md5({
    "query": "아침 초급 30분",
    "filters": {"max_cooking_time": 30, ...},
    "limit": 5
}).hexdigest()
# → "a3f8b2c1..."
```

**특징**:

- ✅ 인메모리 캐시 (서버 재시작 시 초기화)
- ✅ TTL: 5분 (RECIPE_CACHE_TTL_SECONDS)
- ✅ 동일 쿼리 반복 시 즉시 응답
- ⚠️ 서버 재시작 시 캐시 손실

#### Step 2: Mock Mode

**파일**: `recipe_search.py:264-316`

```python
def _get_mock_results(self, query: str, filters: dict, limit: int) -> list[dict]:
    """Mock 모드 레시피 데이터"""
    mock_recipes = [
        {
            "name": "닭가슴살 샐러드",
            "cooking_time": 15,
            "calories": 350,
            "difficulty": "초급",
            "ingredients": ["닭가슴살", "양상추", "방울토마토", "올리브유"],
            "category": "샐러드",
            "carb_g": 15, "protein_g": 40, "fat_g": 12,
            "source": "mock",
        },
        # ... 3개 총
    ]
```

**용도**:

- 개발/테스트 환경에서 외부 API 호출 없이 작동
- 필터 적용 로직 검증
- 빠른 프로토타이핑

#### Step 3: Tavily Web Search

**파일**: `recipe_search.py:128-167`

```python
async def _search_tavily(self, query: str, filters: dict, limit: int) -> list[dict]:
    """Tavily API로 웹 검색"""
    # 검색 쿼리 강화
    enhanced_query = f"한국 레시피 {query}"

    # Tavily 검색 (비동기)
    response = await loop.run_in_executor(
        None,
        lambda: self.tavily_client.search(
            query=enhanced_query,
            max_results=limit * 2,  # 필터링 후 부족 대비
            search_depth="basic",
            include_domains=[
                "10000recipe.com",   # 만개의 레시피
                "wtable.co.kr",       # 우리의 식탁
                "haemukja.com",       # 해먹남녀
            ],
        ),
    )
```

**특징**:

- ✅ 실시간 웹 검색 (최신 트렌드 레시피)
- ✅ 신뢰할 수 있는 한국 레시피 사이트만
- ⚠️ 제한적 정보: title, url만 (영양 정보 없음)
- ⚠️ API 비용 발생
- ⚠️ 네트워크 지연 가능

**반환 형식**:

```python
{
    "name": "제목",           # 웹 페이지 제목
    "cooking_time": None,     # ❌ 추출 불가
    "calories": None,         # ❌ 추출 불가
    "difficulty": None,       # ❌ 추출 불가
    "ingredients": [],        # ❌ 추출 불가
    "category": "기타",
    "source": "web",
    "url": "https://...",
}
```

#### Step 4: Local CSV Search

**파일**: `recipe_search.py:169-262`

**CSV 스키마** (336,587개 레시피):

```python
Columns:
- rcp_id: 레시피 ID
- name: 메뉴명
- category: 카테고리 (밥, 국/찌개, 반찬, 등)
- main_ingredient: 주재료
- servings: 인분
- difficulty: 난이도 (아무나, 초급, 중급, 고급)
- cooking_time: 조리 시간 (분)
- ingredients_raw: 재료 원문 ("|"로 구분)
- ingredients_parsed: 재료 JSON 파싱
- calories: 칼로리 (kcal)
- carb_g: 탄수화물 (g)
- protein_g: 단백질 (g)
- fat_g: 지방 (g)
- sugar_g: 당류 (g)
- sodium_mg: 나트륨 (mg)
- cholesterol_mg: 콜레스테롤 (mg)
- saturated_fat_g: 포화지방 (g)
- nutrition_match_rate: 영양 정보 매칭률 (0.0-1.0)
- year: 수집 연도 (2022, 2023, 2024)
```

**검색 로직**:

```python
# 1. DataFrame 로드 (lazy loading)
df = pd.read_csv("data/recipes_with_nutrition.csv")

# 2. 필터 적용
if max_cooking_time:
    df = df[df["cooking_time"] <= max_cooking_time]

if difficulty:
    # 난이도 매핑: 초급 → "아무나"만, 중급 → "아무나"+"초급", 고급 → 모두
    difficulty_map = {
        "초급": ["아무나"],
        "중급": ["아무나", "초급"],
        "고급": ["아무나", "초급", "중급"]
    }
    allowed = difficulty_map[difficulty]
    df = df[df["difficulty"].isin(allowed)]

if target_calories:
    min_cal = target_calories * (1 - calorie_tolerance)  # 0.7 × 575 = 402.5
    max_cal = target_calories * (1 + calorie_tolerance)  # 1.3 × 575 = 747.5
    df = df[(df["calories"] >= min_cal) & (df["calories"] <= max_cal)]

# 3. 제외 재료 필터링
for ingredient in exclude_ingredients:
    df = df[~df["ingredients_raw"].str.contains(ingredient, case=False, na=False)]

# 4. 키워드 검색 (OR 조건)
keywords = query.split()  # ["아침", "초급", "30분"]
mask = False
for keyword in keywords:
    mask |= (
        df["name"].str.contains(keyword, case=False)
        | df["category"].str.contains(keyword, case=False)
        | df["main_ingredient"].str.contains(keyword, case=False)
    )
df = df[mask]

# 5. 상위 N개
results = df.head(limit)
```

**반환 형식**:

```python
{
    "name": "닭가슴살 샐러드",
    "cooking_time": 15,
    "calories": 350.0,
    "difficulty": "초급",
    "ingredients": ["닭가슴살", "양상추", "방울토마토", ...],
    "category": "샐러드",
    "carb_g": 15.0,
    "protein_g": 40.0,
    "fat_g": 12.0,
    "source": "csv",
}
```

---

## 3. 데이터 소스

### 3.1 CSV 데이터베이스

**위치**: `meal-planner-back/data/recipes_with_nutrition.csv`

**통계**:

- **총 레시피**: 336,587개
- **수집 연도**: 2022, 2023, 2024
- **평균 영양 매칭률**: 약 60% (nutrition_match_rate)

**데이터 출처**:

- `meal-planner-data/data/raw/recipes_2022.csv`
- `meal-planner-data/data/raw/recipes_2023.csv`
- `meal-planner-data/data/raw/recipes_2024.csv`

**처리 파이프라인**:

```
Raw Recipes
    ↓
Nutrition Matching (식품의약품안전처 DB)
    ↓
recipes_with_nutrition.csv (통합)
```

**한계**:

- ⚠️ 일부 레시피는 영양 정보 부정확 (매칭률 < 60%)
- ⚠️ 인코딩 문제 (일부 한글 깨짐)
- ⚠️ 중복 레시피 가능성

### 3.2 Tavily Web Search

**API**: Tavily API (https://tavily.com)

**타겟 사이트**:

1. **10000recipe.com** (만개의 레시피)
   
   - 한국 최대 레시피 커뮤니티
   - 사용자 제작 레시피 중심

2. **wtable.co.kr** (우리의 식탁)
   
   - 전문가 검증 레시피
   - 밀키트 사업 연계

3. **haemukja.com** (해먹남녀)
   
   - 1인 가구 레시피 특화
   - 간단한 요리 중심

**한계**:

- ❌ 영양 정보 추출 불가
- ❌ 재료 정보 추출 불가
- ❌ 조리 시간 추출 불가
- ✅ 최신 트렌드 레시피만 제공

**현재 활용도**:

- Chef agent에서 **참고 자료**로만 사용
- 실제 메뉴 추천에는 LLM 생성 사용
- 레시피 URL만 제공

---

## 4. 검색 필터링

### 4.1 지원 필터

| 필터                    | 타입        | 설명           | 예시               |
| --------------------- | --------- | ------------ | ---------------- |
| `max_cooking_time`    | int       | 조리 시간 제한 (분) | 30               |
| `difficulty`          | str       | 난이도          | "초급", "중급", "고급" |
| `exclude_ingredients` | list[str] | 제외 재료        | ["돼지고기", "갑각류"]  |
| `target_calories`     | float     | 목표 칼로리       | 575.0            |
| `calorie_tolerance`   | float     | 칼로리 허용 범위    | 0.3 (±30%)       |

### 4.2 Chef Agent 통합

**파일**: `app/agents/nodes/meal_planning/chef.py:36-67`

```python
if ENABLE_RECIPE_SEARCH:
    search_service = get_recipe_search_service()

    # 검색 쿼리 구성
    search_query = f"{state['current_meal_type']} {profile.skill_level} {time_limit}분"
    if profile.restrictions:
        search_query += f" exclude:{','.join(profile.restrictions[:2])}"

    # 레시피 검색
    recipes = await search_service.search_recipes(
        query=search_query,
        filters={
            "max_cooking_time": time_limit,
            "difficulty": profile.skill_level,
            "exclude_ingredients": profile.restrictions,
            "target_calories": targets.calories,
            "calorie_tolerance": 0.3,
        },
    )

    # 프롬프트에 참고 레시피 추가
    if recipes:
        recipe_context = "\n## 참고 레시피 (실제 데이터)\n"
        for i, recipe in enumerate(recipes[:3], 1):
            recipe_context += f"\n### 레시피 {i}: {recipe['name']}\n"
            recipe_context += f"- 조리시간: {recipe.get('cooking_time', 'N/A')}분\n"
            recipe_context += f"- 칼로리: {recipe.get('calories', 'N/A')}kcal\n"
            recipe_context += f"- 난이도: {recipe.get('difficulty', 'N/A')}\n"
            recipe_context += f"- 재료: {', '.join(recipe.get('ingredients', [])[:5])}\n"
```

**LLM 프롬프트 예시**:

```
당신은 전문 셰프입니다.

다음 조건에 맞는 아침 메뉴 1개를 추천해주세요.

## 조리 조건
- 조리 시간: 30분 이내
- 요리 실력: 중급
- 제외 재료: 돼지고기, 갑각류

## 영양 목표 (참고)
- 칼로리: 575kcal
- 단백질: 36g

## 참고 레시피 (실제 데이터)

### 레시피 1: 닭가슴살 샐러드
- 조리시간: 15분
- 칼로리: 350kcal
- 난이도: 초급
- 재료: 닭가슴살, 양상추, 방울토마토, 올리브유, 레몬

### 레시피 2: 두부 스테이크
- 조리시간: 20분
- 칼로리: 400kcal
- 난이도: 중급
- 재료: 두부, 버섯, 마늘, 간장, 참기름

위 참고 레시피를 활용하거나 변형할 수 있습니다.
맛있고 조리하기 쉬운 메뉴를 추천해주세요.
```

---

## 5. 캐싱 전략

### 5.1 인메모리 캐시

**구현**: `recipe_search.py:54-55`

```python
# 검색 결과 캐시 {cache_key: (results, expiry_time)}
self._cache: dict[str, tuple[list[dict], datetime]] = {}
```

**캐시 키 생성**:

```python
def _generate_cache_key(self, query: str, filters: dict, limit: int) -> str:
    """캐시 키 생성 (MD5 hash)"""
    cache_data = {"query": query, "filters": filters, "limit": limit}
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()
```

**예시**:

```python
Query: "아침 초급 30분"
Filters: {"max_cooking_time": 30, "difficulty": "초급"}
Limit: 5

Cache Key: "f3a8b2c1d4e5..." (MD5)

Cached Value: (
    [
        {"name": "닭가슴살 샐러드", ...},
        {"name": "계란 볶음밥", ...},
    ],
    expiry=datetime(2026, 1, 2, 15, 10, 0)  # 5분 후
)
```

### 5.2 캐시 동작

**저장**:

```python
def _save_to_cache(self, cache_key: str, results: list[dict]) -> None:
    """캐시에 결과 저장"""
    expiry = datetime.now() + timedelta(seconds=300)  # 5분
    self._cache[cache_key] = (results, expiry)
```

**조회**:

```python
def _get_from_cache(self, cache_key: str) -> Optional[list[dict]]:
    """캐시에서 결과 가져오기"""
    if cache_key in self._cache:
        results, expiry = self._cache[cache_key]
        if datetime.now() < expiry:
            return results  # ✅ 유효한 캐시
        else:
            del self._cache[cache_key]  # ❌ 만료된 캐시 삭제
    return None
```

### 5.3 캐시 효율성

**장점**:

- ✅ 동일 검색 반복 시 즉시 응답 (0ms)
- ✅ CSV 파일 재로드 방지
- ✅ Tavily API 호출 절약

**한계**:

- ⚠️ 서버 재시작 시 모든 캐시 손실
- ⚠️ 메모리 제한 (무한 증가 가능)
- ⚠️ 5분 후 재검색 필요

---

## 6. 문제점 및 개선 방안

### 6.1 현재 문제점

#### 문제 1: Tavily 검색 결과 활용도 낮음

**현상**:

```python
# Tavily 결과
{
    "name": "초간단 닭가슴살 요리",
    "cooking_time": None,     # ❌
    "calories": None,         # ❌
    "ingredients": [],        # ❌
    "source": "web",
    "url": "https://..."
}
```

**원인**:

- 웹 페이지에서 구조화된 데이터 추출 어려움
- Tavily API는 title, url, snippet만 제공
- 영양 정보는 웹 페이지 내부에 비정형 데이터로 존재

**영향**:

- LLM은 레시피 이름만 참고 가능
- 실제 영양 정보/재료는 LLM이 추측해야 함
- 검색 비용 대비 효과 낮음

#### 문제 2: CSV 데이터 품질 이슈

**인코딩 문제**:

```python
name: "��踻��"  # 깨진 한글
ingredients: "�κ�", "���", "����"  # 읽을 수 없음
```

**영양 정보 부정확**:

```python
nutrition_match_rate: 0.200  # 20% 매칭률 → 신뢰도 낮음
calories: 6.4                # 비현실적 값
```

**영향**:

- 검색 결과 품질 저하
- LLM에게 잘못된 정보 제공
- 사용자 만족도 감소

#### 문제 3: 캐시 전략 제한적

**문제**:

```python
self._cache: dict[str, tuple[list[dict], datetime]] = {}
# → 서버 재시작 시 모든 캐시 손실
# → 메모리 무한 증가 가능
# → 동시성 이슈 (멀티 프로세스 시)```

**영향**:
- 서버 재배포마다 cold start
- 메모리 누수 위험
- 로드 밸런싱 환경에서 캐시 비효율

#### 문제 4: CSV Lazy Loading 비효율

**현재 구현**:
```python
# 첫 검색 시에만 로드
if self._csv_df is None:
    self._csv_df = pd.read_csv("data/recipes_with_nutrition.csv")
    # 336,587 rows → 수백 MB 메모리
```

**문제**:

- 첫 검색 시 수 초 지연 (cold start)
- 전체 DataFrame을 메모리에 상주
- 실제 사용 레시피는 극소수인데도 전체 로드

#### 문제 5: 난이도 매핑 로직 혼란

**현재 로직**:

```python
difficulty_map = {
    "초급": ["아무나"],           # 초급은 "아무나"만 허용
    "중급": ["아무나", "초급"],    # 중급은 "아무나" + "초급" 허용
    "고급": ["아무나", "초급", "중급"]  # 고급은 모두 허용
}
```

**의문점**:

- "초급" 사용자는 왜 "초급" 레시피를 못 보는가?
- "아무나" = 가장 쉬운 레시피인데, 왜 초급만 검색?
- 직관적이지 않은 매핑

### 6.2 개선 방안

#### 개선 A: Tavily 결과 파싱 강화

**Option 1: 웹 스크래핑 추가**

```python
async def _scrape_recipe_details(self, url: str) -> dict:
    """웹 페이지에서 레시피 상세 정보 추출"""
    # BeautifulSoup 또는 Playwright 사용
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    # 사이트별 선택자 (예: 만개의 레시피)
    if "10000recipe.com" in url:
        ingredients = soup.select(".ingredient-list li")
        cooking_time = soup.select_one(".cooking-time").text
        calories = soup.select_one(".nutrition-calories").text

    return {
        "ingredients": [i.text for i in ingredients],
        "cooking_time": parse_time(cooking_time),
        "calories": parse_calories(calories),
    }
```

**장점**: ✅ 완전한 레시피 정보 획득  
**단점**: ⚠️ 사이트 구조 변경에 취약, 스크래핑 부하

**Option 2: Tavily 비활성화, CSV만 사용**

```python
# constants.py
ENABLE_WEB_SEARCH = False  # Tavily 완전 비활성화
```

**장점**: ✅ 안정적, 비용 절감, 빠른 응답  
**단점**: ❌ 최신 트렌드 레시피 부재

**권장**: Option 2 (CSV만 사용) + 주기적 CSV 업데이트

#### 개선 B: CSV 데이터 정제

**Step 1: 인코딩 수정**

```bash
# CSV 재인코딩
cd meal-planner-data
python scripts/fix_encoding.py \
    --input data/processed/recipes_with_nutrition.csv \
    --output data/processed/recipes_with_nutrition_fixed.csv \
    --encoding utf-8-sig
```

**Step 2: 품질 필터링**

```python
# 신뢰도 낮은 레시피 제거
df = df[df["nutrition_match_rate"] >= 0.6]  # 60% 이상만

# 비현실적 값 제거
df = df[
    (df["calories"] >= 100) & (df["calories"] <= 2000) &
    (df["cooking_time"] >= 5) & (df["cooking_time"] <= 180)
]

# 중복 제거
df = df.drop_duplicates(subset=["name", "main_ingredient"])
```

**Step 3: 인덱싱 최적화**

```python
# 자주 필터링하는 컬럼에 인덱스 생성
df = df.set_index(["difficulty", "cooking_time", "calories"])
```

**기대 효과**:

- ✅ 검색 품질 향상 (신뢰도 60% 이상만)
- ✅ 메모리 사용량 감소 (중복 제거)
- ✅ 검색 속도 향상 (인덱싱)

#### 개선 C: 캐시 전략 고도화

**Option 1: Redis 캐시**

```python
import redis
from redis import asyncio as aioredis

class RecipeSearchService:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(redis_url)

    async def _get_from_cache(self, cache_key: str) -> Optional[list[dict]]:
        """Redis에서 캐시 조회"""
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    async def _save_to_cache(self, cache_key: str, results: list[dict]) -> None:
        """Redis에 캐시 저장 (TTL 5분)"""
        await self.redis.setex(
            cache_key,
            300,  # 5분
            json.dumps(results, ensure_ascii=False)
        )
```

**장점**:

- ✅ 서버 재시작 후에도 캐시 유지
- ✅ 멀티 프로세스 환경에서 공유 캐시
- ✅ TTL 자동 관리

**단점**:

- ⚠️ Redis 서버 필요 (인프라 복잡도 증가)
- ⚠️ 네트워크 지연 (인메모리보다 느림)

**Option 2: LRU 캐시 (메모리 제한)**

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # 최근 사용으로 이동
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        # 최대 크기 초과 시 오래된 항목 제거
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
```

**장점**:

- ✅ 메모리 사용량 제한
- ✅ 인프라 변경 없음
- ✅ 빠른 응답

**권장**: Development → 인메모리, Production → Redis

#### 개선 D: CSV 로딩 최적화

**Option 1: 사전 필터링 + 샤딩**

```python
# 난이도별로 CSV 분리
recipes_easy = df[df["difficulty"].isin(["아무나", "초급"])]
recipes_medium = df[df["difficulty"].isin(["아무나", "초급", "중급"])]
recipes_hard = df  # 전체

# 파일 저장
recipes_easy.to_csv("data/recipes_easy.csv")
recipes_medium.to_csv("data/recipes_medium.csv")
recipes_hard.to_csv("data/recipes_hard.csv")

# 검색 시
def _get_csv_path(difficulty: str) -> str:
    mapping = {
        "초급": "data/recipes_easy.csv",
        "중급": "data/recipes_medium.csv",
        "고급": "data/recipes_hard.csv",
    }
    return mapping.get(difficulty, "data/recipes_hard.csv")
```

**효과**:

- ✅ 초급 검색 시 1/3 메모리만 사용
- ✅ 로딩 시간 단축
- ❌ 파일 관리 복잡도 증가

**Option 2: Parquet 형식 전환**

```python
# CSV → Parquet 변환 (1회)
df.to_parquet("data/recipes_with_nutrition.parquet", compression="snappy")

# 검색 시 로드 (더 빠름)
df = pd.read_parquet("data/recipes_with_nutrition.parquet")
```

**효과**:

- ✅ 로딩 속도 3-5배 향상
- ✅ 파일 크기 50-70% 감소
- ✅ 컬럼별 선택적 로드 가능

**권장**: Parquet + Redis 캐시 조합

#### 개선 E: 난이도 매핑 수정

**현재 (혼란스러움)**:

```python
"초급": ["아무나"]  # 초급 레시피는 못 봄??
```

**수정안**:

```python
difficulty_map = {
    "초급": ["아무나", "초급"],           # 쉬운 것만
    "중급": ["아무나", "초급", "중급"],    # 중간까지
    "고급": ["아무나", "초급", "중급", "고급"]  # 모두
}
```

**직관적 해석**:

- 초급 사용자 → 아무나 + 초급 레시피 선택
- 중급 사용자 → 중급까지 도전 가능
- 고급 사용자 → 모든 레시피 가능

---

## 7. 우선순위별 개선 로드맵

### Phase 1: 품질 개선 (1-2일)

#### Day 1 오전 (2시간)

✅ **개선 B: CSV 데이터 정제**

- [ ] 인코딩 문제 수정 (UTF-8 with BOM)
- [ ] 품질 필터링 (nutrition_match_rate >= 0.6)
- [ ] 비현실적 값 제거

**검증**:

```python
# 정제 전
total: 336,587
readable: ??%

# 정제 후
total: ~200,000 (예상)
readable: 100%
nutrition_match_rate avg: 0.75+
```

#### Day 1 오후 (1시간)

✅ **개선 E: 난이도 매핑 수정**

- [ ] `recipe_search.py:193` 수정
- [ ] 테스트 케이스 검증

#### Day 2 오전 (2시간)

✅ **개선 D-2: Parquet 전환**

- [ ] CSV → Parquet 변환 스크립트
- [ ] `recipe_search.py` 로딩 로직 수정
- [ ] 성능 벤치마크

**기대 효과**:

- 로딩 속도: 5초 → 1초
- 파일 크기: 100MB → 30MB

### Phase 2: 성능 최적화 (3일차, 선택적)

#### Day 3 (3시간)

✅ **개선 C-2: LRU 캐시 구현**

- [ ] `LRUCache` 클래스 구현
- [ ] `RecipeSearchService` 적용
- [ ] 메모리 사용량 모니터링

**검증**:

- 캐시 크기: 100개 제한
- 히트율: >80% (반복 검색 시)

### Phase 3: 인프라 강화 (4-5일차, 선택적)

#### Day 4-5

✅ **개선 C-1: Redis 캐시 (Production)**

- [ ] Redis 서버 설정
- [ ] Redis 통합
- [ ] 멀티 프로세스 테스트

✅ **개선 A-2: Tavily 비활성화**

- [ ] `ENABLE_WEB_SEARCH=false` 설정
- [ ] Tavily 관련 코드 제거 (선택적)

---

## 8. 최종 권장 아키텍처

```
┌──────────────────────────────────────────┐
│ Chef Agent                               │
│ - 레시피 검색 요청                        │
│ - LLM 프롬프트 강화                       │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ RecipeSearchService                      │
│ ┌────────────────────────────────────┐  │
│ │ 1. Redis Cache Check (5분 TTL)     │  │
│ │    ↓ Miss                           │  │
│ │ 2. Parquet DB Search                │  │
│ │    - 품질 필터링 (match_rate >= 0.6)│  │
│ │    - 난이도/시간/칼로리 필터         │  │
│ │    - 키워드 검색                    │  │
│ │    ↓                                │  │
│ │ 3. Save to Redis                    │  │
│ └────────────────────────────────────┘  │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ Results: list[dict]                      │
│ - name, cooking_time, calories           │
│ - ingredients, difficulty                │
│ - 완전한 영양 정보                        │
└──────────────────────────────────────────┘
```

### 핵심 변경 사항

1. **Tavily 제거**: 비용 대비 효과 낮음, CSV만 사용
2. **Parquet 사용**: 3-5배 빠른 로딩
3. **Redis 캐시**: 영구 캐시, 멀티 프로세스 지원
4. **품질 필터링**: nutrition_match_rate >= 0.6
5. **난이도 매핑 수정**: 직관적 로직

### 기대 효과

| 지표       | 현재          | 개선 후    | 변화     |
| -------- | ----------- | ------- | ------ |
| 첫 검색 지연  | 5초          | 1초      | -80%   |
| 반복 검색 지연 | 5초          | 10ms    | -99.8% |
| 캐시 지속성   | 서버 재시작 시 손실 | 영구      | ✅      |
| 레시피 품질   | 60% 평균      | 75%+ 평균 | +25%   |
| 인코딩 오류   | ~10%        | 0%      | ✅      |
| 메모리 사용량  | 전체 DB       | LRU 제한  | -70%   |

---

## 9. 참고 자료

### 관련 파일

- **서비스**: `app/services/recipe_search.py` (361 lines)
- **상수**: `app/utils/constants.py` (86 lines)
- **Chef 통합**: `app/agents/nodes/meal_planning/chef.py:36-67`
- **데이터**: `data/recipes_with_nutrition.csv` (336,587 rows)

### 환경 변수

```bash
MOCK_MODE=false
TAVILY_API_KEY=tvly-xxx
RECIPES_CSV_PATH=data/recipes_with_nutrition.csv
ENABLE_WEB_SEARCH=false  # 권장: false
ENABLE_RECIPE_SEARCH=true
RECIPE_SEARCH_LIMIT=5
RECIPE_CACHE_TTL_SECONDS=300
```

### 다음 단계

1. **즉시**: 개선 E (난이도 매핑) 수정 - 10분
2. **Phase 1**: 데이터 정제 + Parquet 전환 - 1-2일
3. **Phase 2**: LRU 캐시 구현 - 3시간
4. **Phase 3**: Redis 도입 (선택적) - 1-2일

---

**작성일**: 2026-01-02  
**다음 리뷰**: 개선 작업 시작 전  
**관련 문서**: `system_improvement_opportunities.md`
