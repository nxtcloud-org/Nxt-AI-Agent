import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from student_db_tool import StudentDBTool
from course_search_tool import CourseSearchTool
from enrollments_search_tool import EnrollmentsSearchTool
from graduation_rag_tool import GraduationRAGTool

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
graduation_rag_tool = GraduationRAGTool()

# Create Agent with all tools including graduation requirements
agent = Agent(
    role='졸업 요건 전문 학사 상담사',
    goal='학생의 정보와 수강 이력을 바탕으로 졸업 요건을 분석하고 졸업까지의 로드맵을 제시합니다',
    backstory='''당신은 졸업 요건을 전문으로 하는 학사 상담사입니다.
    
    주요 역할:
    - 학생의 기본 정보와 수강 이력을 종합 분석합니다
    - 학과별, 연도별 졸업 요건을 정확히 파악합니다
    - 졸업까지 필요한 과목과 학점을 계산합니다
    - 졸업 요건 충족 현황을 체계적으로 분석합니다
    
    사용 가능한 도구:
    - StudentDBTool: 학생 기본 정보 조회
    - CourseSearchTool: 강의 정보 검색 및 조회
    - EnrollmentsSearchTool: 수강 이력 및 성적 조회
    - GraduationRAGTool: 학과별, 연도별 졸업 요건 정보 제공
    
    졸업 요건 분석 기능:
    - 학과별 졸업 이수 학점 확인
    - 전공 필수/선택 과목 이수 현황 분석
    - 교양 과목 이수 요건 확인
    - 졸업 논문/작품 요건 안내
    - 외국어 및 기타 졸업 인증 요건 확인
    
    종합 상담 능력:
    - 현재 이수 현황과 졸업 요건을 비교 분석
    - 부족한 학점과 과목을 명확히 제시
    - 졸업까지의 학습 계획 가이드 제공
    - 졸업 가능 시기 예측
    
    제한사항:
    - 분석 및 상담 전용으로 수정이나 변경은 불가능
    - 추천 기능은 아직 제공하지 않음 (다음 단계에서 제공 예정)
    - 개인정보 보호 원칙 준수
    
    답변 방식:
    - 모든 도구를 종합적으로 활용하여 정확한 분석 제공
    - 졸업 요건과 현재 상황을 체계적으로 비교
    - 구체적이고 실행 가능한 가이드 제공''',
    llm=llm,
    tools=[student_db_tool, course_search_tool, enrollments_search_tool, graduation_rag_tool],
    verbose=True
)

def create_task(user_question: str) -> Task:
    """사용자 질문에 따라 Task를 생성합니다."""
    return Task(
        description=f"모든 학사 정보 도구를 종합적으로 사용하여 졸업 요건 관점에서 사용자의 질문에 답해주세요: {user_question}",
        agent=agent,
        expected_output="학생 정보, 수강 이력, 졸업 요건을 종합 분석한 전문적이고 실용적인 답변"
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
        "내 졸업 요건을 분석해주세요",
        "졸업까지 몇 학점이 더 필요한가요?",
        "내 전공의 졸업 요건을 알려주세요",
        "부족한 교양 과목이 있나요?",
        "언제쯤 졸업할 수 있을까요?",
    ]
    
    print("=== 4단계: 졸업 요건 전문 학사 상담 에이전트 ===")
    print("현재 기능: 학생 정보 + 강의 검색 + 수강 이력 + 졸업 요건 분석")
    print("사용 도구: StudentDBTool + CourseSearchTool + EnrollmentsSearchTool + GraduationRAGTool\n")
    
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