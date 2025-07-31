# 🎓 멀티 에이전트 학사 상담 시스템

React 클라이언트와 CrewAI 기반 멀티 에이전트 시스템을 연결한 웹 애플리케이션입니다.

## 🏗️ 시스템 구조

```
7.multi_agent/
├── client/                 # React 프론트엔드
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginForm.js      # 학생 인증 폼
│   │   │   └── ChatInterface.js  # 채팅 인터페이스
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── server/                 # Flask API 백엔드
│   ├── tools/             # CrewAI 도구들
│   ├── app.py            # Flask API 서버
│   ├── agent_system.py   # CrewAI 멀티 에이전트 시스템
│   ├── pyproject.toml    # uv 프로젝트 설정
│   └── requirements.txt  # pip 호환성용
└── README.md
```

## 🔄 동작 흐름

1. **학생 인증**: 클라이언트에서 학번 입력 → DB 조회로 학생 확인
2. **채팅 시작**: 인증된 학생만 AI 에이전트와 대화 가능
3. **질문 처리**: React → Flask API → CrewAI 멀티 에이전트 → 응답 반환

## 🚀 실행 방법

### 1. 서버 실행 (터미널 1)

```bash
cd 7.multi_agent/server
uv run app.py
```

### 2. 클라이언트 실행 (터미널 2)

```bash
cd 7.multi_agent/client
npm install  # 처음 실행 시에만
npm start
```

### 3. 접속

- **클라이언트**: http://localhost:3000
- **API 서버**: http://localhost:8000

## 📋 주요 기능

### 클라이언트 (React)

- 🔐 학번 기반 학생 인증
- 💬 실시간 채팅 인터페이스
- 💡 추천 질문 제공
- 📱 반응형 디자인

### 서버 (Flask + CrewAI)

- 🔍 학생 인증 API (`/api/auth/verify`)
- 💬 채팅 API (`/api/chat`)
- 🤖 멀티 에이전트 시스템 연동
- 🛡️ 보안 검증

### AI 에이전트 시스템

- 👨‍🎓 **학생 정보 전문가**: 기본 정보 및 수강 이력 조회
- 🎓 **졸업 요건 전문가**: 졸업 요건 및 학점 정보
- 📚 **강의 정보 전문가**: 강의 검색 및 정보 제공
- 💡 **수강 추천 전문가**: 개인화된 수강 추천
- 📝 **요약 전문가**: 정보 종합 및 요약

## 🔧 환경 설정

### 서버 환경 변수 (.env)

```env
BEDROCK_MODEL_ID=your_model_id
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
```

### 데이터베이스

- SQLite 데이터베이스 (`../0.data/university.db`) 필요
- 학생 정보 테이블 (`students`) 필요

## 🛠️ 기술 스택

### 프론트엔드

- React 18
- CSS3 (모던 스타일링)
- Fetch API

### 백엔드

- Flask (Python 웹 프레임워크)
- Flask-CORS (CORS 처리)
- SQLite (데이터베이스)
- uv (Python 패키지 관리)

### AI 시스템

- CrewAI (멀티 에이전트 프레임워크)
- AWS Bedrock (LLM)
- LangChain (AI 도구 체인)

## 📝 사용 예시

1. **학번 입력**: `20230578`
2. **인증 완료**: "안녕하세요 김철수님!"
3. **질문 입력**: "내 졸업 요건 알려줘"
4. **AI 응답**: 멀티 에이전트가 협력하여 상세한 답변 제공

## 🔒 보안 기능

- 학번 기반 사용자 인증
- API 요청 시 재인증 검증
- 개인정보 보호 준수
- CORS 정책 적용

## 🎯 주요 특징

- **실시간 채팅**: 자연스러운 대화형 인터페이스
- **멀티 에이전트**: 전문 분야별 에이전트 협력
- **개인화**: 인증된 학생 정보 기반 맞춤 서비스
- **확장성**: 새로운 에이전트 및 기능 추가 용이

## 🚨 주의사항

- 서버와 클라이언트를 모두 실행해야 정상 작동
- 데이터베이스 파일 경로 확인 필요
- AWS Bedrock 설정 및 권한 필요
- Node.js 및 Python 환경 필요
