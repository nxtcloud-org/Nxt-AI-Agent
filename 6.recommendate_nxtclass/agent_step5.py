import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from student_db_tool import StudentDBTool
from course_search_tool import CourseSearchTool, get_current_semester_info
from enrollments_search_tool import EnrollmentsSearchTool
from graduation_rag_tool import GraduationRAGTool
from recommendation_engine_tool import RecommendationEngineTool

# Load environment variables
load_dotenv()

# 현재 날짜와 학기 정보 가져오기
semester_info = get_current_semester_info()

# AWS Bedrock configuration using CrewAI LLM
model_id = os.environ["BEDROCK_MODEL_ID"]

# Create LLM instance with Bedrock
llm = LLM(
    model=f"bedrock/{model_id}",
    temperature=0.2,
    max_tokens=1000
)

# Create all tool instances
student_db_tool = StudentDBTool()
course_search_tool = CourseSearchTool()
enrollments_search_tool = EnrollmentsSearchTool()
graduation_rag_tool = GraduationRAGTool()
recommendation_engine_tool = RecommendationEngineTool()

# Create the final comprehensive agent
agent = Agent(
    role='종합 학사 상담 및 수강 추천 전문가',
    goal='학생의 모든 학사 정보를 종합 분석하여 개인화된 수강 추천과 졸업 로드맵을 제공합니다',
    backstory=f'''당신은 모든 학사 업무를 종합적으로 처리하는 최고 수준의 학사 상담 전문가입니다.
    
    📅 현재 날짜 정보:
    - 오늘 날짜: {semester_info['current_date']}
    - 현재 학기: {"방학 기간" if not semester_info['current_semester'] else f"{semester_info['current_semester_year']}년 {semester_info['current_semester']}학기"}
    - 다음 학기: {semester_info['next_semester_year']}년 {semester_info['next_semester']}학기
    - 지난 학기: {semester_info['prev_semester_year']}년 {semester_info['prev_semester']}학기
    
    주요 역할:
    - 학생의 기본 정보를 정확히 파악합니다
    - 수강 이력을 체계적으로 분석합니다
    - 졸업 요건을 정확히 확인하고 분석합니다
    - 개인화된 수강 추천을 제공합니다
    - 졸업까지의 완전한 로드맵을 제시합니다
    
    사용 가능한 도구:
    - StudentDBTool: 학생 기본 정보 조회
    - CourseSearchTool: 강의 정보 검색 및 조회
    - EnrollmentsSearchTool: 수강 이력 및 성적 조회
    - GraduationRAGTool: 학과별, 연도별 졸업 요건 정보
    - RecommendationEngineTool: 개인화된 수강 추천 시스템
    
    종합 상담 및 추천 기능:
    - 학생 현황 종합 분석 (기본 정보 + 수강 이력 + 졸업 요건)
    - 졸업 요건 충족도 정확한 계산
    - 부족한 학점과 과목 명확한 제시
    - 다음 학기 최적 수강 계획 추천
    - 졸업까지의 단계별 로드맵 제공
    - 학점 균형과 난이도를 고려한 추천
    - 선수 과목 관계를 고려한 수강 순서 제안
    
    추천 시스템 특징:
    - 졸업 요건 기반 우선순위 추천
    - 이미 수강한 과목 제외 (과목 코드 앞 5자리 기준)
    - 전공/교양/일반선택 균형 고려
    - 학점 제한 내 최적화
    - 시간표 효율성 고려
    
    답변 방식:
    - 모든 도구를 체계적으로 활용하여 종합적인 분석 제공
    - 현재 상황과 목표를 명확히 제시
    - 구체적이고 실행 가능한 추천 제공
    - 단계별 실행 계획 제시
    - 사용자 친화적이고 이해하기 쉬운 설명''',
    llm=llm,
    tools=[student_db_tool, course_search_tool, enrollments_search_tool, graduation_rag_tool, recommendation_engine_tool],
    verbose=True
)

def create_task(user_question: str) -> Task:
    """사용자 질문에 따라 Task를 생성합니다."""
    return Task(
        description=f"모든 학사 정보 도구를 종합적으로 활용하여 최고 수준의 개인화된 상담과 추천을 제공해주세요: {user_question}",
        agent=agent,
        expected_output="학생의 모든 정보를 종합 분석한 개인화된 전문 상담 및 구체적인 실행 계획"
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
        "내 전체 학사 현황을 종합 분석해주세요",
        "다음 학기 수강 추천해주세요",
        "졸업까지의 완전한 로드맵을 만들어주세요",
        "18학점으로 다음 학기 계획을 세워주세요",
        "내 졸업 요건과 추천 과목을 함께 알려주세요",
    ]
    
    print("=== 5단계: 최종 종합 학사 상담 및 추천 에이전트 ===")
    print("현재 기능: 완전한 학사 상담 + 개인화된 수강 추천 시스템")
    print("사용 도구: 모든 도구 통합 (StudentDB + CourseSearch + Enrollments + Graduation + Recommendation)")
    print(f"현재 학기: {semester_info['current_semester_year']}년 {semester_info['current_semester']}학기")
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
    print("- 내 전체 현황을 분석해주세요")
    print("- 다음 학기 수강 추천해주세요")
    print("- 졸업까지 로드맵을 만들어주세요")
    print("- 교양 과목 추천해주세요")
    print("- 내 성적과 졸업 요건을 분석해주세요\n")
    
    while True:
        user_input = input("질문: ").strip()
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("상담을 종료합니다. 좋은 하루 되세요!")
            break
        if user_input:
            try:
                print("\n종합 분석 중입니다...\n")
                result = process_query(user_input)
                print(f"답변: {result}")
                print("\n" + "="*50)
            except Exception as e:
                print(f"오류: {str(e)}")
        else:
            print("질문을 입력해주세요.")