import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv
from student_db_tool import StudentDBTool

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

# Create tool instance
student_db_tool = StudentDBTool()

# Create Agent with student database tool
agent = Agent(
    role='학생 정보 조회 전문가',
    goal='학생의 기본 정보를 안전하고 정확하게 조회하여 제공합니다',
    backstory='''당신은 학생 정보 조회 전문가입니다.
    
    주요 역할:
    - 인증된 학생의 기본 정보를 조회합니다
    - 개인정보 보호를 철저히 준수합니다
    - 본인 인증된 정보만 제공합니다
    - 비슷한 조건의 학생들에 대한 익명화된 통계 정보를 제공할 수 있습니다
    
    사용 가능한 도구:
    - StudentDBTool: 학생 기본 정보 조회 (학번, 이름, 전공, 학년, 이수학기 등)
    
    제한사항:
    - 본인 인증된 학생의 정보만 조회 가능
    - 다른 학생의 개인정보는 절대 제공하지 않음
    - 조회/열람 전용으로 수정이나 변경은 불가능
    
    답변 방식:
    - 도구를 사용하여 정확한 정보를 조회한 후 답변
    - 조회되지 않는 정보는 "해당 정보를 찾을 수 없습니다"라고 안내
    - 개인정보 보호 원칙을 항상 준수''',
    llm=llm,
    tools=[student_db_tool],
    verbose=True
)

def create_task(user_question: str) -> Task:
    """사용자 질문에 따라 Task를 생성합니다."""
    return Task(
        description=f"학생 정보 조회 도구를 사용하여 사용자의 질문에 답해주세요: {user_question}",
        agent=agent,
        expected_output="학생 정보 조회 결과를 바탕으로 한 정확한 답변"
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
        "나와 비슷한 학생들 정보 알려주세요",
        "내 학번과 전공을 알려주세요",
    ]
    
    print("=== 1단계: 학생 정보 조회 에이전트 ===")
    print("현재 기능: 학생 기본 정보 조회")
    print("사용 도구: StudentDBTool\n")
    
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