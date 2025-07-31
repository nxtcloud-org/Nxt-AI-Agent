"""
강의 정보 검색 도구 (리팩토링 버전)
"""
from crewai.tools import BaseTool
from typing import Type, List, Dict, Tuple
from pydantic import BaseModel, Field
import sys
import os

# 상위 디렉토리의 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from base_tool import DatabaseManager, QueryValidator, ResultFormatter
from semester_utils import SemesterManager
from query_parser import QueryParser


class CourseToolInput(BaseModel):
    """Input schema for CourseTool."""
    query: str = Field(..., description="강의 검색을 위한 자연어 질문")


class CourseTool(BaseTool):
    name: str = "course_tool"
    description: str = """
    강의 정보 조회/검색 전용 도구입니다.
    사용 가능한 테이블: courses, major
    - courses 테이블: course_code, course_name, credits, course_type, department(major_code), professor, note, target_grade, offered_year, offered_semester
    - major 테이블: college, department, dept_code, major_name, major_code
    
    주요 기능:
    1. 강의 정보 검색 (학과별, 교수별, 학년별, 키워드별)
    2. 학기별 개설 강의 조회 (다음/지난/현재 학기)
    3. 전공명, 학과명, 단과대학명으로 검색 가능
    
    ⚠️ 주의: 이 도구는 조회/검색 전용입니다. 추천 기능은 제공하지 않습니다.
    
    예: "국문학과 관련 강의", "다음 학기 개설 과목", "김철수 교수 강의" 등
    target_grade는 특정 학년 외에 2-4의 경우 2학년부터 4학년까지라는 의미이며, 어떤 과목은 전체 학년이 수강 가능하기도 합니다.
    """
    args_schema: Type[BaseModel] = CourseToolInput

    def _run(self, query: str) -> str:
        """강의 정보 검색 실행"""
        try:
            # 자연어 검증
            validation_error = QueryValidator.validate_natural_language(query)
            if validation_error:
                return validation_error
            
            # 학기 정보 가져오기
            semester_info = SemesterManager.get_current_semester_info()
            
            # 특별 케이스 처리
            if "다음 학기" in query or "다음학기" in query:
                return self._search_by_semester(semester_info, "next")
            elif "지난 학기" in query or "이전 학기" in query:
                return self._search_by_semester(semester_info, "prev")
            elif "이번 학기" in query or "현재 학기" in query:
                return self._search_by_semester(semester_info, "current")
            elif "전체" in query or "모든" in query:
                return self._search_all_courses(semester_info)
            else:
                return self._search_by_conditions(query, semester_info)
        
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
    
    def _search_by_semester(self, semester_info: Dict, semester_type: str) -> str:
        """학기별 강의 검색"""
        if semester_type == "current" and not semester_info['current_semester']:
            return self._format_vacation_message(semester_info)
        
        # 학기 정보 설정
        semester_map = {
            "next": (semester_info['next_semester_year'], semester_info['next_semester']),
            "prev": (semester_info['prev_semester_year'], semester_info['prev_semester']),
            "current": (semester_info['current_semester_year'], semester_info['current_semester'])
        }
        
        year, semester = semester_map[semester_type]
        
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            sql_query = """
            SELECT 
                c.course_code as 과목코드,
                c.course_name as 과목명,
                c.credits as 학점,
                c.course_type as 과목구분,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 개설학과,
                c.professor as 교수,
                c.target_grade as 대상학년
            FROM courses c
            LEFT JOIN major m ON c.department = m.major_code
            WHERE c.offered_year = %s AND c.offered_semester = %s
            ORDER BY m.college, m.department, c.course_name
            """
            cursor.execute(sql_query, (year, semester))
            results = cursor.fetchall()
            
            context = SemesterManager.format_semester_context(semester_info, semester_type)
            formatted_result = ResultFormatter.format_course_list(results, f"{year}년 {semester}학기 개설 강의")
            
            return context + formatted_result
    
    def _search_all_courses(self, semester_info: Dict) -> str:
        """전체 강의 검색"""
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            sql_query = """
            SELECT 
                c.course_code as 과목코드,
                c.course_name as 과목명,
                c.credits as 학점,
                c.course_type as 과목구분,
                CASE 
                    WHEN m.major_name IS NOT NULL THEN 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                    ELSE 
                        CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
                END as 개설학과,
                c.professor as 교수,
                c.target_grade as 대상학년
            FROM courses c
            LEFT JOIN major m ON c.department = m.major_code
            ORDER BY m.college, m.department, c.course_name
            """
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            context = SemesterManager.format_semester_context(semester_info, "all")
            return context + ResultFormatter.format_course_list(results, "전체 강의 목록")
    
    def _search_by_conditions(self, query: str, semester_info: Dict) -> str:
        """조건별 강의 검색"""
        conditions = QueryParser.parse_course_conditions(query)
        
        # 조건이 없으면 안내 메시지
        if not any(conditions.values()):
            return self._get_usage_guide()
        
        sql_query, params = self._build_dynamic_query(conditions)
        
        with DatabaseManager.mysql_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            return ResultFormatter.format_course_list(results, "검색 결과")
    
    def _build_dynamic_query(self, conditions: Dict) -> Tuple[str, List]:
        """동적 SQL 쿼리 생성"""
        base_query = """
        SELECT 
            c.course_code as 과목코드,
            c.course_name as 과목명,
            c.credits as 학점,
            c.course_type as 과목구분,
            CASE 
                WHEN m.major_name IS NOT NULL THEN 
                    CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''), ' ', m.major_name)
                ELSE 
                    CONCAT(COALESCE(m.college, ''), ' ', COALESCE(m.department, ''))
            END as 개설학과,
            c.professor as 교수,
            c.target_grade as 대상학년
        FROM courses c
        LEFT JOIN major m ON c.department = m.major_code
        WHERE 1=1
        """
        
        params = []
        
        # 학년 조건
        if conditions['grade']:
            base_query += " AND (c.target_grade = %s OR c.target_grade LIKE %s OR c.target_grade = '전체')"
            params.extend([conditions['grade'], f"%{conditions['grade']}%"])
        
        # 학과 조건 (동의어 지원)
        if conditions['department']:
            dept_keywords = conditions['department'] if isinstance(conditions['department'], list) else [conditions['department']]
            dept_conditions = []
            for keyword in dept_keywords:
                dept_conditions.extend(["m.department LIKE %s", "m.major_name LIKE %s", "m.college LIKE %s"])
                keyword_pattern = f"%{keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            base_query += f" AND ({' OR '.join(dept_conditions)})"
        
        # 과목 키워드 조건 (동의어 지원)
        if conditions['subject_keyword']:
            subject_keywords = conditions['subject_keyword'] if isinstance(conditions['subject_keyword'], list) else [conditions['subject_keyword']]
            subject_conditions = []
            for keyword in subject_keywords:
                subject_conditions.extend(["c.course_name LIKE %s", "m.department LIKE %s", "m.major_name LIKE %s"])
                keyword_pattern = f"%{keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            base_query += f" AND ({' OR '.join(subject_conditions)})"
        
        # 교수 조건
        if conditions['professor']:
            base_query += " AND c.professor LIKE %s"
            params.append(f"%{conditions['professor']}%")
        
        base_query += " ORDER BY m.college, m.department, c.course_name"
        
        return base_query, params
    
    def _format_vacation_message(self, semester_info: Dict) -> str:
        """방학 기간 메시지"""
        return f"""
        📅 현재 날짜: {semester_info['current_date']}
        현재는 방학 기간입니다.
        
        📚 다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기
        📚 지난 학기: {semester_info['prev_semester_year']}년 {semester_info['prev_semester']}학기
        
        "다음 학기" 또는 "지난 학기" 강의를 검색해보세요.
        """
    
    def _get_usage_guide(self) -> str:
        """사용법 안내"""
        return """
        강의 검색 예시:
        - '3학년 과목 중 한국역사학과 개설 강의 알려줘'
        - '심리학 관련 강의 검색해줘'
        - '김철수 교수의 강의를 알려줘'
        - '소프트웨어학과 2학년 과목 알려줘'
        - '컴퓨터 관련 강의 찾아줘'
        - '다음 학기 개설 과목 알려줘'
        - '국문학과 관련 강의 검색해줘'
        """