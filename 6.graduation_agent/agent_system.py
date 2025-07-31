"""
졸업 요건 전문가 에이전트 시스템
"""
import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from typing import List, Dict, Optional

# 도구 import
from tools.graduation_tool import GraduationTool
from semester_utils import SemesterManager

# Load environment variables
load_dotenv()


class GraduationAgentSystem:
    """졸업 요건 전문가 에이전트 시스템"""
    
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
            'graduation': GraduationTool()
        }
        return tools
    
    def _create_agent(self) -> Agent:
        """졸업 요건 전문가 에이전트 생성"""
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
    
    def _get_graduation_expert_backstory(self) -> str:
        """졸업 요건 전문가 배경 스토리"""
        return f'''당신은 졸업 요건 전문가입니다.
        
        📅 현재 날짜 정보:
        - 오늘 날짜: {self.semester_info['current_date']}
        - 현재 학기: {"방학 기간" if not self.semester_info['current_semester'] else f"{self.semester_info['current_semester_year']}년 {self.semester_info['current_semester']}학기"}
        
        주요 역할:
        - 학과별 졸업 요건 조회
        - 입학년도별 졸업 요건 차이점 확인
        - 필수 이수 학점 및 과목 정보 제공
        - 졸업 논문/작품 요건 안내
        - 외국어 및 기타 졸업 요건 정보
        
        답변 방식:
        - 졸업 요건을 체계적으로 정리
        - 학과와 입학년도에 맞는 정확한 정보 제공
        - 복잡한 요건도 이해하기 쉽게 설명'''
    
    def process_query(self, question: str) -> str:
        """사용자 질문 처리"""
        print(f"🔍 졸업 요건 전문가가 질문을 분석 중: {question}")
        
        # Task 생성
        task = Task(
            description=f"졸업 요건 정보를 상세히 조회해주세요: {question}",
            agent=self.agent,
            expected_output="학과별, 입학년도별 상세한 졸업 요건 정보"
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
    system = GraduationAgentSystem()
    
    print("=== 졸업 요건 전문가 에이전트 시스템 ===")
    print("기능: 학과별 졸업 요건 조회, 입학년도별 차이점 확인, 필수 이수 학점 정보")
    print(f"현재 학기: {system.semester_info['current_semester_year']}년 {system.semester_info['current_semester']}학기" if system.semester_info['current_semester'] else "현재: 방학 기간")
    print(f"다음 학기: {system.semester_info['next_semester_year']}년 {system.semester_info['next_semester']}학기\n")
    
    # 사용자 입력 받기
    print("졸업 요건 관련 질문을 해보세요 (종료하려면 'quit' 입력):")
    print("예시 질문:")
    print("- 컴퓨터공학과 졸업 요건 알려줘")
    print("- 2020년 입학 영상디자인학과 졸업 요건")
    print("- 내 전공 졸업에 필요한 학점")
    print("- 졸업 논문 요건 알려줘\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print(f"\n🤖 졸업 요건 전문가 처리 중...\n")
                result = system.process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")


if __name__ == "__main__":
    main()