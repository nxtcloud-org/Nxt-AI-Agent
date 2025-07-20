import os
import mysql.connector
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class StudentDBToolInput(BaseModel):
    """Input schema for StudentDBTool."""
    query: str = Field(..., description="SQL query or natural language description of what student information to retrieve")

class StudentDBTool(BaseTool):
    name: str = "student_db_tool"
    description: str = """
    인증된 본인의 학생 정보 조회 전용 도구입니다.
    개인정보 보호를 위해 본인 인증된 학생의 정보만 조회 가능합니다.
    
    주요 기능:
    1. 본인의 학적 정보 조회 (전공, 학년, 이수학기 등)
    2. 비슷한 조건 학생들의 익명화된 통계 정보 제공
    
    ⚠️ 주의: 이 도구는 조회/열람 전용입니다. 추천 기능은 제공하지 않습니다.
    
    사용법: "내 정보 조회", "나와 비슷한 학생들 정보" 등
    """
    args_schema: Type[BaseModel] = StudentDBToolInput

    def _run(self, query: str) -> str:
        """Execute database query for authenticated student information."""
        try:
            # Database connection
            connection = mysql.connector.connect(
                host=os.environ["RDS_HOST"],
                port=int(os.environ["RDS_PORT"]),
                database=os.environ["RDS_DATABASE"],
                user=os.environ["RDS_USERNAME"],
                password=os.environ["RDS_PASSWORD"]
            )
            cursor = connection.cursor(dictionary=True)
            
            # 현재 인증된 학생 (시뮬레이션용 - 실제로는 세션에서 가져옴)
            # 테스트를 위해 도윤정 학생으로 설정
            authenticated_student = "도윤정"
            
            # 자연어 쿼리 처리 - 개인정보 보호 준수
            if "내" in query and ("정보" in query or "학적" in query):
                # 본인 정보 조회
                sql_query = """
                SELECT 
                    s.name as 학생이름,
                    s.student_id as 학번,
                    s.completed_semester as 이수학기,
                    s.admission_year as 입학년도,
                    CASE 
                        WHEN m.major_name IS NOT NULL THEN 
                            CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                        ELSE 
                            CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                    END as 소속
                FROM students s
                LEFT JOIN major m ON s.major_code = m.major_code
                WHERE s.name = %s
                """
                cursor.execute(sql_query, (authenticated_student,))
                results = cursor.fetchall()
                
            elif "나와 비슷한" in query or "같은 조건" in query:
                # 본인과 비슷한 조건의 학생들 통계 (익명화)
                # 먼저 본인 정보 조회
                sql_query = """
                SELECT s.major_code, s.completed_semester, s.admission_year
                FROM students s
                WHERE s.name = %s
                """
                cursor.execute(sql_query, (authenticated_student,))
                my_info = cursor.fetchone()
                
                if my_info:
                    # 비슷한 조건의 학생 수 조회 (개인정보 제외)
                    sql_query = """
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
                    """
                    cursor.execute(sql_query, (my_info['major_code'], my_info['admission_year']))
                    results = cursor.fetchall()
                else:
                    return "본인 정보를 찾을 수 없습니다."
                    

            
            else:
                return """
                개인정보 보호를 위해 본인 인증된 정보만 조회 가능합니다.
                
                사용 가능한 명령어:
                - '내 정보 조회해주세요' - 본인의 학적 정보 확인
                - '나와 비슷한 학생들 정보' - 같은 조건 학생들의 익명화된 통계
                
                ⚠️ 주의: 이 도구는 조회/열람 전용입니다. 추천 기능은 별도 도구에서 제공됩니다.
                다른 학생의 개인정보는 개인정보보호법에 따라 조회할 수 없습니다.
                """
            
            if not results:
                return "조회된 데이터가 없습니다."
            
            # 결과 포맷팅
            if len(results) == 1:
                # 단일 정보 상세 표시
                info = results[0]
                formatted_result = "=== 조회 결과 ===\n"
                for key, value in info.items():
                    if value is not None:
                        formatted_result += f"{key}: {value}\n"
                return formatted_result
            else:
                # 통계 정보 표시
                formatted_results = []
                for i, row in enumerate(results, 1):
                    formatted_results.append(f"{i}. {dict(row)}")
                return "통계 결과:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()