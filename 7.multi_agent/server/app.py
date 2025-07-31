"""
FastAPI 서버 - React 클라이언트와 CrewAI 에이전트 시스템 연결
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from dotenv import load_dotenv
import sqlite3
from agent_system import AgentSystem
import logging

# 환경 변수 로드
load_dotenv()

# 로깅 설정 - 디버깅 메시지 제거
logging.getLogger("crewai").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Student Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 개발 환경
        "https://*.s3-website-*.amazonaws.com",  # S3 정적 웹사이트
        "https://*.s3.amazonaws.com",  # S3 버킷 직접 접근
        "*"  # 모든 도메인 허용 (보안상 주의)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 모델
class StudentVerifyRequest(BaseModel):
    student_id: str

class ChatRequest(BaseModel):
    message: str
    student_id: str

class StudentResponse(BaseModel):
    success: bool
    student_id: str
    name: str
    department: str
    admission_year: int

class ChatResponse(BaseModel):
    success: bool
    response: str
    student_id: str

# 데이터베이스 연결 함수
def get_db_connection():
    """데이터베이스 연결"""
    db_path = os.path.join('..', '0.data', 'university.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.post('/api/auth/verify', response_model=StudentResponse)
async def verify_student(request: StudentVerifyRequest):
    """학생 인증 API"""
    try:
        if not request.student_id:
            raise HTTPException(status_code=400, detail='학번을 입력해주세요.')
        
        # 데이터베이스에서 학생 정보 조회
        conn = get_db_connection()
        student = conn.execute(
            'SELECT student_id, name, department, admission_year FROM students WHERE student_id = ?',
            (request.student_id,)
        ).fetchone()
        conn.close()
        
        if student:
            return StudentResponse(
                success=True,
                student_id=student['student_id'],
                name=student['name'],
                department=student['department'],
                admission_year=student['admission_year']
            )
        else:
            raise HTTPException(status_code=404, detail='등록되지 않은 학번입니다.')
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail='서버 오류가 발생했습니다.')

@app.post('/api/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 API - CrewAI 에이전트 시스템 실행"""
    try:
        if not request.message or not request.student_id:
            raise HTTPException(status_code=400, detail='메시지와 학번이 필요합니다.')
        
        # 학생 재인증 (보안)
        conn = get_db_connection()
        student = conn.execute(
            'SELECT student_id FROM students WHERE student_id = ?',
            (request.student_id,)
        ).fetchone()
        conn.close()
        
        if not student:
            raise HTTPException(status_code=401, detail='인증되지 않은 사용자입니다.')
        
        # AgentSystem 초기화 및 비동기 실행
        agent_system = AgentSystem(authenticated_student_id=request.student_id)
        response = await agent_system.process_query_async(request.message)
        
        return ChatResponse(
            success=True,
            response=str(response),
            student_id=request.student_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'처리 중 오류가 발생했습니다: {str(e)}')

@app.get('/api/health')
async def health_check():
    """서버 상태 확인"""
    return {'status': 'healthy', 'message': '서버가 정상 작동 중입니다.'}

if __name__ == '__main__':
    import uvicorn
    print("🚀 FastAPI 서버 시작")
    print("📍 React 클라이언트: http://localhost:3000")
    print("📍 API 서버: http://localhost:8000")
    print("📍 API 문서: http://localhost:8000/docs")
    print("🔗 연결: React → FastAPI → CrewAI")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning"
    )