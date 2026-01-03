# Meal Planner

AI 기반 다중 에이전트 식단 계획 시스템

## 프로젝트 구조

```
meal-planner/
├── meal-planner-back/    # Python 백엔드 (LangGraph)
├── meal-planner-front/   # 프론트엔드
├── meal-planner-data/    # 데이터
└── .mise.toml           # 런타임 버전 관리
```

## 개발 환경 설정

> 💡 **Scoop과 mise를 처음 사용하시나요?**
> 자세한 설명은 [MISE_GUIDE.md](MISE_GUIDE.md)를 참고하세요!
> - Scoop: Windows용 패키지 관리자
> - mise: 프로젝트별 런타임 버전 관리 도구

### mise 설치

mise는 프로젝트의 Python, Node.js 버전을 자동으로 관리합니다.

#### Windows (PowerShell)
```powershell
# 1. Scoop 설치 (아직 없다면)
irm get.scoop.sh | iex

# 2. mise 설치
scoop install mise

# 또는 winget으로 설치
winget install jdx.mise
```

#### macOS/Linux
```bash
# 공식 설치 스크립트
curl https://mise.run | sh

# 또는 brew (macOS)
brew install mise
```

### 프로젝트 설정

1. mise 설치 후, 프로젝트 디렉토리로 이동:
```bash
cd meal-planner
```

2. mise가 자동으로 Python 3.13과 Node.js 24.12.0을 설치:
```bash
mise install
```

3. 현재 활성화된 버전 확인:
```bash
mise current
```

출력 예시:
```
python  3.13.x
node    24.12.0
```

### 빠른 시작

#### 백엔드 실행

```bash
# 의존성 설치
mise run install-backend

# 테스트 실행
mise run test-backend

# 예제 실행 (Mock 모드)
mise run run-example

# 개발 서버 실행
mise run dev-backend
```

#### 프론트엔드 실행 (설정 후)

```bash
# 의존성 설치
mise run install-frontend
```

### mise 유용한 명령어

```bash
# 설치된 도구 확인
mise list

# 사용 가능한 태스크 확인
mise tasks

# 특정 버전으로 전환
mise use python@3.12

# 도구 업그레이드
mise upgrade

# mise 설정 확인
mise config
```

## 백엔드 상세 가이드

자세한 내용은 [meal-planner-back/README.md](meal-planner-back/README.md)를 참고하세요.

주요 기능:
- LangGraph 기반 다중 에이전트 시스템
- 3명의 전문가 에이전트 (영양사, 셰프, 예산 전문가)
- 병렬 실행 및 검증 시스템
- SSE 스트리밍 준비 완료

## 개발 워크플로우

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd meal-planner

# 2. mise로 런타임 설치
mise install

# 3. 백엔드 의존성 설치
mise run install-backend

# 4. 환경 변수 설정
cd meal-planner-back
cp .env.example .env
# .env 파일 수정

# 5. 테스트 실행
cd ..
mise run test-backend

# 6. 예제 실행
mise run run-example
```

## 환경 변수

백엔드 `.env` 파일 설정:

```env
# LLM 설정
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-3-5-haiku-latest

# Mock 모드 (API 호출 없이 테스트)
MOCK_MODE=true

# 로깅
LOG_LEVEL=INFO
```

## 참고 문서

- 📖 [MISE_GUIDE.md](MISE_GUIDE.md) - Scoop과 mise 완벽 가이드
  - Windows 개발 환경 설정
  - Scoop 설치 및 사용법
  - mise 설치 및 사용법
  - 트러블슈팅
- 📚 [meal-planner-back/README.md](meal-planner-back/README.md) - 백엔드 상세 가이드

## 라이센스

MIT
