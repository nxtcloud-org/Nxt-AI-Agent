import os
import json
import psycopg2
import psycopg2.extras
import boto3
from crewai.tools import BaseTool
from typing import Type, Dict, List
from pydantic import BaseModel, Field
from langchain_aws import BedrockEmbeddings
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

class GraduationRAGToolInput(BaseModel):
    """Input schema for GraduationRAGTool."""
    query: str = Field(..., description="졸업 요건 검색을 위한 자연어 질문 (학과명, 입학년도 포함)")

class GraduationRAGTool(BaseTool):
    name: str = "graduation_rag_tool"
    description: str = """
    학과별, 연도별 졸업 요건 정보를 제공하는 RAG 도구입니다.
    
    주요 기능:
    1. 학과별 졸업 요건 조회
    2. 입학년도별 졸업 요건 차이점 확인
    3. 필수 이수 학점 및 과목 정보 제공
    4. 졸업 논문/작품 요건 안내
    5. 외국어 및 기타 졸업 요건 정보
    
    사용법: 
    - "영상디자인학과 2020년 입학 졸업 요건"
    - "컴퓨터공학과 졸업에 필요한 학점"
    - "내 전공 졸업 요건 알려줘"
    """
    args_schema: Type[BaseModel] = GraduationRAGToolInput

    def __init__(self):
        super().__init__()

    def _get_db_connection(self):
        """데이터베이스 연결을 반환합니다."""
        return psycopg2.connect(
            host=os.environ.get('RAG_DB_HOST', 'localhost'),
            port=os.environ.get('RAG_DB_PORT', '5432'),
            database=os.environ.get('RAG_DB_NAME', 'rag_db'),
            user=os.environ.get('RAG_DB_USER', 'postgres'),
            password=os.environ.get('RAG_DB_PASSWORD', 'password')
        )

    def _search_vector_db(self, query: str, top_k: int = 5) -> List[Dict]:
        """벡터 데이터베이스에서 유사한 문서를 검색합니다."""
        try:
            # Bedrock 임베딩 클라이언트 초기화
            bedrock_region = os.environ.get('BEDROCK_REGION', 'us-east-1')
            embedding_model_id = os.environ.get('RAG_EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
            bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=bedrock_region)
            embeddings = BedrockEmbeddings(client=bedrock_client, model_id=embedding_model_id)
            
            # 쿼리를 임베딩으로 변환
            query_embedding = embeddings.embed_query(query)
            
            # PostgreSQL 연결
            conn = self._get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 벡터 유사도 검색 (코사인 유사도 사용)
            cursor.execute("""
                SELECT 
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documents 
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, top_k))
            
            results = cursor.fetchall()
            
            # 결과를 딕셔너리 리스트로 변환
            search_results = []
            for row in results:
                # metadata가 이미 dict인지 string인지 확인
                metadata = row['metadata']
                if isinstance(metadata, str):
                    metadata = json.loads(metadata) if metadata else {}
                elif metadata is None:
                    metadata = {}
                
                search_results.append({
                    'content': row['content'],
                    'metadata': metadata,
                    'similarity': float(row['similarity'])
                })
            
            conn.close()
            return search_results
            
        except Exception as e:
            print(f"벡터 DB 검색 중 오류: {str(e)}")
            return []

    def _format_rag_results(self, query: str, search_results: List[Dict]) -> str:
        """RAG 검색 결과를 포맷팅합니다."""
        if not search_results:
            return "죄송합니다. 해당 질문에 대한 졸업 요건 정보를 찾을 수 없습니다."
        
        result = f"=== 졸업 요건 정보 ===\n\n"
        result += f"**질문**: {query}\n\n"
        
        # 가장 관련성 높은 결과들을 조합
        relevant_content = []
        for i, doc in enumerate(search_results):
            if doc['similarity'] > 0.7:  # 유사도 임계값
                relevant_content.append(doc['content'])
        
        if relevant_content:
            result += "**관련 졸업 요건 정보**:\n\n"
            for i, content in enumerate(relevant_content[:3], 1):  # 상위 3개만 표시
                result += f"{i}. {content}\n\n"
        else:
            # 유사도가 낮더라도 가장 관련성 높은 결과 표시
            result += "**관련 정보** (참고용):\n\n"
            result += f"{search_results[0]['content']}\n\n"
        
        # 메타데이터 정보 추가
        if search_results[0]['metadata']:
            metadata = search_results[0]['metadata']
            if 'source_file' in metadata:
                result += f"📄 **출처**: {metadata['source_file']}\n"
        
        return result

    def _run(self, query: str) -> str:
        """졸업 요건 정보를 검색하고 반환합니다."""
        try:
            # 벡터 데이터베이스에서 관련 문서 검색
            search_results = self._search_vector_db(query, top_k=5)
            
            # 검색 결과를 포맷팅하여 반환
            return self._format_rag_results(query, search_results)
            
        except Exception as e:
            return f"졸업 요건 정보 검색 중 오류가 발생했습니다: {str(e)}"

