# mise 완벽 가이드

## 목차

- [mise란?](#mise란)
- [왜 mise를 사용하는가?](#왜-mise를-사용하는가)
- [Windows 개발 환경 준비 - Scoop](#windows-개발-환경-준비---scoop)
- [설치](#설치)
- [기본 사용법](#기본-사용법)
- [설정 파일](#설정-파일)
- [고급 기능](#고급-기능)
- [유용한 명령어](#유용한-명령어)
- [트러블슈팅](#트러블슈팅)
- [참고 자료](#참고-자료)

---

## mise란?

**mise** (발음: "meez", 프랑스어로 "준비")는 개발 환경을 관리하는 범용 도구입니다.

### 주요 특징

- 🚀 **다중 런타임 관리**: Python, Node.js, Ruby, Go 등 70+ 언어/도구 지원
- 📦 **통합 도구**: 런타임, 환경 변수, 태스크를 하나의 파일로 관리
- ⚡ **빠른 성능**: Rust로 작성되어 asdf보다 20-200배 빠름
- 🔄 **자동 전환**: 디렉토리 진입 시 자동으로 올바른 버전 활성화
- 🛠️ **태스크 러너**: Makefile 대체, 프로젝트 작업 자동화

### mise vs 다른 도구

| 기능       | mise | asdf | nvm/pyenv | volta |
| -------- | ---- | ---- | --------- | ----- |
| 다중 언어 지원 | ✅    | ✅    | ❌         | ❌     |
| 성능       | ⚡⚡⚡  | ⚡    | ⚡⚡        | ⚡⚡    |
| 환경 변수 관리 | ✅    | ❌    | ❌         | ❌     |
| 태스크 러너   | ✅    | ❌    | ❌         | ❌     |
| 플러그인 필요  | ❌    | ✅    | N/A       | N/A   |

---

## 왜 mise를 사용하는가?

### 1. **단일 도구로 모든 것 관리**

```bash
# 과거: 여러 도구 필요
nvm use 20          # Node.js
pyenv local 3.13    # Python
rbenv local 3.2.0   # Ruby

# mise: 하나로 통합
mise install
```

### 2. **팀 협업 개선**

- `.mise.toml` 파일 하나로 팀 전체가 동일한 환경 사용
- "내 컴퓨터에서는 되는데..." 문제 해결

### 3. **프로젝트 자동화**

```toml
[tasks.test]
run = "pytest tests/ -v"

[tasks.dev]
run = "uvicorn app:main --reload"
```

### 4. **환경 변수 관리**

```toml
[env]
DATABASE_URL = "postgresql://localhost/mydb"
API_KEY = { file = ".secrets/api-key" }
```

---

## 설치

### Windows

#### Option 1: Scoop (권장)

```powershell
scoop install mise
```

#### Option 2: winget

```powershell
winget install jdx.mise
```

#### Option 3: 수동 설치

```powershell
# PowerShell에서 실행
irm https://mise.run | iex
```

### macOS

#### Option 1: Homebrew (권장)

```bash
brew install mise
```

#### Option 2: Curl

```bash
curl https://mise.run | sh
```

### Linux

#### Option 1: 공식 설치 스크립트

```bash
curl https://mise.run | sh
```

#### Option 2: apt (Ubuntu/Debian)

```bash
# GPG 키 추가
wget -qO - https://mise.jdx.dev/gpg-key.pub | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/mise-archive-keyring.gpg 1> /dev/null

# 저장소 추가
echo "deb [signed-by=/etc/apt/trusted.gpg.d/mise-archive-keyring.gpg arch=amd64] https://mise.jdx.dev/deb stable main" | sudo tee /etc/apt/sources.list.d/mise.list

# 설치
sudo apt update
sudo apt install mise
```

#### Option 3: dnf (Fedora/RHEL)

```bash
dnf install mise
```

### 설치 후 셸 설정

#### Bash

```bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
source ~/.bashrc
```

#### Zsh

```bash
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc
```

#### Fish

```bash
echo 'mise activate fish | source' >> ~/.config/fish/config.fish
```

#### PowerShell

```powershell
# PowerShell 프로필 열기
notepad $PROFILE

# 다음 줄 추가
mise activate pwsh | Out-String | Invoke-Expression
```

### 설치 확인

```bash
mise --version
# 출력: mise 2024.x.x
```

---

## 기본 사용법

### 1. 프로젝트 초기화

```bash
# 프로젝트 디렉토리로 이동
cd my-project

# Python 3.13 사용
mise use python@3.13

# Node.js 20 사용
mise use node@20
```

이 명령어들은 `.mise.toml` 파일을 자동으로 생성합니다.

### 2. 도구 설치

```bash
# .mise.toml에 정의된 모든 도구 설치
mise install

# 특정 도구만 설치
mise install python@3.13
mise install node@20.10.0
```

### 3. 버전 확인

```bash
# 현재 활성화된 버전 확인
mise current

# 출력 예시:
# python  3.13.0
# node    20.10.0

# 설치된 모든 버전 확인
mise list
```

### 4. 도구 사용

```bash
# mise가 설치한 도구는 자동으로 PATH에 추가됨
python --version  # Python 3.13.0
node --version    # v20.10.0
```

---

## 설정 파일

### `.mise.toml` 구조

```toml
# mise 설정 파일
# https://mise.jdx.dev/configuration.html

# 런타임 버전 정의
[tools]
python = "3.13"              # 최신 3.13.x
node = "20.10.0"             # 정확한 버전
ruby = "latest"              # 최신 버전
go = { version = "1.21" }    # 객체 형식

# 환경 변수
[env]
DATABASE_URL = "postgresql://localhost/mydb"
API_KEY = "secret-key"
NODE_ENV = "development"

# 파일에서 읽기
SECRET = { file = ".secrets/api-key" }

# 다른 환경 변수 참조
PATH = ["/custom/bin", "{{env.PATH}}"]

# 태스크 정의
[tasks.dev]
description = "Start development server"
run = "python manage.py runserver"

[tasks.test]
description = "Run tests"
run = "pytest tests/ -v"

[tasks.lint]
description = "Run linter"
run = [
    "black .",
    "flake8 .",
]

[tasks.deploy]
description = "Deploy to production"
depends = ["test"]  # test 태스크 먼저 실행
run = "bash deploy.sh"

# 서브 디렉토리 작업
[tasks.frontend-build]
description = "Build frontend"
dir = "frontend"
run = "npm run build"
```

### 설정 파일 우선순위

mise는 다음 순서로 설정을 찾습니다:

1. `.mise.local.toml` (로컬 오버라이드, gitignore에 추가)
2. `.mise.toml` (프로젝트 설정)
3. `~/.config/mise/config.toml` (글로벌 설정)

### 전역 설정

```bash
# 글로벌 Python 버전 설정
mise use -g python@3.12

# ~/.config/mise/config.toml 파일에 저장됨
```

---

## 고급 기능

### 1. 버전 범위 지정

```toml
[tools]
python = "3.13"      # 3.13.x 최신
node = "20"          # 20.x.x 최신
ruby = "~3.2.0"      # 3.2.0 <= version < 3.3.0
go = "^1.21.0"       # 1.21.0 <= version < 2.0.0
```

### 2. 여러 버전 동시 사용

```toml
[tools]
python = ["3.11", "3.12", "3.13"]  # 3개 버전 모두 설치
```

```bash
# 특정 버전 사용
python3.11 --version
python3.12 --version
python3.13 --version
```

### 3. 조건부 설정

```toml
[tools]
# OS별 다른 버전
python = "{{ if eq .os 'windows' }}3.12{{ else }}3.13{{ end }}"
```

### 4. 플러그인 사용

```bash
# 사용 가능한 플러그인 검색
mise plugins ls-remote | grep postgres

# PostgreSQL 플러그인 설치
mise plugins install postgres

# PostgreSQL 설치
mise install postgres@16
```

### 5. 환경별 설정

```toml
# .mise.toml
[env]
NODE_ENV = "development"

# .mise.production.toml
[env]
NODE_ENV = "production"
DATABASE_URL = "postgresql://prod-server/db"
```

```bash
# 프로덕션 환경 사용
export MISE_ENV=production
mise env
```

### 6. 태스크 고급 기능

#### 태스크 체이닝

```toml
[tasks.ci]
depends = ["lint", "test", "build"]
run = "echo 'CI complete'"
```

#### 파일 감시

```toml
[tasks.watch]
run = "pytest tests/"
sources = ["src/**/*.py", "tests/**/*.py"]
outputs = [".pytest_cache"]
```

#### 환경 변수 설정

```toml
[tasks.test]
run = "pytest"
env = { PYTHONPATH = "src", DEBUG = "true" }
```

---

## 유용한 명령어

### 버전 관리

```bash
# 사용 가능한 버전 확인
mise ls-remote python
mise ls-remote node

# 설치된 버전 확인
mise list
mise list python

# 특정 버전 설치
mise install python@3.13.0
mise install node@20.10.0

# 버전 제거
mise uninstall python@3.12
```

### 환경 관리

```bash
# 현재 환경 변수 확인
mise env

# 특정 셸에서 환경 변수 내보내기
mise env -s bash
mise env -s fish

# 현재 디렉토리 설정 확인
mise current
```

### 태스크 실행

```bash
# 사용 가능한 태스크 목록
mise tasks

# 태스크 실행
mise run test
mise run dev

# 태스크 정보 확인
mise task info test
```

### 설정 관리

```bash
# 현재 설정 확인
mise config

# 전역 설정 수정
mise settings set legacy_version_file false

# 전역 설정 확인
mise settings
```

### 업데이트

```bash
# mise 자체 업데이트
mise self-update

# 도구 업그레이드
mise upgrade python
mise upgrade --all  # 모든 도구 업그레이드
```

### 캐시 관리

```bash
# 캐시 확인
mise cache

# 캐시 정리
mise cache clear
```

### 디버깅

```bash
# 디버그 모드로 실행
mise --debug install python

# 추적 로그
mise --trace run test

# 의존성 트리 확인
mise which python
```

---

## 트러블슈팅

### 문제 1: mise 명령어를 찾을 수 없음

**증상**:

```bash
mise: command not found
```

**해결**:

```bash
# 셸 설정 확인
cat ~/.bashrc | grep mise
cat ~/.zshrc | grep mise

# 활성화 스크립트 추가 (Bash)
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
source ~/.bashrc

# 활성화 스크립트 추가 (Zsh)
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc
```

### 문제 2: 도구가 PATH에 없음

**증상**:

```bash
python: command not found
```

**해결**:

```bash
# mise 환경 다시 로드
mise activate

# 또는 셸 재시작
exec $SHELL

# PATH 확인
echo $PATH | grep mise
```

### 문제 3: 버전이 자동으로 전환되지 않음

**증상**:
디렉토리 이동 시 버전이 바뀌지 않음

**해결**:

```bash
# mise hook 설정 확인
mise doctor

# cd hook 수동 실행
eval "$(mise hook-env)"
```

### 문제 4: 설치 실패

**증상**:

```bash
mise install python@3.13
# Error: ...
```

**해결**:

```bash
# 의존성 설치 (Ubuntu/Debian)
sudo apt install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev

# 의존성 설치 (macOS)
brew install openssl readline sqlite3 xz zlib

# 재시도
mise install python@3.13 --verbose
```

### 문제 5: Windows에서 권한 오류

**증상**:

```powershell
# 실행 정책 오류
```

**해결**:

```powershell
# 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 관리자 권한으로 PowerShell 실행
```

### 문제 6: .mise.toml 문법 오류

**증상**:

```bash
Error parsing .mise.toml
```

**해결**:

```bash
# TOML 문법 검증
mise config ls

# 또는 온라인 TOML 검증기 사용
# https://www.toml-lint.com/
```

---

## 모범 사례

### 1. `.mise.toml` 버전 관리

```bash
# .mise.toml은 git에 추가
git add .mise.toml

# 로컬 오버라이드는 제외
echo '.mise.local.toml' >> .gitignore
```

### 2. 팀 협업

```toml
# 정확한 버전 명시 (팀 전체 동일한 환경)
[tools]
python = "3.13.0"  # 명확한 버전
node = "20.10.0"

# 환경 변수는 예시만 제공
[env]
DATABASE_URL = "postgresql://localhost/dev"  # 개발 환경 기본값
```

### 3. CI/CD 통합

```yaml
# GitHub Actions 예시
name: CI

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install mise
        run: curl https://mise.run | sh

      - name: Install tools
        run: |
          eval "$(mise activate bash)"
          mise install

      - name: Run tests
        run: mise run test
```

### 4. 문서화

```toml
# .mise.toml에 주석 추가
[tasks.test]
description = "Run all tests with coverage"  # 명확한 설명
run = "pytest tests/ --cov"
```

---

## 참고 자료

### 공식 문서

- 📖 [mise 공식 문서](https://mise.jdx.dev/)
- 💻 [GitHub 저장소](https://github.com/jdx/mise)
- 📝 [설정 레퍼런스](https://mise.jdx.dev/configuration.html)
- 🎯 [태스크 가이드](https://mise.jdx.dev/tasks/)

### 커뮤니티

- 💬 [Discord](https://discord.gg/UBa7pJUN7Z)
- 🐦 [Twitter/X](https://twitter.com/jdxcode)
- 📢 [토론 포럼](https://github.com/jdx/mise/discussions)

### 비교 및 마이그레이션

- [asdf에서 마이그레이션](https://mise.jdx.dev/getting-started.html#migrating-from-asdf)
- [rtx → mise 변경사항](https://mise.jdx.dev/rtx.html)
- [도구 비교](https://mise.jdx.dev/comparison-to-asdf.html)

### 추가 자료

- 🎬 [YouTube 튜토리얼](https://www.youtube.com/results?search_query=mise+dev+tools)
- 📚 [예제 프로젝트](https://github.com/jdx/mise/tree/main/examples)
- 🔧 [플러그인 목록](https://github.com/mise-plugins)

---

## 빠른 참조

### 자주 사용하는 명령어

```bash
# 설치 및 사용
mise use python@3.13          # 프로젝트에 Python 3.13 추가
mise install                  # 모든 도구 설치
mise list                     # 설치된 도구 확인

# 태스크
mise tasks                    # 사용 가능한 태스크 목록
mise run <task>               # 태스크 실행

# 정보
mise current                  # 현재 버전 확인
mise which python             # 실행 파일 경로 확인
mise doctor                   # 환경 진단

# 업데이트
mise upgrade                  # 도구 업그레이드
mise self-update              # mise 업데이트
```

### 도움말

```bash
# 전체 도움말
mise --help

# 특정 명령어 도움말
mise install --help
mise use --help
mise run --help
```

---

**문서 버전**: 1.0
**최종 업데이트**: 2026-01-01
**mise 버전**: 2024.x 기준

이 가이드에 대한 피드백이나 개선 사항이 있으면 이슈를 열어주세요.
