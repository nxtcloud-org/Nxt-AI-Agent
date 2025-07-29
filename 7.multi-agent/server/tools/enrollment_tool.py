"""
수강 이력 조회 도구 (리팩토링 버전)
"""
from crewai.tools import BaseTool
from typing import Type, List, Dict
from pydantic import BaseModel, Field
import sys
import os

# 상위 디렉토리의 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from base_tool import DatabaseManager, QueryValidator, ResultFormatter
from query_parser import QueryParser


class EnrollmentToolInput(BaseModel):
    """Input schema for EnrollmentTool."""
    query: str = Field(..., description="이수 과목 검색을 위한 자연어 설명")


class EnrollmentTool(BaseTool):
    name: str = "enrollment_tool"
    description: str = """
    인증된 본인의 이수 과목 조회 전용 도구입니다.
    개인정보 보호를 위해 본인 인증된 학생의 이수 과목만 조회 가능합니다.
    
    사용 가능한 테이블: enrollments, courses, major
    - enrollments 테이블: student_id, course_code, enrollment_type, earned_credits, offering_department, enrollment_semester, grade
    - courses 테이블: course_code, course_name, credits, course_type, department, professor, note, target_grade
    - major 테이블: college, department, dept_code, major_name, major_code
    
    주요 기능:
    1. 본인의 이수 과목 목록 조회
    2. 학기별 이수 과목 조회
    3. 성적별 이수 과목 조회 (A+, A, B+ 등)
    4. 학점별 이수 과목 조회
    5. 과목 유형별 이수 과목 조회 (전공필수, 전공선택, 교양 등)
    
    ⚠️ 주의: 이 도구는 조회/열람 전용입니다. 추천 기능은 제공하지 않습니다.
    
    사용법: "내가 이수한 과목", "지난 학기 들은 과목", "A학점 받은 과목" 등
    """
    args_schema: Type[BaseModel] = EnrollmentToolInput
    authenticated_student_id: str = None

    def set_authenticated_user(self, student_id: str):
        """인증된 사용자 정보를 설정합니다."""
        self.authenticated_student_id = student_id

    def _run(self, query: str) -> str:
        """수강 이력 조회 실행"""
        try:
            # 자연어 검증
            validation_error = QueryValidator.validate_natural_language(query)
            if validation_error:
                return validation_error
            
            # 인증 확인
            if not self.authenticated_student_id:
                return "인증된 사용자 정보가 없습니다. 로그인이 필요합니다."
            
            # 이수 과목 존재 여부 확인
            if not self._check_enrollment_exists():
                return f"학번 {self.authenticated_student_id} 학생의 이수 과목 정보가 없습니다."
            
            # 쿼리 타입에 따른 처리
            if any(keyword in query for keyword in ["내가 이수한", "내 이수", "들은 과목"]):
                return self._get_all_enrollments()
            elif any(keyword in query for keyword in ["학기별", "학기"]):
                return self._get_enrollments_by_semester(query)
            elif any(keyword in query for keyword in ["성적"]) or any(grade in query for grade in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']):
                return self._get_enrollments_by_grade(query)
            elif any(keyword in query for keyword in ["통계", "요약"]):
                return self._get_enrollment_statistics()
            else:
                return self._get_usage_guide()
        
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
    
    def _check_enrollment_exists(self) -> bool:
        """이수 과목 존재 여부 확인"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(DISTINCT course_code) as count FROM enrollments WHERE student_id = %s", 
                         (self.authenticated_student_id,))
            result = cursor.fetchone()
            return result and result['count'] > 0
    
    def _get_all_enrollments(self) -> str:
        """전체 이수 과목 조회"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            sql_query = """
            SELECT DISTINCT
                e.course_code as 과목코드,
                c.course_name as 과목명,
                e.earned_credits as 취득학점,
                e.enrollment_type as 이수구분,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 개설학과,
                e.enrollment_semester as 이수학기,
                e.grade as 성적
            FROM enrollments e
            LEFT JOIN courses c ON e.course_code = c.course_code
            LEFT JOIN major m ON e.offering_department = m.major_code
            WHERE e.student_id = %s
            ORDER BY e.enrollment_semester DESC, e.course_code
            """
            cursor.execute(sql_query, (self.authenticated_student_id,))
            results = cursor.fetchall()
            
            return self._format_enrollment_results(results, "전체 이수 과목")
    
    def _get_enrollments_by_semester(self, query: str) -> str:
        """학기별 이수 과목 조회"""
        conditions = QueryParser.parse_enrollment_conditions(query)
        
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            sql_query = """
            SELECT 
                e.course_code as 과목코드,
                c.course_name as 과목명,
                e.earned_credits as 취득학점,
                e.enrollment_type as 이수구분,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 개설학과,
                e.enrollment_semester as 이수학기,
                e.grade as 성적
            FROM enrollments e
            LEFT JOIN courses c ON e.course_code = c.course_code
            LEFT JOIN major m ON e.offering_department = m.major_code
            WHERE e.student_id = %s
            """
            params = [self.authenticated_student_id]
            
            if conditions['semester']:
                sql_query += " AND e.enrollment_semester = %s"
                params.append(conditions['semester'])
            
            sql_query += " ORDER BY e.enrollment_semester DESC, e.course_code"
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            title = f"{conditions['semester']} 이수 과목" if conditions['semester'] else "학기별 이수 과목"
            return self._format_enrollment_results(results, title)
    
    def _get_enrollments_by_grade(self, query: str) -> str:
        """성적별 이수 과목 조회"""
        conditions = QueryParser.parse_enrollment_conditions(query)
        
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            sql_query = """
            SELECT 
                e.course_code as 과목코드,
                c.course_name as 과목명,
                e.earned_credits as 취득학점,
                e.enrollment_type as 이수구분,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 개설학과,
                e.enrollment_semester as 이수학기,
                e.grade as 성적
            FROM enrollments e
            LEFT JOIN courses c ON e.course_code = c.course_code
            LEFT JOIN major m ON e.offering_department = m.major_code
            WHERE e.student_id = %s
            """
            params = [self.authenticated_student_id]
            
            if conditions['grade']:
                sql_query += " AND e.grade = %s"
                params.append(conditions['grade'])
            
            sql_query += " ORDER BY e.enrollment_semester DESC, e.grade DESC"
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            title = f"{conditions['grade']} 성적 과목" if conditions['grade'] else "성적별 이수 과목"
            return self._format_enrollment_results(results, title)
    
    def _get_enrollment_statistics(self) -> str:
        """이수 과목 통계 정보"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            # 전체 통계
            cursor.execute("""
                SELECT 
                    COUNT(*) as 총이수과목수,
                    SUM(e.earned_credits) as 총취득학점,
                    AVG(CASE 
                        WHEN e.grade = 'A+' THEN 4.5
                        WHEN e.grade = 'A' THEN 4.0
                        WHEN e.grade = 'B+' THEN 3.5
                        WHEN e.grade = 'B' THEN 3.0
                        WHEN e.grade = 'C+' THEN 2.5
                        WHEN e.grade = 'C' THEN 2.0
                        WHEN e.grade = 'D+' THEN 1.5
                        WHEN e.grade = 'D' THEN 1.0
                        ELSE 0
                    END) as 평균평점
                FROM enrollments e
                WHERE e.student_id = %s
            """, (self.authenticated_student_id,))
            
            total_stats = cursor.fetchone()
            
            # 이수구분별 통계
            cursor.execute("""
                SELECT 
                    e.enrollment_type as 이수구분,
                    COUNT(*) as 과목수,
                    SUM(e.earned_credits) as 취득학점
                FROM enrollments e
                WHERE e.student_id = %s
                GROUP BY e.enrollment_type
                ORDER BY 과목수 DESC
            """, (self.authenticated_student_id,))
            
            type_stats = cursor.fetchall()
            
            return self._format_statistics(total_stats, type_stats)
    
    def _format_enrollment_results(self, results: List[Dict], title: str) -> str:
        """이수 과목 결과 포맷팅"""
        if not results:
            return "조회된 이수 과목이 없습니다."
        
        total_count = len(results)
        display_limit = 15
        display_results = results[:display_limit]
        
        formatted_results = []
        for i, course in enumerate(display_results, 1):
            course_info = f"{i}. [{course.get('과목코드', 'N/A')}] {course.get('과목명', 'N/A')}"
            
            if course.get('취득학점'):
                course_info += f" ({course['취득학점']}학점)"
            if course.get('성적'):
                course_info += f" - {course['성적']}"
            if course.get('이수학기'):
                course_info += f" - {course['이수학기']}"
            if course.get('이수구분'):
                course_info += f" - {course['이수구분']}"
                
            formatted_results.append(course_info)
        
        result = f"{title} ({total_count}개):\n" + "\n".join(formatted_results)
        if total_count > display_limit:
            result = f"총 {total_count}개 중 상위 {display_limit}개 표시:\n" + "\n".join(formatted_results)
        
        return result
    
    def _format_statistics(self, total_stats: Dict, type_stats: List[Dict]) -> str:
        """통계 정보 포맷팅"""
        result = "=== 이수 과목 통계 ===\n"
        
        if total_stats:
            result += f"총 이수 과목: {total_stats['총이수과목수']}개\n"
            result += f"총 취득 학점: {total_stats['총취득학점']}학점\n"
            result += f"평균 평점: {total_stats['평균평점']:.2f}/4.5\n\n"
        
        result += "=== 이수구분별 현황 ===\n"
        for i, row in enumerate(type_stats, 1):
            result += f"{i}. {row['이수구분']}: {row['과목수']}과목 ({row['취득학점']}학점)\n"
        
        return result
    
    def _get_usage_guide(self) -> str:
        """사용법 안내"""
        return """
        개인정보 보호를 위해 본인 인증된 이수 과목만 조회 가능합니다.
        
        사용 가능한 명령어:
        - '내가 이수한 과목 보여주세요' - 전체 이수 과목 목록
        - '2024-1학기에 들은 과목' - 특정 학기 이수 과목
        - 'A학점 받은 과목' - 특정 성적의 이수 과목
        - '전공필수 과목' - 과목 유형별 이수 과목
        - '이수 과목 통계' - 이수 현황 요약 정보
        """