"""
FastAPI 서버 - React 클라이언트와 CrewAI 에이전트 시스템 연결
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from dotenv import load_dotenv
import pymysql
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
    allow_origins=["*"],  # 모든 도메인 허용 (개발/테스트용)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    major_code: str
    admission_year: int

class ChatResponse(BaseModel):
    success: bool
    response: str
    student_id: str

# 데이터베이스 연결 함수
def get_db_connection():
    """MySQL 데이터베이스 연결"""
    try:
        conn = pymysql.connect(
            host=os.getenv('RDS_HOST'),
            port=int(os.getenv('RDS_PORT', 3306)),
            user=os.getenv('RDS_USERNAME'),
            password=os.getenv('RDS_PASSWORD'),
            database=os.getenv('RDS_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")
        raise HTTPException(status_code=500, detail='데이터베이스 연결에 실패했습니다.')

@app.post('/api/auth/verify', response_model=StudentResponse)
async def verify_student(request: StudentVerifyRequest):
    """학생 인증 API"""
    print(f"🔍 인증 요청 받음: {request.student_id}")
    try:
        if not request.student_id:
            raise HTTPException(status_code=400, detail='학번을 입력해주세요.')
        
        # 데이터베이스에서 학생 정보 조회
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT student_id, name, major_code, admission_year FROM students WHERE student_id = %s',
                (request.student_id,)
            )
            student = cursor.fetchone()
        conn.close()
        
        if student:
            print(f"✅ 학생 인증 성공: {student['name']}")
            return StudentResponse(
                success=True,
                student_id=str(student['student_id']),
                name=student['name'],
                major_code=student['major_code'],
                admission_year=student['admission_year']
            )
        else:
            print(f"❌ 등록되지 않은 학번: {request.student_id}")
            raise HTTPException(status_code=404, detail='등록되지 않은 학번입니다.')
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 서버 오류: {str(e)}")
        raise HTTPException(status_code=500, detail='서버 오류가 발생했습니다.')

@app.post('/api/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 API - CrewAI 에이전트 시스템 실행"""
    try:
        if not request.message or not request.student_id:
            raise HTTPException(status_code=400, detail='메시지와 학번이 필요합니다.')
        
        # 학생 재인증 (보안)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT student_id FROM students WHERE student_id = %s',
                (request.student_id,)
            )
            student = cursor.fetchone()
        conn.close()
        
        if not student:
            raise HTTPException(status_code=401, detail='인증되지 않은 사용자입니다.')
        
        # AgentSystem 초기화 및 비동기 실행
        print(f"🤖 AI 에이전트 시스템 초기화 중...")
        agent_system = AgentSystem(authenticated_student_id=request.student_id)
        print(f"💬 질문 처리 시작: {request.message}")
        response = await agent_system.process_query_async(request.message)
        print(f"✅ AI 응답 완료")
        
        return ChatResponse(
            success=True,
            response=str(response),
            student_id=request.student_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'처리 중 오류가 발생했습니다: {str(e)}')

@app.get('/')
async def root():
    """루트 경로 - 서버 상태 페이지"""
    from fastapi.responses import FileResponse
    return FileResponse('templates/index.html')

@app.get('/api/health')
async def health_check():
    """서버 상태 확인"""
    return {'status': 'healthy', 'message': '서버가 정상 작동 중입니다.'}

@app.options('/api/auth/verify')
async def options_verify():
    """CORS preflight 요청 처리"""
    return {"message": "OK"}

@app.options('/api/chat')
async def options_chat():
    """CORS preflight 요청 처리"""
    return {"message": "OK"}

def get_external_ip():
    """외부 IP 주소 조회"""
    try:
        import subprocess
        result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "localhost"

if __name__ == '__main__':
    import uvicorn
    
    # 외부 IP 주소 조회
    external_ip = get_external_ip()
    
    print("🚀 FastAPI 서버 시작")
    print(f"📍 React 클라이언트: http://{external_ip}:3000")
    print(f"📍 API 서버: http://{external_ip}:8000")
    print(f"📍 API 문서: http://{external_ip}:8000/docs")
    print("🔗 연결: React → FastAPI → CrewAI")
    print(f"💡 .env 파일 설정: REACT_APP_API_URL=http://{external_ip}:8000")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning"
    )