import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from tools.student_tool import StudentTool
from tools.course_tool import CourseTool
from tools.enrollment_tool import EnrollmentTool
from tools.graduation_tool import GraduationTool
from tools.recommendation_tool import RecommendationTool
from semester_utils import SemesterManager

# Load environment variables
load_dotenv()

# 현재 날짜와 학기 정보 가져오기
semester_info = SemesterManager.get_current_semester_info()

# AWS Bedrock configuration using CrewAI LLM
model_id = os.environ["BEDROCK_MODEL_ID"]

# Create LLM instance with Bedrock
llm = LLM(
    model=f"bedrock/{model_id}",
    temperature=0.2,
    max_tokens=3000
)

# 인증된 사용자 정보 (실제로는 세션에서 가져옴)
AUTHENTICATED_STUDENT_ID = "20230578"

# Create all tool instances
student_tool = StudentTool()
course_tool = CourseTool()
enrollment_tool = EnrollmentTool()
graduation_tool = GraduationTool()
recommendation_tool = RecommendationTool()

# 도구들에 인증된 사용자 정보 전달
student_tool.set_authenticated_user(AUTHENTICATED_STUDENT_ID)
enrollment_tool.set_authenticated_user(AUTHENTICATED_STUDENT_ID)

# 단일 통합 에이전트 생성
academic_advisor_agent = Agent(
    # TODO: 이 부분을 수정해주세요!
    role='',
    goal='',
    backstory=f'',
    llm='',
    tools=[],
    verbose=True,
    max_iter=5,
    allow_delegation=False
)

def process_query(question: str) -> str:
    """사용자 질문을 단일 에이전트로 처리합니다."""
    print(f"🔍 단일 에이전트가 질문을 처리 중: {question}")
    
    # 단일 Task 생성
    task = Task(
        description=f"다음 질문에 종합적으로 답변해주세요. 필요한 경우 여러 도구를 사용하여 완전한 답변을 제공하세요: {question}",
        agent=academic_advisor_agent,
        expected_output="질문에 대한 종합적이고 정확한 답변"
    )
    
    # Crew 생성 및 실행 (단일 에이전트, 단일 Task)
    crew = Crew(
        agents=[academic_advisor_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    print("=== 단일 에이전트 학사 상담 시스템 ===")
    print("특징: 하나의 통합 에이전트가 모든 학사 상담을 처리")
    print("장점: 간단한 구조, 빠른 응답, 일관된 서비스")
    print("보안: SQL 직접 작성 방지, 개인정보 보호")
    print(f"현재 학기: {semester_info['current_semester_year']}년 {semester_info['current_semester']}학기" if semester_info['current_semester'] else "현재: 방학 기간")
    print(f"다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"[테스트 {i}] 질문: {question}")
        print("-" * 50)
        try:
            result = process_query(question)
            print(f"답변: {result}")
        except Exception as e:
            print(f"오류: {str(e)}")
        print("=" * 50)
        print()
    
    # 사용자 입력 받기
    print("\n직접 질문해보세요 (종료하려면 'quit' 입력):")
    print("예시 질문:")
    print("- 내 졸업 요건 알려줘")
    print("- 다음 학기 추천해줘")
    print("- 강의 정보 찾아줘")
    print("- 내 성적 분석해줘")
    print("- 전체 현황 분석해줘")
    print("- 컴퓨터 관련 강의 찾아줘\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print(f"\n🤖 단일 에이전트 시스템 처리 중...\n")
                result = process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")