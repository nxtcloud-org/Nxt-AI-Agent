"""
Flask API 서버 - React 클라이언트와 CrewAI 에이전트 시스템 연결
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv
import sqlite3
from agent_system import AgentSystem

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)

# 데이터베이스 연결 함수
def get_db_connection():
    """데이터베이스 연결"""
    db_path = os.path.join('..', '0.data', 'university.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/auth/verify', methods=['POST'])
def verify_student():
    """학생 인증 API"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({'error': True, 'message': '학번을 입력해주세요.'}), 400
        
        # 데이터베이스에서 학생 정보 조회
        conn = get_db_connection()
        student = conn.execute(
            'SELECT student_id, name, department, admission_year FROM students WHERE student_id = ?',
            (student_id,)
        ).fetchone()
        conn.close()
        
        if student:
            return jsonify({
                'success': True,
                'student_id': student['student_id'],
                'name': student['name'],
                'department': student['department'],
                'admission_year': student['admission_year']
            })
        else:
            return jsonify({'error': True, 'message': '등록되지 않은 학번입니다.'}), 404
            
    except Exception as e:
        print(f"인증 오류: {str(e)}")
        return jsonify({'error': True, 'message': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """채팅 API - CrewAI 에이전트 시스템 실행"""
    try:
        data = request.get_json()
        message = data.get('message')
        student_id = data.get('student_id')
        
        if not message or not student_id:
            return jsonify({'error': True, 'message': '메시지와 학번이 필요합니다.'}), 400
        
        # 학생 재인증 (보안)
        conn = get_db_connection()
        student = conn.execute(
            'SELECT student_id FROM students WHERE student_id = ?',
            (student_id,)
        ).fetchone()
        conn.close()
        
        if not student:
            return jsonify({'error': True, 'message': '인증되지 않은 사용자입니다.'}), 401
        
        # AgentSystem 초기화 및 실행
        agent_system = AgentSystem(authenticated_student_id=student_id)
        response = agent_system.process_query(message)
        
        return jsonify({
            'success': True,
            'response': str(response),
            'student_id': student_id
        })
        
    except Exception as e:
        print(f"채팅 오류: {str(e)}")
        return jsonify({'error': True, 'message': f'처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({'status': 'healthy', 'message': '서버가 정상 작동 중입니다.'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': True, 'message': 'API 엔드포인트를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': True, 'message': '내부 서버 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    print("🚀 Flask API 서버 시작")
    print("📍 React 클라이언트: http://localhost:3000")
    print("📍 API 서버: http://localhost:8000")
    print("🔗 연결: React → Flask → CrewAI")
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )