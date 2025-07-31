"""
졸업 요건 RAG 도구 (리팩토링 버전)
"""
import os
import json
import boto3
from crewai.tools import BaseTool
from typing import Type, Dict, List
from pydantic import BaseModel, Field
from langchain_aws import BedrockEmbeddings
from dotenv import load_dotenv
import sys
import os

# 상위 디렉토리의 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from base_tool import DatabaseManager

# .env 파일에서 환경변수 로드
load_dotenv()


class GraduationToolInput(BaseModel):
    """Input schema for GraduationTool."""
    query: str = Field(..., description="졸업 요건 검색을 위한 자연어 질문 (학과명, 입학년도 포함)")


class GraduationTool(BaseTool):
    name: str = "graduation_tool"
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
    args_schema: Type[BaseModel] = GraduationToolInput

    def __init__(self):
        super().__init__()
        self._embeddings = None
    
    @property
    def embeddings(self):
        """임베딩 클라이언트 지연 초기화"""
        if self._embeddings is None:
            bedrock_region = os.environ.get('BEDROCK_REGION', 'us-east-1')
            embedding_model_id = os.environ.get('RAG_EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
            bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=bedrock_region)
            self._embeddings = BedrockEmbeddings(client=bedrock_client, model_id=embedding_model_id)
        return self._embeddings

    def _run(self, query: str) -> str:
        """졸업 요건 정보를 검색하고 반환합니다."""
        try:
            print(f"[RAG Tool] 검색 시작: {query}")
            
            # 벡터 데이터베이스에서 관련 문서 검색
            search_results = self._search_vector_db(query, top_k=5)
            
            print(f"[RAG Tool] 검색 결과: {len(search_results)}개 문서 발견")
            
            # 검색 결과를 포맷팅하여 반환
            formatted_result = self._format_rag_results(query, search_results)
            
            print(f"[RAG Tool] 포맷팅 완료: {len(formatted_result)}자 반환")
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"❌ RAG 도구 오류: {str(e)}"
            print(f"[RAG Tool] 오류 발생: {error_msg}")
            return error_msg

    def _search_vector_db(self, query: str, top_k: int = 5) -> List[Dict]:
        """벡터 데이터베이스에서 유사한 문서를 검색합니다."""
        try:
            # 쿼리를 임베딩으로 변환
            query_embedding = self.embeddings.embed_query(query)
            
            # PostgreSQL 연결 및 검색
            with DatabaseManager.postgres_connection() as conn:
                cursor = conn.cursor()
                
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
                    content, metadata, similarity = row
                    
                    # metadata 처리
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata) if metadata else {}
                    elif metadata is None:
                        metadata = {}
                    
                    search_results.append({
                        'content': content,
                        'metadata': metadata,
                        'similarity': float(similarity)
                    })
                
                return search_results
                
        except Exception as e:
            print(f"벡터 DB 검색 중 오류: {str(e)}")
            return []

    def _format_rag_results(self, query: str, search_results: List[Dict]) -> str:
        """RAG 검색 결과를 포맷팅합니다."""
        if not search_results:
            return "❌ RAG 검색 결과: 해당 질문에 대한 졸업 요건 정보를 찾을 수 없습니다."
        
        result = f"✅ RAG 검색 성공 - 졸업 요건 정보 발견\n\n"
        result += f"🔍 **검색 질문**: {query}\n"
        result += f"📊 **검색된 문서 수**: {len(search_results)}개\n"
        result += f"🎯 **최고 유사도**: {search_results[0]['similarity']:.3f}\n\n"
        
        # 관련성 높은 결과들 선별 및 조합
        relevant_content = self._extract_relevant_content(search_results)
        
        if relevant_content:
            result += f"📋 **관련 졸업 요건 정보** ({len(relevant_content)}개 문서에서 추출):\n\n"
            for i, content in enumerate(relevant_content, 1):
                result += f"[문서 {i}] {content}\n\n"
        else:
            # 유사도가 낮더라도 가장 관련성 높은 결과 표시
            result += f"📋 **참고 정보** (유사도: {search_results[0]['similarity']:.3f}):\n\n"
            result += f"[문서 1] {search_results[0]['content']}\n\n"
        
        # 메타데이터 정보 추가
        if search_results[0]['metadata'] and 'source_file' in search_results[0]['metadata']:
            result += f"📄 **출처**: {search_results[0]['metadata']['source_file']}\n"
        
        result += f"\n💡 **RAG 도구 상태**: 정상 작동 중 - 총 {len(search_results)}개 문서 검색 완료"
        
        return result

    def _extract_relevant_content(self, search_results: List[Dict], similarity_threshold: float = 0.5) -> List[str]:
        """관련성 높은 콘텐츠 추출"""
        relevant_content = []
        
        for doc in search_results[:3]:  # 상위 3개만 확인
            if doc['similarity'] > similarity_threshold:
                relevant_content.append(doc['content'])
        
        return relevant_content