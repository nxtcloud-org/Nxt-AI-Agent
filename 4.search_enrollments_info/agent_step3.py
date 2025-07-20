import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from student_db_tool import StudentDBTool
from course_search_tool import CourseSearchTool
from enrollments_search_tool import EnrollmentsSearchTool

# Load environment variables
load_dotenv()

# AWS Bedrock configuration using CrewAI LLM
model_id = os.environ["BEDROCK_MODEL_ID"]

# Create LLM instance with Bedrock
llm = LLM(
    model=f"bedrock/{model_id}",
    temperature=0.3,
    max_tokens=1000
)

# Create tool instances
student_db_tool = StudentDBTool()
course_search_tool = CourseSearchTool()
enrollments_search_tool = EnrollmentsSearchTool()

# Create Agent with student, course, and enrollment tools
agent = Agent(
    role='종합 학사 정보 상담사',
    goal='학생의 기본 정보, 강의 정보, 수강 이력을 종합적으로 분석하여 유용한 정보를 제공합니다',
    backstory='''당신은 종합적인 학사 정보를 다루는 전문 상담사입니다.
    
    주요 역할:
    - 학생의 기본 정보를 조회합니다
    - 다양한 강의 정보를 검색하고 제공합니다
    - 학생의 수강 이력과 성적을 분석합니다
    - 학생의 학업 진행 상황을 파악합니다
    
    사용 가능한 도구:
    - StudentDBTool: 학생 기본 정보 조회
    - CourseSearchTool: 강의 정보 검색 및 조회
    - EnrollmentsSearchTool: 수강 이력 및 성적 조회
    
    수강 이력 분석 기능:
    - 전체 이수 과목 목록 조회
    - 학기별 수강 과목 분석
    - 성적별 과목 분류 (A+, A, B+ 등)
    - 과목 유형별 이수 현황 (전공필수, 전공선택, 교양 등)
    - 이수 학점 통계 및 분석
    
    종합 분석 능력:
    - 학생 정보 + 수강 이력을 연계한 학업 현황 분석
    - 개설 강의와 이수 과목을 비교하여 유용한 정보 제공
    - 학업 진행도 파악 및 현황 정리
    
    제한사항:
    - 조회/분석 전용으로 수정이나 변경은 불가능
    - 추천 기능은 아직 제공하지 않음
    - 개인정보 보호 원칙 준수
    
    답변 방식:
    - 여러 도구를 조합하여 종합적인 정보 제공
    - 학생의 학업 현황을 체계적으로 분석
    - 데이터 기반의 정확한 정보 제공''',
    llm=llm,
    tools=[student_db_tool, course_search_tool, enrollments_search_tool],
    verbose=True
)

def create_task(user_question: str) -> Task:
    """사용자 질문에 따라 Task를 생성합니다."""
    return Task(
        description=f"학생 정보, 강의 검색, 수강 이력 도구를 종합적으로 사용하여 사용자의 질문에 답해주세요: {user_question}",
        agent=agent,
        expected_output="학생 정보, 강의 정보, 수강 이력을 종합 분석한 체계적이고 유용한 답변"
    )

def process_query(question: str) -> str:
    """사용자 질문을 처리합니다."""
    task = create_task(question)
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    # 테스트용 질문들
    test_questions = [
        "내 정보와 수강 이력을 종합해서 알려주세요",
        "내가 이수한 과목들을 분석해주세요",
        "내 성적 현황을 정리해주세요",
        "전공 과목과 교양 과목 이수 현황을 알려주세요",
        "내 학업 진행 상황을 분석해주세요",
    ]
    
    print("=== 3단계: 종합 학사 정보 상담 에이전트 ===")
    print("현재 기능: 학생 정보 + 강의 검색 + 수강 이력 분석")
    print("사용 도구: StudentDBTool + CourseSearchTool + EnrollmentsSearchTool\n")
    
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
    while True:
        user_input = input("\n질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            break
        if user_input:
            try:
                result = process_query(user_input)
                print(f"답변: {result}")
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")