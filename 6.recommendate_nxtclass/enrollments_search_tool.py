import os
import mysql.connector
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class EnrollmentsSearchToolInput(BaseModel):
    """Input schema for EnrollmentsSearchTool."""
    query: str = Field(..., description="이수 과목 검색을 위한 자연어 설명")

class EnrollmentsSearchTool(BaseTool):
    name: str = "enrollments_search_tool"
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
    args_schema: Type[BaseModel] = EnrollmentsSearchToolInput

    def _parse_query_conditions(self, query: str) -> dict:
        """자연어 쿼리에서 조건들을 추출합니다."""
        import re
        
        conditions = {
            'semester': None,
            'grade': None,
            'enrollment_type': None,
            'subject_keyword': None,
            'credits': None
        }
        
        # 학기 추출 (2024-1, 2025-2 등)
        semester_patterns = [
            r'(\d{4})-?([12])학기',
            r'(\d{4})년\s*([12])학기',
            r'([12])학기'
        ]
        for pattern in semester_patterns:
            semester_match = re.search(pattern, query)
            if semester_match:
                if len(semester_match.groups()) == 2:
                    year, sem = semester_match.groups()
                    conditions['semester'] = f"{year}-{sem}"
                else:
                    # 연도 없이 학기만 있는 경우 현재 연도 기준
                    sem = semester_match.group(1)
                    conditions['semester'] = f"2025-{sem}"  # 현재 연도 기준
                break
        
        # 성적 추출 (A+, A, B+, B, C+, C, D+, D, F)
        grade_patterns = [
            r'([ABCDF][+]?)학점',
            r'([ABCDF][+]?)\s*받은',
            r'성적\s*([ABCDF][+]?)',
            r'([ABCDF][+]?)\s*과목'
        ]
        for pattern in grade_patterns:
            grade_match = re.search(pattern, query)
            if grade_match:
                conditions['grade'] = grade_match.group(1)
                break
        
        # 과목 유형 추출
        enrollment_types = {
            '전공필수': 'major_required',
            '전공선택': 'major_elective', 
            '교양필수': 'general_required',
            '교양선택': 'general_elective',
            '교양': 'general',
            '전공': 'major'
        }
        for korean_type, eng_type in enrollment_types.items():
            if korean_type in query:
                conditions['enrollment_type'] = eng_type
                break
        
        # 과목 키워드 추출
        subject_keywords = ['수학', '영어', '물리', '화학', '생물', '역사', '철학', 
                          '경제', '경영', '컴퓨터', '프로그래밍', '국문학', '영문학',
                          '심리학', '사회학', '정치학', '법학', '의학', '공학']
        
        for keyword in subject_keywords:
            if keyword in query:
                conditions['subject_keyword'] = keyword
                break
        
        # 학점 추출 (1학점, 2학점, 3학점 등)
        credits_match = re.search(r'([1-9])학점', query)
        if credits_match:
            conditions['credits'] = int(credits_match.group(1))
        
        return conditions

    def _run(self, query: str) -> str:
        """Execute database query for authenticated student's enrollment information."""
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
            # 테스트를 위해 다인장 학생으로 설정
            authenticated_student = "다인장"
            
            # 먼저 인증된 학생의 student_id 조회
            student_query = "SELECT student_id FROM students WHERE name = %s"
            cursor.execute(student_query, (authenticated_student,))
            student_result = cursor.fetchone()
            
            if not student_result:
                return "인증된 학생 정보를 찾을 수 없습니다."
            
            student_id = student_result['student_id']
            
            # 학생의 이수 과목이 있는지 먼저 확인
            check_query = "SELECT COUNT(DISTINCT course_code) as count FROM enrollments WHERE student_id = %s"
            cursor.execute(check_query, (student_id,))
            count_result = cursor.fetchone()
            
            if not count_result or count_result['count'] == 0:
                return f"학번 {student_id}({authenticated_student}) 학생의 이수 과목 정보가 없습니다."
            
            # 자연어 쿼리 처리 - 개인정보 보호 준수
            if "내가 이수한" in query or "내 이수" in query or "들은 과목" in query:
                # 전체 이수 과목 조회 (중복 제거)
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
                cursor.execute(sql_query, (student_id,))
                results = cursor.fetchall()
                
            elif "학기별" in query or "학기" in query:
                # 조건 파싱
                conditions = self._parse_query_conditions(query)
                
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
                params = [student_id]
                
                if conditions['semester']:
                    sql_query += " AND e.enrollment_semester = %s"
                    params.append(conditions['semester'])
                
                sql_query += " ORDER BY e.enrollment_semester DESC, e.course_code"
                cursor.execute(sql_query, params)
                results = cursor.fetchall()
                
            elif "성적" in query or any(grade in query for grade in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']):
                # 성적별 이수 과목 조회
                conditions = self._parse_query_conditions(query)
                
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
                params = [student_id]
                
                if conditions['grade']:
                    sql_query += " AND e.grade = %s"
                    params.append(conditions['grade'])
                
                sql_query += " ORDER BY e.enrollment_semester DESC, e.grade DESC"
                cursor.execute(sql_query, params)
                results = cursor.fetchall()
                
            elif "통계" in query or "요약" in query:
                # 이수 과목 통계 정보
                sql_query = """
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
                    END) as 평균평점,
                    e.enrollment_type as 이수구분,
                    COUNT(*) as 과목수
                FROM enrollments e
                WHERE e.student_id = %s
                GROUP BY e.enrollment_type
                """
                cursor.execute(sql_query, (student_id,))
                results = cursor.fetchall()
                
            else:
                return """
                개인정보 보호를 위해 본인 인증된 이수 과목만 조회 가능합니다.
                
                사용 가능한 명령어:
                - '내가 이수한 과목 보여주세요' - 전체 이수 과목 목록
                - '2024-1학기에 들은 과목' - 특정 학기 이수 과목
                - 'A학점 받은 과목' - 특정 성적의 이수 과목
                - '전공필수 과목' - 과목 유형별 이수 과목
                - '이수 과목 통계' - 이수 현황 요약 정보
                
                ⚠️ 주의: 이 도구는 조회/열람 전용입니다. 추천 기능은 별도 도구에서 제공됩니다.
                다른 학생의 이수 정보는 개인정보보호법에 따라 조회할 수 없습니다.
                """
            
            if not results:
                return "조회된 이수 과목이 없습니다."
            
            # 전체 결과 개수
            total_count = len(results)
            
            # 표시할 결과 개수 제한 (최대 15개 - 이수 과목은 조금 더 많이 표시)
            display_limit = 15
            display_results = results[:display_limit]
            
            # 결과 포맷팅
            if "통계" in query or "요약" in query:
                # 통계 정보 포맷팅
                formatted_result = "=== 이수 과목 통계 ===\n"
                total_subjects = 0
                total_credits = 0
                
                for row in results:
                    if row.get('총이수과목수'):
                        total_subjects = row['총이수과목수']
                        total_credits = row['총취득학점']
                        avg_gpa = row['평균평점']
                        formatted_result += f"총 이수 과목: {total_subjects}개\n"
                        formatted_result += f"총 취득 학점: {total_credits}학점\n"
                        formatted_result += f"평균 평점: {avg_gpa:.2f}/4.5\n\n"
                        break
                
                formatted_result += "=== 이수구분별 현황 ===\n"
                for i, row in enumerate(results, 1):
                    if row.get('이수구분'):
                        formatted_result += f"{i}. {row['이수구분']}: {row['과목수']}과목\n"
                
                return formatted_result
            else:
                # 일반 이수 과목 목록 포맷팅
                formatted_results = []
                for i, course in enumerate(display_results, 1):
                    course_info = f"{i}. "
                    course_info += f"[{course.get('과목코드', 'N/A')}] {course.get('과목명', 'N/A')}"
                    if course.get('취득학점'):
                        course_info += f" ({course['취득학점']}학점)"
                    if course.get('성적'):
                        course_info += f" - {course['성적']}"
                    if course.get('이수학기'):
                        course_info += f" - {course['이수학기']}"
                    if course.get('이수구분'):
                        course_info += f" - {course['이수구분']}"
                    formatted_results.append(course_info)
                
                # 결과 텍스트 생성
                if total_count > display_limit:
                    result_text = f"총 {total_count}개의 이수 과목이 있습니다. (상위 {display_limit}개 표시)\n\n" + "\n".join(formatted_results)
                else:
                    result_text = f"이수한 과목 ({total_count}개):\n" + "\n".join(formatted_results)
                
                return result_text
            
        except Exception as e:
            return f"데이터베이스 오류: {str(e)}"
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()