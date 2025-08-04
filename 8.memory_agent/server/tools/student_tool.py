"""
학생 정보 조회 도구 (리팩토링 버전)
"""
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import sys
import os

# 상위 디렉토리의 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from base_tool import DatabaseManager, QueryValidator, ResultFormatter


class StudentToolInput(BaseModel):
    """Input schema for StudentTool."""
    query: str = Field(..., description="학생 정보 조회를 위한 자연어 설명")


class StudentTool(BaseTool):
    name: str = "student_tool"
    description: str = """
    인증된 본인의 학생 정보 조회 전용 도구입니다.
    개인정보 보호를 위해 본인 인증된 학생의 정보만 조회 가능합니다.
    사용 가능한 테이블: students, major
    - students 테이블: student_id, name, major_code, completed_semester, admission_year
    - major 테이블: college, department, dept_code, major_name, major_code
    
    주요 기능:
    1. 본인의 학적 정보 조회 (전공, 학년, 이수학기 등)
    2. 비슷한 조건 학생들의 익명화된 통계 정보 제공
    
    ⚠️ 주의: 이 도구는 조회/열람 전용입니다. 추천 기능은 제공하지 않습니다.
    
    사용법: "내 정보 조회", "나와 비슷한 학생들 정보" 등
    """
    args_schema: Type[BaseModel] = StudentToolInput
    authenticated_student_id: str = None

    def set_authenticated_user(self, student_id: str):
        """인증된 사용자 정보를 설정합니다."""
        self.authenticated_student_id = student_id

    def _run(self, query: str) -> str:
        """학생 정보 조회 실행"""
        try:
            # 자연어 검증
            validation_error = QueryValidator.validate_natural_language(query)
            if validation_error:
                return validation_error
            
            # 인증 확인
            if not self.authenticated_student_id:
                return "인증된 사용자 정보가 없습니다. 로그인이 필요합니다."
            
            # 쿼리 타입에 따른 처리
            if any(keyword in query for keyword in ["내", "정보", "학적", "현황", "분석"]):
                return self._get_my_info()
            elif any(keyword in query for keyword in ["나와 비슷한", "같은 조건"]):
                return self._get_similar_students_stats()
            else:
                return self._get_usage_guide()
        
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
    
    def _get_my_info(self) -> str:
        """본인 정보 조회"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor()
            
            sql_query = """
            SELECT 
                s.name as 학생이름,
                s.student_id as 학번,
                s.completed_semester as 이수학기,
                s.admission_year as 입학년도,
                s.major_code as 전공코드,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 소속
            FROM students s
            LEFT JOIN major m ON s.major_code = m.major_code
            WHERE s.student_id = %s
            """
            cursor.execute(sql_query, (self.authenticated_student_id,))
            result = cursor.fetchone()
            
            return ResultFormatter.format_student_info(result) if result else "학생 정보를 찾을 수 없습니다."
    
    def _get_similar_students_stats(self) -> str:
        """비슷한 조건 학생들의 통계 정보"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor()
            
            # 본인 정보 먼저 조회
            cursor.execute("""
                SELECT major_code, completed_semester, admission_year
                FROM students WHERE student_id = %s
            """, (self.authenticated_student_id,))
            
            my_info = cursor.fetchone()
            if not my_info:
                return "본인 정보를 찾을 수 없습니다."
            
            # 비슷한 조건 학생들 통계
            cursor.execute("""
                SELECT 
                    COUNT(*) as 학생수,
                    CASE 
                        WHEN m.major_name IS NOT NULL THEN 
                            CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                        ELSE 
                            CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                    END as 소속,
                    AVG(s.completed_semester) as 평균이수학기
                FROM students s
                LEFT JOIN major m ON s.major_code = m.major_code
                WHERE s.major_code = %s AND s.admission_year = %s
                GROUP BY s.major_code, m.college, m.department, m.major_name
            """, (my_info['major_code'], my_info['admission_year']))
            
            results = cursor.fetchall()
            
            if not results:
                return "비슷한 조건의 학생 정보가 없습니다."
            
            # 통계 정보 포맷팅
            result = "=== 비슷한 조건 학생들 통계 ===\n"
            for row in results:
                result += f"소속: {row['소속']}\n"
                result += f"동일 조건 학생 수: {row['학생수']}명\n"
                result += f"평균 이수 학기: {row['평균이수학기']:.1f}학기\n"
            
            return result
    
    def _get_usage_guide(self) -> str:
        """사용법 안내"""
        return """
        개인정보 보호를 위해 본인 인증된 정보만 조회 가능합니다.
        
        사용 가능한 명령어:
        - '내 정보 조회해주세요' - 본인의 학적 정보 확인
        - '나와 비슷한 학생들 정보' - 같은 조건 학생들의 익명화된 통계
        
        ⚠️ 주의: 다른 학생의 개인정보는 개인정보보호법에 따라 조회할 수 없습니다.
        """