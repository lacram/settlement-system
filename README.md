# Settlement System

Python과 Streamlit, SQLite를 활용한 간편 정산 관리 웹앱입니다.

## 주요 기능
- 여러 명이 함께 사용한 금액을 입력하고, 각 참여자가 부담해야 할 금액을 자동 계산
- 거래 내역(설명, 금액, 날짜, 참여자) 관리 및 수정/삭제
- 정산 결과 자동 계산 및 저장
- 과거 정산 기록 조회 및 안전한 삭제(2단계 확인)
- 모바일/데스크톱 반응형 UI, 다크 모드 지원

## 설치 및 실행
1. Python 3.8 이상이 필요합니다.
2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
3. 앱 실행:
   ```bash
   streamlit run settlement_app.py
   ```

## 사용법
1. **거래 입력**: 설명, 금액, 날짜, 참여자 입력 후 저장
2. **정산 결과**: 자동 계산된 결과 확인 및 정산 이름/날짜로 저장
3. **정산 기록**: 과거 정산 내역 조회 및 필요시 삭제

## 데이터베이스
- 모든 데이터는 프로젝트 폴더 내 `settlement.db`(SQLite) 파일에 저장됩니다.
- 거래 내역과 정산 기록이 영구적으로 보존됩니다.

## 기술 스택
- Python, Streamlit
- SQLite (내장 DB)
- 반응형 웹 UI

## 배포 및 공유
- 로컬에서 실행하거나, GitHub/Streamlit Cloud 등으로 손쉽게 배포 가능
- `.gitignore`에 DB, 임시파일, 업로드 폴더 등 포함

## 문의
- 개발: lacram (github.com/lacram)
- 이슈 및 제안: GitHub Issue 활용

---

**간편하고 직관적인 정산 관리가 필요하다면 이 프로젝트를 활용해보세요!** 