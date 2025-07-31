"""
자연어 쿼리 파싱 유틸리티
"""
import re
from typing import Dict, List, Optional, Union


class QueryParser:
    """자연어 쿼리 파싱 클래스"""
    
    # 동의어 매핑
    SYNONYM_MAPPING = {
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
    
    # 과목 키워드
    SUBJECT_KEYWORDS = [
        '심리학', '심리', '수학', '영어', '물리학', '화학', '생물학', 
        '역사', '철학', '경제학', '경영학', '컴퓨터', '프로그래밍',
        '데이터', '인공지능', 'AI', '머신러닝', '통계', '국문학', '국문',
        '영문학', '영문', '중문학', '중문'
    ]
    
    # 과목 유형 매핑
    ENROLLMENT_TYPES = {
        '전공필수': 'major_required',
        '전공선택': 'major_elective', 
        '교양필수': 'general_required',
        '교양선택': 'general_elective',
        '교양': 'general',
        '전공': 'major'
    }
    
    @classmethod
    def parse_course_conditions(cls, query: str) -> Dict:
        """강의 검색 조건 파싱"""
        conditions = {
            'grade': None,
            'department': None,
            'subject_keyword': None,
            'professor': None,
            'course_type': None
        }
        
        # 학년 추출
        grade_match = re.search(r'([1-4])학년', query)
        if grade_match:
            conditions['grade'] = grade_match.group(1)
        
        # 학과명 추출 및 동의어 매핑
        dept_patterns = [r'(\w+학과)', r'(\w+과)(?!목)', r'(\w+)학과', r'(\w+)과(?!목)']
        for pattern in dept_patterns:
            dept_match = re.search(pattern, query)
            if dept_match:
                dept_name = dept_match.group(1)
                if dept_name not in ['과목', '학과', '전공', '강의']:
                    conditions['department'] = cls._apply_synonym_mapping(dept_name)
                    break
        
        # 과목 키워드 추출
        for keyword in cls.SUBJECT_KEYWORDS:
            if keyword in query:
                conditions['subject_keyword'] = cls._apply_synonym_mapping(keyword)
                break
        
        # 교수명 추출
        prof_match = re.search(r'(\w+)\s*교수', query)
        if prof_match:
            conditions['professor'] = prof_match.group(1)
        
        return conditions
    
    @classmethod
    def parse_enrollment_conditions(cls, query: str) -> Dict:
        """수강 이력 검색 조건 파싱"""
        conditions = {
            'semester': None,
            'grade': None,
            'enrollment_type': None,
            'subject_keyword': None,
            'credits': None
        }
        
        # 학기 추출
        semester_patterns = [
            r'(\d{4})-?([12])학기',
            r'(\d{4})년\s*([12])학기',
            r'([12])학기'
        ]
        for pattern in semester_patterns:
            semester_match = re.search(pattern, query)
            if semester_match:
                groups = semester_match.groups()
                if len(groups) == 2:
                    year, sem = groups
                    conditions['semester'] = f"{year}-{sem}"
                else:
                    sem = groups[0]
                    conditions['semester'] = f"2025-{sem}"
                break
        
        # 성적 추출
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
        for korean_type, eng_type in cls.ENROLLMENT_TYPES.items():
            if korean_type in query:
                conditions['enrollment_type'] = eng_type
                break
        
        # 과목 키워드 추출
        for keyword in cls.SUBJECT_KEYWORDS:
            if keyword in query:
                conditions['subject_keyword'] = keyword
                break
        
        # 학점 추출
        credits_match = re.search(r'([1-9])학점', query)
        if credits_match:
            conditions['credits'] = int(credits_match.group(1))
        
        return conditions
    
    @classmethod
    def _apply_synonym_mapping(cls, keyword: str) -> Union[List[str], str]:
        """동의어 매핑 적용"""
        for key, synonyms in cls.SYNONYM_MAPPING.items():
            if keyword in synonyms:
                return synonyms
        return keyword