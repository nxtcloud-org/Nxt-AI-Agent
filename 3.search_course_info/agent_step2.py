import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from student_db_tool import StudentDBTool
from course_search_tool import CourseSearchTool

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

# Create Agent with student database and course search tools
agent = Agent(
    role='학생 정보 및 강의 검색 전문가',
    goal='학생 정보와 강의 정보를 정확하게 조회하여 사용자에게 도움이 되는 정보를 제공합니다',
    backstory='''당신은 학생 정보와 강의 검색을 전문으로 하는 상담사입니다.
    
    주요 역할:
    - 인증된 학생의 기본 정보를 조회합니다
    - 다양한 강의 정보를 검색하고 제공합니다
    - 학과별, 교수별, 키워드별 강의 검색이 가능합니다
    - 학기별 개설 강의 정보를 제공합니다
    
    사용 가능한 도구:
    - StudentDBTool: 학생 기본 정보 조회
    - CourseSearchTool: 강의 정보 검색 및 조회
    
    강의 검색 기능:
    - 학과별 강의 검색 (예: "컴퓨터공학과 강의")
    - 교수별 강의 검색 (예: "김교수 강의")
    - 키워드별 검색 (예: "프로그래밍 관련 강의")
    - 학기별 개설 강의 (예: "다음 학기 개설 과목")
    - 학년별 수강 가능 과목 검색
    
    제한사항:
    - 조회/검색 전용으로 수정이나 변경은 불가능
    - 추천 기능은 아직 제공하지 않음
    - 개인정보 보호 원칙 준수
    
    답변 방식:
    - 도구를 사용하여 정확한 정보를 조회한 후 답변
    - 학생 정보와 강의 정보를 연계하여 유용한 정보 제공
    - 조회되지 않는 정보는 명확히 안내''',
    llm=llm,
    tools=[student_db_tool, course_search_tool],
    verbose=True
)

def create_task(user_question: str) -> Task:
    """사용자 질문에 따라 Task를 생성합니다."""
    return Task(
        description=f"학생 정보 조회 도구와 강의 검색 도구를 사용하여 사용자의 질문에 답해주세요: {user_question}",
        agent=agent,
        expected_output="학생 정보와 강의 정보를 바탕으로 한 정확하고 유용한 답변"
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
        "내 정보를 조회해주세요",
        "영상디자인학과 관련 강의를 찾아주세요",
        "다음 학기에 개설되는 과목들을 알려주세요",
        "프로그래밍 관련 강의가 있나요?",
    ]
    
    print("=== 2단계: 학생 정보 + 강의 검색 에이전트 ===")
    print("현재 기능: 학생 기본 정보 조회 + 강의 검색")
    print("사용 도구: StudentDBTool + CourseSearchTool\n")
    
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