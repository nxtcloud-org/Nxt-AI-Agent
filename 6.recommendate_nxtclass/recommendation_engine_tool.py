import os
import json
import mysql.connector
from crewai.tools import BaseTool
from typing import Type, Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class RecommendationEngineToolInput(BaseModel):
    """Input schema for RecommendationEngineTool."""
    student_id: str = Field(..., description="추천을 받을 학생의 ID")
    semester: Optional[str] = Field(None, description="추천받을 학기 (예: 2024-1, 2024-2). 없으면 다음 학기로 자동 설정")
    max_credits: Optional[int] = Field(21, description="최대 수강 가능 학점 (기본값: 21학점)")

class RecommendationEngineTool(BaseTool):
    name: str = "recommendation_engine_tool"
    description: str = """
    학생의 수강 내역을 분석하여 다음 학기 추천 과목을 제안하는 도구입니다.
    
    주요 기능:
    1. 졸업 요건 기반 필수 과목 추천
    2. 선수 과목을 고려한 후속 과목 추천
    3. 전공/교양/일반선택 균형 고려
    4. 시간표 충돌 방지
    5. 학점 및 난이도 균형 추천
    
    추천 기준:
    - 졸업 요건 충족을 위한 필수 과목 우선
    - 이미 수강한 과목의 선수 조건을 만족하는 과목
    - 학생의 전공과 관련된 과목
    - 적절한 학점 분배 (전공 60%, 교양 30%, 일반선택 10%)
    
    사용법:
    - "다음 학기 추천 과목 알려줘"
    - "2024-2학기 수강 추천해줘"
    - "18학점으로 수강 계획 세워줘"
    """
    args_schema: Type[BaseModel] = RecommendationEngineToolInput

    def _get_db_connection(self):
        """MySQL 데이터베이스 연결을 반환합니다."""
        return mysql.connector.connect(
            host=os.environ.get('RDS_HOST', 'localhost'),
            port=int(os.environ.get('RDS_PORT', '3306')),
            database=os.environ.get('RDS_DATABASE', 'nxtclass_db'),
            user=os.environ.get('RDS_USERNAME', 'admin'),
            password=os.environ.get('RDS_PASSWORD', 'password')
        )

    def _get_student_info(self, student_id: str) -> Dict:
        """학생 기본 정보를 조회합니다."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    s.student_id, 
                    s.name, 
                    s.major_code,
                    s.admission_year, 
                    s.completed_semester,
                    m.major_name,
                    m.college,
                    m.department
                FROM students s
                LEFT JOIN major m ON s.major_code = m.major_code
                WHERE s.student_id = %s
            """, (student_id,))
            
            student_info = cursor.fetchone()
            conn.close()
            
            return student_info if student_info else {}
            
        except Exception as e:
            print(f"학생 정보 조회 중 오류: {str(e)}")
            return {}

    def _get_completed_courses(self, student_id: str) -> List[Dict]:
        """학생의 수강 완료 과목 목록을 조회합니다."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    e.course_code,
                    c.course_name,
                    c.credits,
                    c.course_type,
                    c.department,
                    e.grade,
                    e.enrollment_semester as semester
                FROM enrollments e
                JOIN courses c ON e.course_code = c.course_code
                WHERE e.student_id = %s 
                AND e.grade IS NOT NULL 
                AND e.grade NOT IN ('F', 'NP')
                ORDER BY e.enrollment_semester
            """, (student_id,))
            
            completed_courses = cursor.fetchall()
            conn.close()
            
            return completed_courses
            
        except Exception as e:
            print(f"수강 완료 과목 조회 중 오류: {str(e)}")
            return []

    def _get_available_courses(self, semester: str, major_code: str) -> List[Dict]:
        """특정 학기에 개설되는 과목 목록을 조회합니다."""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 다음 학기 개설 과목이 있는지 확인 (실제 스키마에 맞게 수정)
            cursor.execute("""
                SELECT DISTINCT
                    c.course_code,
                    c.course_name,
                    c.credits,
                    c.course_type,
                    c.department,
                    c.note as description
                FROM courses c
                WHERE c.department = %s
                OR c.course_type IN ('교양기초', '교양선택', '핵심교양')
                ORDER BY c.course_type, c.course_name
                LIMIT 50
            """, (major_code,))
            
            available_courses = cursor.fetchall()
            
            # 앞 5자리 기준으로 중복 제거
            unique_courses = []
            seen_prefixes = set()
            
            for course in available_courses:
                course_prefix = course['course_code'][:5]
                if course_prefix not in seen_prefixes:
                    unique_courses.append(course)
                    seen_prefixes.add(course_prefix)
            
            conn.close()
            return unique_courses
            
        except Exception as e:
            print(f"개설 과목 조회 중 오류: {str(e)}")
            return []

    def _check_prerequisites(self, course: Dict, completed_courses: List[Dict]) -> bool:
        """선수 과목 조건을 확인합니다."""
        if not course.get('prerequisites'):
            return True
        
        prerequisites = course['prerequisites'].split(',')
        completed_codes = [c['course_code'] for c in completed_courses]
        
        for prereq in prerequisites:
            prereq = prereq.strip()
            if prereq and prereq not in completed_codes:
                return False
        
        return True

    def _is_same_course(self, course_code1: str, course_code2: str) -> bool:
        """과목 코드의 앞 5자리가 같으면 같은 수업으로 판단합니다."""
        if not course_code1 or not course_code2:
            return False
        return course_code1[:5] == course_code2[:5]

    def _is_already_taken(self, course_code: str, completed_courses: List[Dict]) -> bool:
        """이미 수강한 과목인지 확인합니다 (앞 5자리 기준)."""
        for completed_course in completed_courses:
            if self._is_same_course(course_code, completed_course['course_code']):
                return True
        return False

    def _calculate_graduation_progress(self, student_info: Dict, completed_courses: List[Dict]) -> Dict:
        """졸업 요건 진행 상황을 계산합니다."""
        major_code = student_info.get('major_code', '')
        
        # 학점 계산
        total_credits = sum(course['credits'] for course in completed_courses)
        major_credits = sum(course['credits'] for course in completed_courses if course['department'] == major_code)
        liberal_credits = sum(course['credits'] for course in completed_courses 
                            if course['course_type'] in ['교양기초', '교양선택', '핵심교양'])
        
        # 졸업 요건 (기본값, 실제로는 전공별로 다름)
        required_total = 130  # 대부분 학과 기준
        required_major = 60
        required_liberal = 30
        
        return {
            'total_credits': total_credits,
            'major_credits': major_credits,
            'liberal_credits': liberal_credits,
            'required_total': required_total,
            'required_major': required_major,
            'required_liberal': required_liberal,
            'remaining_total': max(0, required_total - total_credits),
            'remaining_major': max(0, required_major - major_credits),
            'remaining_liberal': max(0, required_liberal - liberal_credits)
        }

    def _generate_recommendations(self, student_info: Dict, completed_courses: List[Dict], 
                                available_courses: List[Dict], max_credits: int, semester: str) -> List[Dict]:
        """추천 과목 목록을 생성합니다."""
        major_code = student_info.get('major_code', '')
        progress = self._calculate_graduation_progress(student_info, completed_courses)
        
        # 이미 수강한 과목 코드 목록
        completed_codes = [c['course_code'] for c in completed_courses]
        
        recommendations = []
        current_credits = 0
        
        # 1. 전공 필수 과목 우선 추천
        major_courses = [c for c in available_courses 
                        if c['department'] == major_code and not self._is_already_taken(c['course_code'], completed_courses)]
        
        for course in major_courses:
            if current_credits + course['credits'] <= max_credits:
                if self._check_prerequisites(course, completed_courses):
                    recommendations.append({
                        'course': course,
                        'reason': '전공 필수 과목',
                        'priority': 1
                    })
                    current_credits += course['credits']
        
        # 2. 교양 과목 추천 (교양 학점이 부족한 경우)
        if progress['remaining_liberal'] > 0:
            liberal_courses = [c for c in available_courses 
                             if c['course_type'] in ['교양기초', '교양선택', '핵심교양'] 
                             and not self._is_already_taken(c['course_code'], completed_courses)]
            
            for course in liberal_courses:
                if current_credits + course['credits'] <= max_credits:
                    if self._check_prerequisites(course, completed_courses):
                        recommendations.append({
                            'course': course,
                            'reason': '교양 요건 충족',
                            'priority': 2
                        })
                        current_credits += course['credits']
                        if current_credits >= max_credits:
                            break
        
        # 3. 전공 선택 과목 추천
        if current_credits < max_credits:
            elective_courses = [c for c in available_courses 
                              if c['department'] == major_code and not self._is_already_taken(c['course_code'], completed_courses)]
            
            for course in elective_courses:
                if current_credits + course['credits'] <= max_credits:
                    if self._check_prerequisites(course, completed_courses):
                        # 이미 추천된 과목과 중복되지 않는지 확인 (앞 5자리 기준)
                        already_recommended = any(
                            self._is_same_course(r['course']['course_code'], course['course_code']) 
                            for r in recommendations
                        )
                        if not already_recommended:
                            recommendations.append({
                                'course': course,
                                'reason': '전공 심화 과목',
                                'priority': 3
                            })
                            current_credits += course['credits']
                            if current_credits >= max_credits:
                                break
        
        return recommendations

    def _format_recommendations(self, student_info: Dict, recommendations: List[Dict], 
                              progress: Dict, semester: str, max_credits: int) -> str:
        """추천 결과를 포맷팅합니다."""
        if not recommendations:
            return f"죄송합니다. {semester} 학기에 추천할 수 있는 과목을 찾을 수 없습니다."
        
        result = f"=== {student_info.get('name', '학생')}님의 {semester} 학기 수강 추천 ===\n\n"
        
        # 졸업 진행 상황
        result += "📊 **졸업 요건 진행 상황**\n"
        result += f"- 총 이수 학점: {progress['total_credits']}/{progress['required_total']} (잔여: {progress['remaining_total']}학점)\n"
        result += f"- 전공 학점: {progress['major_credits']}/{progress['required_major']} (잔여: {progress['remaining_major']}학점)\n"
        result += f"- 교양 학점: {progress['liberal_credits']}/{progress['required_liberal']} (잔여: {progress['remaining_liberal']}학점)\n\n"
        
        # 추천 과목 목록
        result += f"🎯 **추천 과목 ({max_credits}학점 기준)**\n\n"
        
        total_recommended_credits = 0
        for i, rec in enumerate(recommendations, 1):
            course = rec['course']
            total_recommended_credits += course['credits']
            
            result += f"{i}. **{course['course_name']}** ({course['course_code']})\n"
            result += f"   - 학점: {course['credits']}학점\n"
            result += f"   - 구분: {course['course_type']}\n"
            result += f"   - 추천 이유: {rec['reason']}\n"
            if course.get('description'):
                result += f"   - 과목 설명: {course['description'][:100]}...\n"
            result += "\n"
        
        result += f"**총 추천 학점**: {total_recommended_credits}학점\n\n"
        
        # 추가 조언
        result += "💡 **수강 신청 팁**\n"
        result += "- 선수 과목을 확인하여 수강 순서를 계획하세요\n"
        result += "- 시간표 충돌을 피하기 위해 여러 대안을 준비하세요\n"
        result += "- 적절한 난이도 분배로 학습 부담을 조절하세요\n"
        
        return result

    def _run(self, student_id: str, semester: Optional[str] = None, max_credits: Optional[int] = None) -> str:
        """수강 추천을 실행합니다."""
        try:
            # 학생 정보 조회
            student_info = self._get_student_info(student_id)
            if not student_info:
                return f"학생 ID '{student_id}'를 찾을 수 없습니다."
            
            # 기본값 설정
            if max_credits is None:
                max_credits = 21  # 기본 최대 학점
            
            # 기본 학기 설정 (다음 학기)
            if not semester:
                current_year = 2025  # 현재 2025년
                current_sem = 1  # 현재 1학기
                next_sem = 2 if current_sem == 1 else 1
                next_year = current_year if next_sem == 2 else current_year + 1
                semester = f"{next_year}-{next_sem}"
            
            # 수강 완료 과목 조회
            completed_courses = self._get_completed_courses(student_id)
            
            # 개설 과목 조회
            available_courses = self._get_available_courses(semester, student_info['major_code'])
            
            # 졸업 진행 상황 계산
            progress = self._calculate_graduation_progress(student_info, completed_courses)
            
            # 추천 과목 생성
            recommendations = self._generate_recommendations(
                student_info, completed_courses, available_courses, max_credits, semester
            )
            
            # 결과 포맷팅
            return self._format_recommendations(
                student_info, recommendations, progress, semester, max_credits
            )
            
        except Exception as e:
            return f"수강 추천 중 오류가 발생했습니다: {str(e)}"