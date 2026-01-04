# AI 맞춤 식단 플래너 - 동작 예시

## 실제 동작 URL

- **배포 URL**: http://54.252.234.206:3000/
- **GitHub**: https://github.com/aiStudy001/meal-planner

## 1. 홈 화면

![홈 화면](screenshots/demo/01-home-landing.png)
*AI 맞춤 식단 플래너의 메인 화면입니다. 영양 균형, 조리 시간 고려, 예산 관리의 3가지 핵심 기능을 제공합니다.*

## 2. 사용자 정보 입력

### Step 1: 기본 정보

![기본 정보](screenshots/demo/02-input-step1-basic.png)
*성별, 나이, 키, 몸무게, 목표, 활동량을 입력합니다.*

### Step 2: 제한 사항

![제한 사항](screenshots/demo/03-input-step2-restrictions.png)
*알레르기, 식단 선호도, 건강 상태를 선택합니다.*

### Step 3: 조리 설정

![조리 설정](screenshots/demo/04-input-step3-cooking.png)
*조리 시간, 실력 수준, 하루 끼니 수, 식단 기간을 설정합니다.*

### Step 4: 예산 및 최종 확인

![예산 설정](screenshots/demo/05-input-step4-budget.png)
*예산을 입력하고 전체 설정을 최종 확인합니다.*

## 3. 식단 생성 과정

### 진행 중

![생성 진행](screenshots/demo/06-processing-in-progress.png)
*Multi-Agent AI 시스템이 실시간으로 식단을 생성합니다. SSE를 통해 진행 상황이 실시간 업데이트됩니다.*

### 완성

![생성 완료](screenshots/demo/07-processing-complete.png)
*5일치 식단이 완성되었습니다. 총 끼니 수, 평균 칼로리, 총 비용이 요약되어 표시됩니다.*
