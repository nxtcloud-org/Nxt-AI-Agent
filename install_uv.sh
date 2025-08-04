#!/bin/bash

# Nxt AI Agent - UV 설치 스크립트
# Python UV 패키지 매니저와 필요한 패키지들을 설치합니다.

set -e

echo "🚀 Nxt AI Agent 환경 설정을 시작합니다..."
echo

# UV 설치
echo "📦 UV 패키지 매니저 설치 중..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ UV 설치 완료"
else
    echo "✅ UV가 이미 설치되어 있습니다"
fi

# 가상환경 생성
echo
echo "🐍 Python 가상환경 생성 중..."
uv venv
source .venv/bin/activate
echo "✅ 가상환경 생성 및 활성화 완료"

# 프로젝트 초기화
echo
echo "📁 프로젝트 초기화 중..."
uv init
echo "✅ 프로젝트 초기화 완료"

# 패키지 설치
echo
echo "📚 필요한 패키지 설치 중..."
uv add crewai python-dotenv mysql-connector-python psycopg2-binary \
       langchain-aws boto3 pydantic pandas pymysql sqlalchemy \
       tabulate fastapi uvicorn
echo "✅ 패키지 설치 완료"

echo
echo "🎉 설치 완료!"
echo
echo "다음 단계:"
echo "1. 가상환경 활성화: source .venv/bin/activate"
echo "2. 프로젝트 실행: uv run your_script.py"
echo