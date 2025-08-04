import os
from crewai import Agent, Crew, Task, Process, LLM
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Bedrock configuration using CrewAI LLM
model_id = os.environ["BEDROCK_MODEL_ID"]

# Create LLM instance with Bedrock
llm = LLM(
    model=f"bedrock/{model_id}",
    temperature=0.7,
    max_tokens=1000
)

# Create a simple agent without any tools
simple_agent = Agent(
    role='친근한 AI 에이전트',
    goal='사용자와 자연스럽고 도움이 되는 대화를 나누며, 질문에 최선을 다해 답변합니다',
    backstory='''당신은 친근하고 도움이 되는 AI 에이전트입니다.
    
    특징:
    - 사용자와 자연스럽게 대화합니다
    - 질문에 성실하게 답변하려고 노력합니다
    - 모르는 것은 솔직하게 모른다고 말합니다
    - 항상 예의 바르고 친절합니다
    - 한국어로 대화합니다
    
    제한사항:
    - 외부 도구나 데이터베이스에 접근할 수 없습니다
    - 실시간 정보를 조회할 수 없습니다
    - 개인정보나 민감한 정보는 다루지 않습니다
    
    답변 스타일:
    - 간결하고 명확하게 답변합니다
    - 필요시 예시를 들어 설명합니다
    - 사용자의 질문 의도를 파악하여 적절히 답변합니다''',
    llm=llm,
    tools=[],  # 도구 없음
    verbose=True
)

def create_simple_task(user_question: str) -> Task:
    """사용자 질문에 따라 간단한 Task를 생성합니다."""
    return Task(
        description=f"사용자의 질문에 친근하고 도움이 되는 답변을 해주세요: {user_question}",
        agent=simple_agent,
        expected_output="사용자 질문에 대한 친근하고 도움이 되는 답변"
    )

def chat_with_simple_agent(question: str) -> str:
    """사용자 질문을 받아서 간단한 에이전트가 답변을 제공합니다."""
    task = create_simple_task(question)
    
    crew = Crew(
        agents=[simple_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    print("=== 간단한 AI 에이전트 ===")
    print("안녕하세요! 저는 간단한 AI 에이전트입니다.")
    print("궁금한 것이 있으면 언제든 물어보세요!")
    print("(종료하려면 'quit', 'exit', '종료' 중 하나를 입력하세요)\n")
    
    while True:
        user_input = input("질문: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '종료', 'q']:
            print("대화를 종료합니다. 안녕히 가세요!")
            break
            
        if not user_input:
            print("질문을 입력해주세요.")
            continue
            
        try:
            print("\n답변을 생성하고 있습니다...\n")
            response = chat_with_simple_agent(user_input)
            print(f"답변: {response}\n")
            print("-" * 50)
            
        except Exception as e:
            print(f"오류가 발생했습니다: {str(e)}")
            print("다시 시도해주세요.\n")