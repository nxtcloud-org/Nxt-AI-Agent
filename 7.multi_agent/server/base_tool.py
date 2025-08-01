"""
공통 기능을 제공하는 베이스 도구 클래스
"""
import os
import pymysql
import psycopg2
import psycopg2.extras
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class DatabaseManager:
    """데이터베이스 연결 관리 클래스"""
    
    @staticmethod
    @contextmanager
    def mysql_connection():
        """MySQL 연결 컨텍스트 매니저"""
        connection = None
        try:
            connection = pymysql.connect(
                host=os.environ["RDS_HOST"],
                port=int(os.environ["RDS_PORT"]),
                database=os.environ["RDS_DATABASE"],
                user=os.environ["RDS_USERNAME"],
                password=os.environ["RDS_PASSWORD"],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            yield connection
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    @contextmanager
    def postgres_connection():
        """PostgreSQL 연결 컨텍스트 매니저"""
        connection = None
        try:
            connection = psycopg2.connect(
                host=os.environ.get('RAG_DB_HOST'),
                port=os.environ.get('RAG_DB_PORT', '5432'),
                database=os.environ.get('RAG_DB_NAME'),
                user=os.environ.get('RAG_DB_USER'),
                password=os.environ.get('RAG_DB_PASSWORD')
            )
            yield connection
        finally:
            if connection:
                connection.close()


class QueryValidator:
    """쿼리 검증 클래스"""
    
    SQL_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
        'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET',
        'CREATE', 'DROP', 'ALTER', 'TABLE', 'INDEX',
        'UNION', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN'
    }
    
    @classmethod
    def contains_sql_keywords(cls, query: str) -> bool:
        """SQL 키워드 포함 여부 확인"""
        return any(keyword in query.upper() for keyword in cls.SQL_KEYWORDS)
    
    @classmethod
    def validate_natural_language(cls, query: str) -> Optional[str]:
        """자연어 쿼리 검증"""
        if cls.contains_sql_keywords(query):
            return """
            ❌ SQL 쿼리 직접 작성은 허용되지 않습니다!
            
            올바른 사용법: 자연어로 질문해주세요
            ✅ "컴퓨터 관련 강의 찾아줘"
            ✅ "내 정보 조회해주세요"
            
            잘못된 사용법:
            ❌ "SELECT * FROM ..."
            """
        return None


class ResultFormatter:
    """결과 포맷팅 유틸리티"""
    
    @staticmethod
    def format_course_list(courses: List[Dict], title: str = "조회 결과", limit: int = 10) -> str:
        """강의 목록 포맷팅"""
        if not courses:
            return "조회된 강의가 없습니다."
        
        total_count = len(courses)
        display_courses = courses[:limit]
        
        formatted_results = []
        for i, course in enumerate(display_courses, 1):
            course_info = f"{i}. [{course.get('과목코드', 'N/A')}] {course.get('과목명', 'N/A')}"
            
            if course.get('학점'):
                course_info += f" ({course['학점']}학점)"
            if course.get('개설학과'):
                course_info += f" - {course['개설학과']}"
            if course.get('교수'):
                course_info += f" - {course['교수']} 교수"
            if course.get('대상학년'):
                course_info += f" - {course['대상학년']}학년"
                
            formatted_results.append(course_info)
        
        result = f"{title} ({total_count}개):\n" + "\n".join(formatted_results)
        if total_count > limit:
            result = f"총 {total_count}개 중 상위 {limit}개 표시:\n" + "\n".join(formatted_results)
        
        return result
    
    @staticmethod
    def format_student_info(student_data: Dict) -> str:
        """학생 정보 포맷팅"""
        if not student_data:
            return "조회된 데이터가 없습니다."
        
        result = "=== 조회 결과 ===\n"
        for key, value in student_data.items():
            if value is not None:
                result += f"{key}: {value}\n"
        return result


class BaseTool(ABC):
    """모든 도구의 베이스 클래스"""
    
    def __init__(self):
        self.authenticated_student_id: Optional[str] = None
    
    def set_authenticated_user(self, student_id: str):
        """인증된 사용자 설정"""
        self.authenticated_student_id = student_id
    
    def _validate_authentication(self) -> Optional[str]:
        """인증 검증"""
        if not self.authenticated_student_id:
            return "인증된 사용자 정보가 없습니다. 로그인이 필요합니다."
        return None
    
    @abstractmethod
    def _run(self, query: str) -> str:
        """도구 실행 메서드 (하위 클래스에서 구현)"""
        pass