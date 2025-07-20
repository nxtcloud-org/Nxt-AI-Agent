import os
import mysql.connector
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from datetime import datetime

def get_current_semester_info():
    """현재 날짜를 기준으로 학기 정보를 반환합니다."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    current_day = now.day
    
    # 1학기: 3월 ~ 6월 20일
    # 2학기: 9월 ~ 12월 20일
    
    if (current_month == 3) or (current_month == 4) or (current_month == 5) or (current_month == 6 and current_day <= 20):
        # 현재 1학기
        current_semester = 1
        current_semester_year = current_year
        next_semester = 2
        next_semester_year = current_year
        prev_semester = 2
        prev_semester_year = current_year - 1
        
    elif (current_month == 9) or (current_month == 10) or (current_month == 11) or (current_month == 12 and current_day <= 20):
        # 현재 2학기
        current_semester = 2
        current_semester_year = current_year
        next_semester = 1
        next_semester_year = current_year + 1
        prev_semester = 1
        prev_semester_year = current_year
        
    elif current_month in [1, 2] or (current_month == 6 and current_day > 20) or current_month in [7, 8]:
        # 방학 기간
        if current_month in [1, 2] or (current_month == 6 and current_day > 20) or current_month in [7, 8]:
            if current_month in [1, 2]:
                # 겨울방학 (1-2월)
                current_semester = None
                next_semester = 1
                next_semester_year = current_year
                prev_semester = 2
                prev_semester_year = current_year - 1
            else:
                # 여름방학 (6월 21일 이후 ~ 8월)
                current_semester = None
                next_semester = 2
                next_semester_year = current_year
                prev_semester = 1
                prev_semester_year = current_year
    else:
        # 12월 21일 이후
        current_semester = None
        next_semester = 1
        next_semester_year = current_year + 1
        prev_semester = 2
        prev_semester_year = current_year
    
    return {
        'current_date': now.strftime('%Y년 %m월 %d일'),
        'current_semester': current_semester,
        'current_semester_year': current_semester_year if current_semester else None,
        'next_semester': next_semester,
        'next_semester_year': next_semester_year,
        'prev_semester': prev_semester,
        'prev_semester_year': prev_semester_year
    }

class CourseSearchToolInput(BaseModel):
    """Input schema for CourseSearchTool."""
    query: str = Field(..., description="강의 검색을 위한 SQL 쿼리 또는 자연어 설명")

class CourseSearchTool(BaseTool):
    name: str = "course_search_tool"
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
    args_schema: Type[BaseModel] = CourseSearchToolInput

    def _parse_query_conditions(self, query: str) -> dict:
        """자연어 쿼리에서 조건들을 추출합니다."""
        import re
        
        conditions = {
            'grade': None,
            'department': None,
            'subject_keyword': None,
            'professor': None,
            'course_type': None
        }
        
        # 동의어/유사어 매핑
        synonym_mapping = {
            '국문학': ['국문학', '한국어문학', '한국문학', '국어국문학'],
            '국문': ['국문', '한국어문', '한국문', '국어국문'],
            '영문학': ['영문학', '영어영문학', '영어문학'],
            '영문': ['영문', '영어영문', '영어'],
            '중문학': ['중문학', '중국학', '중국어문'],
            '중문': ['중문', '중국', '중국어'],
            '심리학': ['심리학', '심리'],
            '경영학': ['경영학', '경영', '기업경영'],
            '컴퓨터': ['컴퓨터', '소프트웨어', 'SW', 'IT', '인공지능', 'AI'],
            '수학': ['수학', '응용수학', '통계'],
            '물리': ['물리', '물리학', '응용물리'],
            '화학': ['화학', '응용화학', '생화학'],
            '역사': ['역사', '한국역사', '세계사'],
            '미술': ['미술', '회화', '조형', '디자인'],
            '음악': ['음악', '성악', '피아노', '관현악'],
            '체육': ['체육', '스포츠', '운동']
        }
        
        # 학년 추출 (1학년, 2학년, 3학년, 4학년)
        grade_match = re.search(r'([1-4])학년', query)
        if grade_match:
            conditions['grade'] = grade_match.group(1)
        
        # 학과명 추출 (~~학과, ~~과) - 동의어 매핑 적용
        dept_patterns = [
            r'(\w+학과)',
            r'(\w+과)(?!목)',  # '과목'의 '과'는 제외
            r'(\w+)학과',
            r'(\w+)과(?!목)'
        ]
        for pattern in dept_patterns:
            dept_match = re.search(pattern, query)
            if dept_match:
                dept_name = dept_match.group(1)
                # 일반적인 단어들 제외
                if dept_name not in ['과목', '학과', '전공', '강의']:
                    # 동의어 매핑 적용
                    mapped_keywords = []
                    for key, synonyms in synonym_mapping.items():
                        if dept_name in synonyms:
                            mapped_keywords.extend(synonyms)
                            break
                    
                    conditions['department'] = mapped_keywords if mapped_keywords else [dept_name]
                    break
        
        # 과목 키워드 추출 - 동의어 매핑 적용
        subject_keywords = ['심리학', '심리', '수학', '영어', '물리학', '화학', '생물학', 
                          '역사', '철학', '경제학', '경영학', '컴퓨터', '프로그래밍',
                          '데이터', '인공지능', 'AI', '머신러닝', '통계', '국문학', '국문',
                          '영문학', '영문', '중문학', '중문']
        
        for keyword in subject_keywords:
            if keyword in query:
                # 동의어 매핑 적용
                mapped_keywords = []
                for key, synonyms in synonym_mapping.items():
                    if keyword in synonyms:
                        mapped_keywords.extend(synonyms)
                        break
                
                conditions['subject_keyword'] = mapped_keywords if mapped_keywords else [keyword]
                break
        
        # 교수명 추출 (교수 앞의 이름)
        prof_match = re.search(r'(\w+)\s*교수', query)
        if prof_match:
            conditions['professor'] = prof_match.group(1)
        
        return conditions
    
    def _build_sql_query(self, conditions: dict) -> tuple:
        """조건들을 바탕으로 SQL 쿼리를 동적으로 생성합니다."""
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
            c.target_grade as 대상학년,
            c.note as 비고
        FROM courses c
        LEFT JOIN major m ON c.department = m.major_code
        WHERE 1=1
        """
        
        params = []
        
        # 학년 조건
        if conditions['grade']:
            base_query += " AND (c.target_grade = %s OR c.target_grade LIKE %s OR c.target_grade = '전체')"
            params.extend([conditions['grade'], f"%{conditions['grade']}%"])
        
        # 학과 조건 - major 테이블의 정보도 검색 (동의어 지원)
        if conditions['department']:
            dept_keywords = conditions['department'] if isinstance(conditions['department'], list) else [conditions['department']]
            dept_conditions = []
            for keyword in dept_keywords:
                dept_conditions.extend([
                    "m.department LIKE %s",
                    "m.major_name LIKE %s", 
                    "m.college LIKE %s"
                ])
                keyword_pattern = f"%{keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            base_query += f" AND ({' OR '.join(dept_conditions)})"
        
        # 과목 키워드 조건 - major 테이블의 정보도 검색 (동의어 지원)
        if conditions['subject_keyword']:
            subject_keywords = conditions['subject_keyword'] if isinstance(conditions['subject_keyword'], list) else [conditions['subject_keyword']]
            subject_conditions = []
            for keyword in subject_keywords:
                subject_conditions.extend([
                    "c.course_name LIKE %s",
                    "m.department LIKE %s",
                    "m.major_name LIKE %s"
                ])
                keyword_pattern = f"%{keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            base_query += f" AND ({' OR '.join(subject_conditions)})"
        
        # 교수 조건
        if conditions['professor']:
            base_query += " AND c.professor LIKE %s"
            params.append(f"%{conditions['professor']}%")
        
        base_query += " ORDER BY m.college, m.department, c.course_name"
        
        return base_query, params

    def _run(self, query: str) -> str:
        """Execute database query to get course information."""
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
            
            # 현재 날짜 기반 학기 정보 가져오기
            semester_info = get_current_semester_info()
            
            # 특별한 케이스들 먼저 처리
            if "다음 학기" in query or "다음학기" in query:
                # 다음 학기 정보를 쿼리에 포함 (major 테이블과 조인)
                next_semester = semester_info['next_semester']
                next_year = semester_info['next_semester_year']
                
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
                    c.target_grade as 대상학년,
                    c.offered_year as 개설년도,
                    c.offered_semester as 개설학기
                FROM courses c
                LEFT JOIN major m ON c.department = m.major_code
                WHERE c.offered_year = %s AND c.offered_semester = %s
                ORDER BY m.college, m.department, c.course_name
                """
                cursor.execute(sql_query, (next_year, next_semester))
                results = cursor.fetchall()
                
                # 결과에 학기 정보 추가
                semester_context = f"\n📅 현재 날짜: {semester_info['current_date']}\n📚 다음 학기: {next_year}년 {next_semester}학기\n\n"
                
            elif "지난 학기" in query or "이전 학기" in query:
                # 지난 학기 정보를 쿼리에 포함 (major 테이블과 조인)
                prev_semester = semester_info['prev_semester']
                prev_year = semester_info['prev_semester_year']
                
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
                    c.target_grade as 대상학년,
                    c.offered_year as 개설년도,
                    c.offered_semester as 개설학기
                FROM courses c
                LEFT JOIN major m ON c.department = m.major_code
                WHERE c.offered_year = %s AND c.offered_semester = %s
                ORDER BY m.college, m.department, c.course_name
                """
                cursor.execute(sql_query, (prev_year, prev_semester))
                results = cursor.fetchall()
                
                # 결과에 학기 정보 추가
                semester_context = f"\n📅 현재 날짜: {semester_info['current_date']}\n📚 지난 학기: {prev_year}년 {prev_semester}학기\n\n"
                
            elif "이번 학기" in query or "현재 학기" in query:
                # 현재 학기 정보를 쿼리에 포함 (major 테이블과 조인)
                if semester_info['current_semester']:
                    current_semester = semester_info['current_semester']
                    current_year = semester_info['current_semester_year']
                    
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
                        c.target_grade as 대상학년,
                        c.offered_year as 개설년도,
                        c.offered_semester as 개설학기
                    FROM courses c
                    LEFT JOIN major m ON c.department = m.major_code
                    WHERE c.offered_year = %s AND c.offered_semester = %s
                    ORDER BY m.college, m.department, c.course_name
                    """
                    cursor.execute(sql_query, (current_year, current_semester))
                    results = cursor.fetchall()
                    
                    semester_context = f"\n📅 현재 날짜: {semester_info['current_date']}\n📚 현재 학기: {current_year}년 {current_semester}학기\n\n"
                else:
                    return f"""
                    📅 현재 날짜: {semester_info['current_date']}
                    현재는 방학 기간입니다.
                    
                    📚 다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기
                    📚 지난 학기: {semester_info['prev_semester_year']}년 {semester_info['prev_semester']}학기
                    
                    "다음 학기" 또는 "지난 학기" 강의를 검색해보세요.
                    """
                    
            elif "전체" in query or "모든" in query:
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
                semester_context = f"\n📅 현재 날짜: {semester_info['current_date']}\n\n"
                
            elif query.strip().upper().startswith("SELECT"):
                # 직접 SQL 쿼리
                if "courses" in query.lower():
                    cursor.execute(query)
                    results = cursor.fetchall()
                else:
                    return "courses 테이블만 사용할 수 있습니다."
                    
            else:
                # 자연어 쿼리 파싱 및 동적 SQL 생성
                conditions = self._parse_query_conditions(query)
                
                # 조건이 하나도 없으면 안내 메시지
                if not any(conditions.values()):
                    return """
                    강의 검색 예시:
                    - '3학년 과목 중 한국역사학과 개설 강의 알려줘'
                    - '심리학 관련 강의 검색해줘'
                    - '김철수 교수의 강의를 알려줘'
                    - '소프트웨어학과 2학년 과목 알려줘'
                    - '컴퓨터 관련 강의 찾아줘'
                    - '다음 학기 개설 과목 알려줘'
                    - '국문학과 관련 강의 검색해줘'
                    
                    ⚠️ 주의: 이 도구는 조회/검색 전용입니다. 추천 기능은 별도 도구에서 제공됩니다.
                    """
                
                sql_query, params = self._build_sql_query(conditions)
                cursor.execute(sql_query, params)
                results = cursor.fetchall()
            
            if not results:
                return "조회된 강의가 없습니다."
            
            # 전체 결과 개수
            total_count = len(results)
            
            # 표시할 결과 개수 제한 (최대 10개)
            display_limit = 10
            display_results = results[:display_limit]
            
            # 결과 포맷팅
            formatted_results = []
            for i, course in enumerate(display_results, 1):
                course_info = f"{i}. "
                course_info += f"[{course.get('과목코드', 'N/A')}] {course.get('과목명', 'N/A')}"
                if course.get('학점'):
                    course_info += f" ({course['학점']}학점)"
                if course.get('개설학과'):
                    course_info += f" - {course['개설학과']}"
                if course.get('교수'):
                    course_info += f" - {course['교수']} 교수"
                if course.get('대상학년'):
                    course_info += f" - {course['대상학년']}학년"
                formatted_results.append(course_info)
            
            # 결과 텍스트 생성
            if total_count > display_limit:
                result_text = f"총 {total_count}개의 강의가 개설되었습니다. (상위 {display_limit}개 표시)\n\n" + "\n".join(formatted_results)
            else:
                result_text = f"조회된 강의 ({total_count}개):\n" + "\n".join(formatted_results)
            
            # 학기 정보가 있으면 포함해서 반환
            if 'semester_context' in locals():
                result_text = semester_context + result_text
            
            return result_text
            
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()