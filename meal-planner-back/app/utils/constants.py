"""상수 정의"""

# 활동 계수
ACTIVITY_MULTIPLIERS = {
    "low": 1.2,
    "moderate": 1.375,
    "high": 1.55,
    "very_high": 1.725,
}

# 목표별 칼로리 조정
CALORIE_ADJUSTMENTS = {
    "다이어트": -500,
    "벌크업": +500,
    "유지": 0,
    "질병관리": 0,  # LLM이 판단
}

# 목표별 매크로 비율 (탄:단:지)
MACRO_RATIOS = {
    "다이어트": {"carb": 50, "protein": 30, "fat": 20},
    "벌크업": {"carb": 40, "protein": 40, "fat": 20},
    "유지": {"carb": 55, "protein": 20, "fat": 25},
    "당뇨": {"carb": 45, "protein": 25, "fat": 30},
    "고혈압": {"carb": 55, "protein": 20, "fat": 25},
    "고지혈증": {"carb": 55, "protein": 25, "fat": 20},
}

# 질병별 제한
HEALTH_CONSTRAINTS = {
    "당뇨": {
        "max_sugar_g": 25,
        "prefer_low_gi": True,
    },
    "고혈압": {
        "max_sodium_mg": 2000,
        "prefer_high_potassium": True,
    },
    "고지혈증": {
        "max_saturated_fat_g": 15,
        "max_cholesterol_mg": 300,
    },
}

# 조리시간 제한 (분)
COOKING_TIME_LIMITS = {
    "15분 이내": 15,
    "30분 이내": 30,
    "제한 없음": 180,
}

# 검증 허용 범위
VALIDATION_TOLERANCE = 0.20  # ±20%

# 재시도 설정
MAX_RETRIES = 5

# 끼니 타입
MEAL_TYPES = ["아침", "점심", "저녁", "간식"]

# 예산 배분 비율 (차등 배분 시)
BUDGET_RATIOS = {
    "아침": 2.0,
    "점심": 3.0,
    "저녁": 3.5,
    "간식": 1.5,
}

# 알레르기 목록 (식약처 22종)
ALLERGENS = [
    "알류(계란)", "우유", "메밀", "땅콩", "대두", "밀",
    "고등어", "게", "새우", "돼지고기", "복숭아", "토마토",
    "아황산류", "호두", "닭고기", "쇠고기", "오징어",
    "조개류", "잣", "오리고기", "토끼고기", "아몬드",
]

# 식이 선호
DIETARY_PREFERENCES = [
    "채식(락토오보)", "비건", "페스코",
    "저염식", "저당식", "저지방", "글루텐프리",
]

# 재시도 매핑: 실패한 검증기 → 재실행할 전문가
RETRY_MAPPING = {
    "nutrition_checker": "nutritionist",
    "allergy_checker": "chef",  # 재료 변경
    "time_checker": "chef",  # 레시피 변경
    "health_checker": "nutritionist",  # 건강 제약 조정
    "budget_checker": "budget",  # 예산 조정
}

# Recipe Search Settings
RECIPE_SEARCH_LIMIT = 5
RECIPE_CACHE_TTL_SECONDS = 300  # 5분
ENABLE_RECIPE_SEARCH = True
