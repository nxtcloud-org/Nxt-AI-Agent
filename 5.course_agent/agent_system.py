"""
강의 정보 전문가 에이전트 시스템
"""
import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from typing import List, Dict, Optional

# 도구 import
from tools.course_tool import CourseTool
from semester_utils import SemesterManager

# Load environment variables
load_dotenv()


class CourseAgentSystem:
    """강의 정보 전문가 에이전트 시스템"""
    
    def __init__(self):
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
            'course': CourseTool()
        }
        return tools
    
    def _create_agent(self) -> Agent:
        """강의 정보 전문가 에이전트 생성"""
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
    
    def _get_course_expert_backstory(self) -> str:
        """강의 정보 전문가 배경 스토리"""
        return f'''당신은 강의 정보 전문가입니다.
        
        📅 현재 날짜 정보:
        - 오늘 날짜: {self.semester_info['current_date']}
        - 현재 학기: {"방학 기간" if not self.semester_info['current_semester'] else f"{self.semester_info['current_semester_year']}년 {self.semester_info['current_semester']}학기"}
        - 다음 학기: {self.semester_info['next_semester_year']}년 {self.semester_info['next_semester']}학기
        
        주요 역할:
        - 강의 정보 검색 및 조회
        - 강의 시간표 및 교수 정보 제공
        - 선수과목 관계 분석
        - 다음 학기 수업이 미리 등록되지 않을 경우 절대 조회할 수 없다는 답변을 내려야 함
        - 조회된 정보와 다르게 출력할 수 없으며, 없는 정보를 창작할 수 없음
        
        답변 방식:
        - 도구의 출력을 그대로 전달
        - 필요시 간단한 설명 추가
        - 명확하고 직접적인 정보 제공'''
    
    def process_query(self, question: str) -> str:
        """사용자 질문 처리"""
        print(f"🔍 강의 정보 전문가가 질문을 분석 중: {question}")
        
        # Task 생성
        task = Task(
            description=f"강의 정보를 검색해주세요: {question}",
            agent=self.agent,
            expected_output="강의 정보 및 세부사항"
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
    system = CourseAgentSystem()
    
    print("=== 강의 정보 전문가 에이전트 시스템 ===")
    print("기능: 강의 정보 검색, 시간표 조회, 교수 정보 제공")
    print(f"현재 학기: {system.semester_info['current_semester_year']}년 {system.semester_info['current_semester']}학기" if system.semester_info['current_semester'] else "현재: 방학 기간")
    print(f"다음 학기: {system.semester_info['next_semester_year']}년 {system.semester_info['next_semester']}학기\n")
    
    # 사용자 입력 받기
    print("강의 정보 관련 질문을 해보세요 (종료하려면 'quit' 입력):")
    print("예시 질문:")
    print("- 컴퓨터 관련 강의 찾아줘")
    print("- 다음 학기 개설 과목 알려줘")
    print("- 김철수 교수 강의 검색해줘")
    print("- 3학년 수강 가능한 강의 알려줘\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print(f"\n🤖 강의 정보 전문가 처리 중...\n")
                result = system.process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")


if __name__ == "__main__":
    main()