"""
리팩토링된 멀티 에이전트 시스템
"""
import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from typing import List, Dict, Optional
from enum import Enum

# 도구 import
from tools.student_tool import StudentTool
from tools.course_tool import CourseTool
from tools.enrollment_tool import EnrollmentTool
from tools.graduation_tool import GraduationTool
from tools.recommendation_tool import RecommendationTool
from semester_utils import SemesterManager

# Load environment variables
load_dotenv()


class QuestionType(Enum):
    """질문 유형 열거형"""
    COMPREHENSIVE = "comprehensive"
    GRADUATION = "graduation"
    RECOMMENDATION = "recommendation"
    COURSE = "course"
    STUDENT = "student"
    GENERAL = "general"


class AgentSystem:
    """멀티 에이전트 시스템 관리 클래스"""
    
    def __init__(self, authenticated_student_id: str = "20230578"):
        self.authenticated_student_id = authenticated_student_id
        self.semester_info = SemesterManager.get_current_semester_info()
        self.llm = self._create_llm()
        self.tools = self._initialize_tools()
        self.agents = self._create_agents()
    
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
            'course': CourseTool(),
            'enrollment': EnrollmentTool(),
            'graduation': GraduationTool(),
            'recommendation': RecommendationTool()
        }
        
        # 인증된 사용자 정보 설정
        for tool_name in ['student', 'enrollment']:
            tools[tool_name].set_authenticated_user(self.authenticated_student_id)
        
        return tools
    
    def _create_agents(self) -> Dict[str, Agent]:
        """에이전트 생성"""
        agents = {}
        
        # 학생 정보 전문가
        agents['student_expert'] = Agent(
            role='학생 정보 전문가',
            goal='학생의 기본 정보와 수강 이력을 정확하게 조회하고 분석합니다',
            backstory=self._get_student_expert_backstory(),
            llm=self.llm,
            tools=[self.tools['student'], self.tools['enrollment']],
            verbose=True,
            max_iter=3,
            allow_delegation=False
        )
        
        # 졸업 요건 전문가
        agents['graduation_expert'] = Agent(
            role='졸업 요건 전문가',
            goal='학과별, 연도별 졸업 요건을 정확하게 제공합니다',
            backstory=self._get_graduation_expert_backstory(),
            llm=self.llm,
            tools=[self.tools['graduation']],
            verbose=True,
            max_iter=2,
            allow_delegation=False
        )
        
        # 강의 정보 전문가
        agents['course_expert'] = Agent(
            role='강의 정보 전문가',
            goal='강의 정보를 검색하고 분석합니다',
            backstory=self._get_course_expert_backstory(),
            llm=self.llm,
            tools=[self.tools['course']],
            verbose=True,
            max_iter=2,
            allow_delegation=False
        )
        
        # 수강 추천 전문가
        agents['recommendation_expert'] = Agent(
            role='수강 추천 전문가',
            goal='개인화된 수강 추천을 제공합니다',
            backstory=self._get_recommendation_expert_backstory(),
            llm=self.llm,
            tools=[self.tools['recommendation']],
            verbose=True,
            max_iter=20,
            allow_delegation=False,
            max_retry_limit=5,
        )
        
        # 요약 전문가
        agents['summary_expert'] = Agent(
            role='학사 상담 요약 전문가',
            goal='전문가들의 정보를 간단히 요약하여 제공합니다',
            backstory=self._get_summary_expert_backstory(),
            llm=self.llm,
            tools=[],
            verbose=True,
            max_iter=1,
            allow_delegation=False
        )
        
        return agents
    
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
    
    def _get_graduation_expert_backstory(self) -> str:
        """졸업 요건 전문가 배경 스토리"""
        return '''당신은 졸업 요건 전문가입니다.
        
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
    
    def _get_course_expert_backstory(self) -> str:
        """강의 정보 전문가 배경 스토리"""
        return f'''당신은 강의 정보 전문가입니다.
        
        📅 현재 날짜 정보:
        - 다음 학기: {self.semester_info['next_semester_year']}년 {self.semester_info['next_semester']}학기
        
        주요 역할:
        - 강의 정보 검색 및 조회
        - 강의 시간표 및 교수 정보 제공
        - 선수과목 관계 분석
        
        답변 방식:
        - 도구의 출력을 그대로 전달
        - 필요시 간단한 설명 추가
        - 명확하고 직접적인 정보 제공'''
    
    def _get_recommendation_expert_backstory(self) -> str:
        """수강 추천 전문가 배경 스토리"""
        return '''당신은 수강 추천 전문가입니다.
        
        주요 역할:
        - 학생 상황에 맞는 개인화된 수강 추천
        - 졸업 요건 기반 우선순위 추천
        - 학점 균형과 난이도 고려
        - 시간표 효율성 분석
        
        답변 방식:
        - 구체적이고 실행 가능한 추천
        - 추천 이유와 함께 제시
        - 학습 계획과 로드맵 제공'''
    
    def _get_summary_expert_backstory(self) -> str:
        """요약 전문가 배경 스토리"""
        return f'''당신은 학사 상담 요약 전문가입니다.
        
        📅 현재 날짜 정보:
        - 오늘 날짜: {self.semester_info['current_date']}
        - 현재 학기: {"방학 기간" if not self.semester_info['current_semester'] else f"{self.semester_info['current_semester_year']}년 {self.semester_info['current_semester']}학기"}
        - 다음 학기: {self.semester_info['next_semester_year']}년 {self.semester_info['next_semester']}학기
        
        주요 역할:
        - 이미 수집된 정보를 간단히 요약
        - 명확하고 이해하기 쉬운 설명 제공
        - 실용적인 조언 제시
        
        답변 방식:
        - 간결하고 명확한 요약
        - 핵심 포인트 위주로 정리
        - 실행 가능한 다음 단계 제시'''
    
    def classify_question(self, question: str) -> QuestionType:
        """질문 유형 분류"""
        question_lower = question.lower()
        
        # 키워드 매핑
        keyword_mapping = {
            QuestionType.COMPREHENSIVE: ['종합', '전체', '모든', '완전한', '전반적', '총괄'],
            QuestionType.GRADUATION: ['졸업', '요건', '학점', '필수', '이수', '논문', '인증'],
            QuestionType.RECOMMENDATION: ['추천', '수강', '계획', '로드맵', '다음학기', '선택'],
            QuestionType.COURSE: ['강의', '과목', '시간표', '교수', '강좌'],
            QuestionType.STUDENT: ['내', '현황', '성적', '이력', '정보', '분석']
        }
        
        # 키워드 매칭
        for question_type, keywords in keyword_mapping.items():
            if any(keyword in question_lower for keyword in keywords):
                return question_type
        
        return QuestionType.GENERAL
    
    def create_tasks(self, question: str, question_type: QuestionType) -> List[Task]:
        """질문 유형에 따른 Task 생성"""
        tasks = []
        
        task_configs = {
            QuestionType.COMPREHENSIVE: [
                ('student_expert', "학생의 기본 정보와 수강 이력을 조회하고 분석해주세요", "학생의 기본 정보, 수강 이력, 취득 학점 현황"),
                ('graduation_expert', "해당 학생의 졸업 요건을 상세히 조회해주세요", "학과별, 입학년도별 상세한 졸업 요건 정보"),
                ('recommendation_expert', "앞선 정보를 바탕으로 수강 추천을 제공해주세요", "개인화된 수강 추천 및 로드맵"),
                ('summary_expert', "앞선 전문가들의 정보를 바탕으로 간단한 요약과 조언을 제공해주세요", "종합적인 요약 및 실행 가이드")
            ],
            QuestionType.GRADUATION: [
                ('graduation_expert', f"졸업 요건 정보를 상세히 조회해주세요: {question}", "상세한 졸업 요건 정보")
            ],
            QuestionType.RECOMMENDATION: [
                ('student_expert', f"수강 추천을 위한 학생 정보를 조회해주세요: {question}", "학생 현황 정보"),
                ('recommendation_expert', f"개인화된 수강 추천을 제공해주세요: {question}", "구체적인 수강 추천"),
                ('summary_expert', f"추천 정보를 요약하여 최종 가이드를 제공해주세요: {question}", "수강 추천 요약 가이드")
            ],
            QuestionType.COURSE: [
                ('course_expert', f"강의 정보를 검색해주세요: {question}", "강의 정보 및 세부사항")
            ],
            QuestionType.STUDENT: [
                ('student_expert', f"학생 정보를 조회하고 분석해주세요: {question}", "학생 정보 및 현황 분석")
            ],
            QuestionType.GENERAL: [
                ('graduation_expert', f"다음 질문에 답변해주세요: {question}", "질문에 대한 정확한 답변")
            ]
        }
        
        config = task_configs.get(question_type, task_configs[QuestionType.GENERAL])
        
        for agent_name, description, expected_output in config:
            tasks.append(Task(
                description=description,
                agent=self.agents[agent_name],
                expected_output=expected_output
            ))
        
        return tasks
    
    def process_query(self, question: str) -> str:
        """사용자 질문 처리"""
        # 질문 유형 분류
        question_type = self.classify_question(question)
        
        # Task 생성
        tasks = self.create_tasks(question, question_type)
        
        # 참여 에이전트 수집
        agents = list(set([task.agent for task in tasks]))
        
        # Crew 생성 및 실행
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=False  # 디버깅 메시지 제거
        )
        
        result = crew.kickoff()
        return result
    
    async def process_query_async(self, question: str) -> str:
        """비동기 사용자 질문 처리"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # CPU 집약적 작업을 별도 스레드에서 실행
        result = await loop.run_in_executor(
            None, 
            self.process_query, 
            question
        )
        return result


def main():
    """메인 실행 함수"""
    # 시스템 초기화
    system = AgentSystem()
    
    print("=== 리팩토링된 멀티 에이전트 학사 상담 시스템 ===")
    print("특징: 최적화된 구조, 반복문 최소화, 깔끔한 코드")
    print("장점: 높은 성능, 유지보수성, 확장성")
    print(f"현재 학기: {system.semester_info['current_semester_year']}년 {system.semester_info['current_semester']}학기" if system.semester_info['current_semester'] else "현재: 방학 기간")
    print(f"다음 학기: {system.semester_info['next_semester_year']}년 {system.semester_info['next_semester']}학기\n")
    
    # 사용자 입력 받기
    print("직접 질문해보세요 (종료하려면 'quit' 입력):")
    print("예시 질문:")
    print("- 내 졸업 요건 알려줘")
    print("- 다음 학기 추천해줘")
    print("- 강의 정보 찾아줘")
    print("- 내 성적 분석해줘")
    print("- 전체 현황 분석해줘\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print(f"\n🤖 리팩토링된 멀티 에이전트 시스템 처리 중...\n")
                result = system.process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")


if __name__ == "__main__":
    main()