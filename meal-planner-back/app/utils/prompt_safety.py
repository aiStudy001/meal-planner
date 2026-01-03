"""Prompt Injection 방지 유틸리티

EC-028: 사용자 입력 sanitization으로 prompt injection 공격 차단
"""

import re
from typing import List


# 허용된 문자 패턴: 한글, 영문, 숫자, 공백, 하이픈
ALLOWED_PATTERN = re.compile(r'^[가-힣a-zA-Z0-9\s\-]+$')

# Prompt injection 공격 패턴 (금지된 패턴)
INJECTION_PATTERNS = [
    re.compile(r'ignore\s+.*(previous|above|all|prior).*\s+instructions?', re.IGNORECASE),
    re.compile(r'system\s*:', re.IGNORECASE),
    re.compile(r'<\s*system\s*>', re.IGNORECASE),
    re.compile(r'you\s+are\s+(now|a)', re.IGNORECASE),
    re.compile(r'forget\s+(everything|all|previous)', re.IGNORECASE),
    re.compile(r'act\s+as\s+', re.IGNORECASE),
    re.compile(r'pretend\s+(you|to)\s+', re.IGNORECASE),
    re.compile(r'\|\s*sudo\s+', re.IGNORECASE),
    re.compile(r'```', re.IGNORECASE),  # Code blocks
]

# 최대 길이 제한
MAX_STRING_LENGTH = 100


def sanitize_string(value: str, field_name: str = "입력값") -> str:
    """단일 문자열 sanitization

    Args:
        value: 검증할 문자열
        field_name: 필드 이름 (에러 메시지용)

    Returns:
        검증된 문자열

    Raises:
        ValueError: 허용되지 않은 문자 또는 injection 패턴 발견
    """
    if not value:
        return value

    # 길이 제한 검사
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError(
            f"{field_name}이(가) 너무 깁니다. "
            f"최대 {MAX_STRING_LENGTH}자 (현재: {len(value)}자)"
        )

    # 허용된 문자만 포함하는지 검사
    if not ALLOWED_PATTERN.match(value):
        raise ValueError(
            f"{field_name}에 허용되지 않은 문자가 포함되어 있습니다. "
            f"한글, 영문, 숫자, 공백, 하이픈만 사용 가능합니다."
        )

    # Prompt injection 패턴 검사
    for pattern in INJECTION_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"{field_name}에 허용되지 않은 패턴이 발견되었습니다. "
                f"보안상의 이유로 입력이 거부되었습니다."
            )

    return value.strip()


def sanitize_string_list(values: List[str], field_name: str = "목록") -> List[str]:
    """문자열 리스트 sanitization

    Args:
        values: 검증할 문자열 리스트
        field_name: 필드 이름 (에러 메시지용)

    Returns:
        검증된 문자열 리스트

    Raises:
        ValueError: 허용되지 않은 문자 또는 injection 패턴 발견
    """
    if not values:
        return values

    sanitized = []
    for idx, value in enumerate(values):
        try:
            sanitized_value = sanitize_string(value, f"{field_name}[{idx}]")
            sanitized.append(sanitized_value)
        except ValueError as e:
            raise ValueError(f"{field_name} 검증 실패: {str(e)}")

    return sanitized


def escape_for_llm(text: str) -> str:
    """LLM 프롬프트에 안전하게 삽입하기 위한 이스케이프

    사용자 입력을 LLM 프롬프트에 포함할 때 사용

    Args:
        text: 이스케이프할 텍스트

    Returns:
        이스케이프된 텍스트
    """
    if not text:
        return text

    # 백슬래시, 따옴표 이스케이프
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("'", "\\'")

    # 중괄호 이스케이프 (f-string 보호)
    escaped = escaped.replace("{", "{{")
    escaped = escaped.replace("}", "}}")

    return escaped
