"""
학생 정보 전문가 에이전트 시스템
"""
import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from typing import List, Dict, Optional

# 도구 import
from tools.student_tool import StudentTool
from tools.enrollment_tool import EnrollmentTool
from semester_utils import SemesterManager

# Load environment variables
load_dotenv()


class StudentAgentSystem:
    """학생 정보 전문가 에이전트 시스템"""
    
    def __init__(self, authenticated_student_id: str = "20230578"):
        self.authenticated_student_id = authenticated_student_id
        self.semester_info = SemesterManager.get_current_semester_info()
        self.llm = self._create_llm()
        self.tools = self._initialize_tools()
        self.agent = self._create_agent()
    
    def _create_llm(self) -> LLM:
        """LLM 인스턴스 생성"""
        model_id = os.environ["BEDROCK_MODEL_ID"]
        return LLM(
            model=f"bedrock/{model_id}",
            temperature=0.2,
            max_tokens=3000
        )
    
    def _initialize_tools(self) -> Dict:
        """도구 초기화"""
        tools = {
            'student': StudentTool(),
            'enrollment': EnrollmentTool()
        }
        
        # 인증된 사용자 정보 설정
        for tool_name in ['student', 'enrollment']:
            tools[tool_name].set_authenticated_user(self.authenticated_student_id)
        
        return tools
    
    def _create_agent(self) -> Agent:
        """학생 정보 전문가 에이전트 생성"""
        return Agent(
            # TODO: 이 부분을 수정해주세요!
            role='',
            goal='',
            backstory='',
            llm='',
            tools=[],
            verbose=True,
            max_iter=3,
            allow_delegation=False
        )
    
    def _get_student_expert_backstory(self) -> str:
        """학생 정보 전문가 배경 스토리"""
        return f'''당신은 학생 데이터베이스 전문가입니다.
        
        📅 현재 날짜 정보:
        - 오늘 날짜: {self.semester_info['current_date']}
        - 현재 학기: {"방학 기간" if not self.semester_info['current_semester'] else f"{self.semester_info['current_semester_year']}년 {self.semester_info['current_semester']}학기"}
        
        주요 역할:
        - 학생의 기본 정보 조회 (학번, 이름, 학과, 입학년도 등)
        - 수강 이력 및 성적 분석
        - 취득 학점 현황 파악
        
        답변 방식:
        - 정확하고 구체적인 데이터 제공
        - 학생 현황을 명확하게 요약
        - 개인정보 보호 준수'''
    
    def process_query(self, question: str) -> str:
        """사용자 질문 처리"""
        print(f"🔍 학생 정보 전문가가 질문을 분석 중: {question}")
        
        # Task 생성
        task = Task(
            description=f"학생 정보를 조회하고 분석해주세요: {question}",
            agent=self.agent,
            expected_output="학생의 기본 정보, 수강 이력, 취득 학점 현황"
        )
        
        # Crew 생성 및 실행
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return result


def main():
    """메인 실행 함수"""
    # 시스템 초기화
    system = StudentAgentSystem()
    
    print("=== 학생 정보 전문가 에이전트 시스템 ===")
    print("기능: 학생 기본 정보 조회, 수강 이력 분석, 성적 현황 파악")
    print(f"현재 학기: {system.semester_info['current_semester_year']}년 {system.semester_info['current_semester']}학기" if system.semester_info['current_semester'] else "현재: 방학 기간")
    print(f"다음 학기: {system.semester_info['next_semester_year']}년 {system.semester_info['next_semester']}학기\n")
    
    # 사용자 입력 받기
    print("학생 정보 관련 질문을 해보세요 (종료하려면 'quit' 입력):")
    print("예시 질문:")
    print("- 내 기본 정보 알려줘")
    print("- 내 수강 이력 분석해줘")
    print("- 내 성적 현황 보여줘")
    print("- 취득 학점 현황 알려줘\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print(f"\n🤖 학생 정보 전문가 처리 중...\n")
                result = system.process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")


if __name__ == "__main__":
    main()