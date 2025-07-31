"""
학기 관련 유틸리티 함수들
"""
from datetime import datetime
from typing import Dict, Optional


class SemesterManager:
    """학기 정보 관리 클래스"""
    
    @staticmethod
    def get_current_semester_info() -> Dict:
        """현재 날짜 기준 학기 정보 반환"""
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_day = now.day
        
        # 학기 구분 로직
        semester_info = {
            'current_date': now.strftime('%Y년 %m월 %d일'),
            'current_semester': None,
            'current_semester_year': None,
            'next_semester': None,
            'next_semester_year': None,
            'prev_semester': None,
            'prev_semester_year': None
        }
        
        # 1학기: 3월 ~ 6월 20일
        if (current_month == 3) or (current_month == 4) or (current_month == 5) or (current_month == 6 and current_day <= 20):
            semester_info.update({
                'current_semester': 1,
                'current_semester_year': current_year,
                'next_semester': 2,
                'next_semester_year': current_year,
                'prev_semester': 2,
                'prev_semester_year': current_year - 1
            })
        
        # 2학기: 9월 ~ 12월 20일
        elif (current_month == 9) or (current_month == 10) or (current_month == 11) or (current_month == 12 and current_day <= 20):
            semester_info.update({
                'current_semester': 2,
                'current_semester_year': current_year,
                'next_semester': 1,
                'next_semester_year': current_year + 1,
                'prev_semester': 1,
                'prev_semester_year': current_year
            })
        
        # 방학 기간
        else:
            if current_month in [1, 2]:  # 겨울방학
                semester_info.update({
                    'next_semester': 1,
                    'next_semester_year': current_year,
                    'prev_semester': 2,
                    'prev_semester_year': current_year - 1
                })
            else:  # 여름방학 또는 12월 말
                next_year = current_year + 1 if current_month == 12 else current_year
                semester_info.update({
                    'next_semester': 2 if current_month <= 8 else 1,
                    'next_semester_year': next_year if current_month == 12 else current_year,
                    'prev_semester': 1 if current_month <= 8 else 2,
                    'prev_semester_year': current_year
                })
        
        return semester_info
    
    @staticmethod
    def format_semester_context(semester_info: Dict, semester_type: str) -> str:
        """학기 컨텍스트 포맷팅"""
        context = f"\n📅 현재 날짜: {semester_info['current_date']}\n"
        
        if semester_type == "next":
            context += f"📚 다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기\n\n"
        elif semester_type == "prev":
            context += f"📚 지난 학기: {semester_info['prev_semester_year']}년 {semester_info['prev_semester']}학기\n\n"
        elif semester_type == "current":
            if semester_info['current_semester']:
                context += f"📚 현재 학기: {semester_info['current_semester_year']}년 {semester_info['current_semester']}학기\n\n"
            else:
                context += "현재는 방학 기간입니다.\n"
                context += f"📚 다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기\n"
                context += f"📚 지난 학기: {semester_info['prev_semester_year']}년 {semester_info['prev_semester']}학기\n\n"
        
        return context