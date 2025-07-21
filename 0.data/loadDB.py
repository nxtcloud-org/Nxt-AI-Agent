import pandas as pd
import pymysql
import psycopg2
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from tabulate import tabulate

# 환경변수 로드
load_dotenv()

# RDS 연결 정보
RDS_CONFIG = {
    'host': os.getenv('RDS_HOST', 'your_host'),
    'port': int(os.getenv('RDS_PORT', '3306')),
    'database': os.getenv('RDS_DATABASE', 'nxtclass'),  # 수정된 DB 이름
    'username': os.getenv('RDS_USERNAME', 'admin'),
    'password': os.getenv('RDS_PASSWORD', 'your_password'),
    'engine_type': os.getenv('DB_ENGINE', 'mysql')
}

def create_connection():
    """데이터베이스 연결 생성"""
    try:
        if RDS_CONFIG['engine_type'] == 'mysql':
            connection_string = f"mysql+pymysql://{RDS_CONFIG['username']}:{RDS_CONFIG['password']}@{RDS_CONFIG['host']}:{RDS_CONFIG['port']}/{RDS_CONFIG['database']}"
        else:
            connection_string = f"postgresql://{RDS_CONFIG['username']}:{RDS_CONFIG['password']}@{RDS_CONFIG['host']}:{RDS_CONFIG['port']}/{RDS_CONFIG['database']}"
        
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return None

def get_all_tables(engine):
    """모든 테이블 목록 가져오기"""
    try:
        with engine.connect() as conn:
            if RDS_CONFIG['engine_type'] == 'mysql':
                query = text("SHOW TABLES")
                result = conn.execute(query)
                tables = [row[0] for row in result.fetchall()]
            else:  # postgresql
                query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                """)
                result = conn.execute(query)
                tables = [row[0] for row in result.fetchall()]
            
            return tables
    except Exception as e:
        print(f"❌ 테이블 목록 조회 실패: {e}")
        return []

def get_table_structure_mysql(engine, table_name):
    """MySQL 테이블 구조 상세 조회"""
    try:
        with engine.connect() as conn:
            # 컬럼 정보
            desc_query = text(f"DESCRIBE `{table_name}`")
            desc_result = conn.execute(desc_query)
            
            columns = []
            for row in desc_result.fetchall():
                columns.append({
                    'Column': row[0],
                    'Type': row[1],
                    'Null': row[2],
                    'Key': row[3],
                    'Default': row[4] if row[4] is not None else 'NULL',
                    'Extra': row[5]
                })
            
            # 테이블 정보
            info_query = text(f"""
                SELECT 
                    TABLE_COMMENT,
                    ENGINE,
                    TABLE_COLLATION,
                    AUTO_INCREMENT
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = '{RDS_CONFIG['database']}' 
                AND TABLE_NAME = '{table_name}'
            """)
            info_result = conn.execute(info_query).fetchone()
            
            # 인덱스 정보
            index_query = text(f"SHOW INDEX FROM `{table_name}`")
            index_result = conn.execute(index_query)
            
            indexes = {}
            for row in index_result.fetchall():
                index_name = row[2]
                if index_name not in indexes:
                    indexes[index_name] = {
                        'columns': [],
                        'unique': not bool(row[1]),
                        'type': row[10] if len(row) > 10 else 'BTREE'
                    }
                indexes[index_name]['columns'].append(row[4])
            
            # 외래키 정보
            fk_query = text(f"""
                SELECT 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME,
                    CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = '{RDS_CONFIG['database']}' 
                AND TABLE_NAME = '{table_name}'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            fk_result = conn.execute(fk_query)
            foreign_keys = list(fk_result.fetchall())
            
            return {
                'columns': columns,
                'table_info': info_result,
                'indexes': indexes,
                'foreign_keys': foreign_keys
            }
            
    except Exception as e:
        print(f"❌ 테이블 '{table_name}' 구조 조회 실패: {e}")
        return None

def get_table_structure_postgresql(engine, table_name):
    """PostgreSQL 테이블 구조 상세 조회"""
    try:
        with engine.connect() as conn:
            # 컬럼 정보
            column_query = text(f"""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            column_result = conn.execute(column_query)
            
            columns = []
            for row in column_result.fetchall():
                data_type = row[1]
                if row[2]:  # character_maximum_length
                    data_type += f"({row[2]})"
                
                columns.append({
                    'Column': row[0],
                    'Type': data_type,
                    'Null': 'YES' if row[3] == 'YES' else 'NO',
                    'Default': row[4] if row[4] is not None else 'NULL'
                })
            
            # 기본키/인덱스 정보
            key_query = text(f"""
                SELECT 
                    kcu.column_name,
                    tc.constraint_type
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = '{table_name}' 
                AND tc.table_schema = 'public'
            """)
            key_result = conn.execute(key_query)
            keys = {row[0]: row[1] for row in key_result.fetchall()}
            
            # 컬럼에 키 정보 추가
            for col in columns:
                if col['Column'] in keys:
                    if keys[col['Column']] == 'PRIMARY KEY':
                        col['Key'] = 'PRI'
                    elif keys[col['Column']] == 'FOREIGN KEY':
                        col['Key'] = 'FOR'
                    else:
                        col['Key'] = 'KEY'
                else:
                    col['Key'] = ''
            
            # 외래키 정보
            fk_query = text(f"""
                SELECT 
                    kcu.column_name,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column,
                    tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = '{table_name}'
                AND tc.table_schema = 'public'
            """)
            fk_result = conn.execute(fk_query)
            foreign_keys = list(fk_result.fetchall())
            
            return {
                'columns': columns,
                'foreign_keys': foreign_keys
            }
            
    except Exception as e:
        print(f"❌ 테이블 '{table_name}' 구조 조회 실패: {e}")
        return None

def get_table_data_sample(engine, table_name, limit=5):
    """테이블 샘플 데이터 조회"""
    try:
        with engine.connect() as conn:
            query = text(f"SELECT * FROM `{table_name}` LIMIT {limit}")
            result = conn.execute(query)
            
            # 컬럼명과 데이터 가져오기
            columns = list(result.keys())
            rows = result.fetchall()
            
            return columns, rows
    except Exception as e:
        print(f"❌ 테이블 '{table_name}' 데이터 조회 실패: {e}")
        return [], []

def get_table_stats(engine, table_name):
    """테이블 통계 정보"""
    try:
        with engine.connect() as conn:
            # 행 개수
            count_query = text(f"SELECT COUNT(*) FROM `{table_name}`")
            row_count = conn.execute(count_query).scalar()
            
            if RDS_CONFIG['engine_type'] == 'mysql':
                # 테이블 크기 (MySQL)
                size_query = text(f"""
                    SELECT 
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'size_mb'
                    FROM information_schema.TABLES 
                    WHERE table_schema = '{RDS_CONFIG['database']}' 
                    AND table_name = '{table_name}'
                """)
                size_result = conn.execute(size_query).scalar()
                table_size = f"{size_result} MB" if size_result else "N/A"
            else:
                # PostgreSQL의 경우 크기 계산이 복잡하므로 생략
                table_size = "N/A"
            
            return {
                'row_count': row_count,
                'size': table_size
            }
    except Exception as e:
        print(f"❌ 테이블 '{table_name}' 통계 조회 실패: {e}")
        return {'row_count': 'N/A', 'size': 'N/A'}

def print_table_structure(table_name, structure):
    """테이블 구조 예쁘게 출력"""
    print(f"\n{'='*80}")
    print(f"📋 테이블: {table_name}")
    print(f"{'='*80}")
    
    # 컬럼 정보
    if structure and 'columns' in structure:
        print(f"\n📊 컬럼 정보:")
        
        # tabulate가 없는 경우를 대비한 수동 테이블
        try:
            df = pd.DataFrame(structure['columns'])
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
        except:
            # 수동으로 테이블 출력
            print(f"{'Column':<20} {'Type':<20} {'Null':<8} {'Key':<8} {'Default':<15}")
            print("-" * 80)
            for col in structure['columns']:
                print(f"{col.get('Column', ''):<20} {col.get('Type', ''):<20} {col.get('Null', ''):<8} {col.get('Key', ''):<8} {str(col.get('Default', '')):<15}")
    
    # 외래키 정보
    if structure and 'foreign_keys' in structure and structure['foreign_keys']:
        print(f"\n🔗 외래키:")
        for fk in structure['foreign_keys']:
            if len(fk) >= 3:
                print(f"  - {fk[0]} → {fk[1]}.{fk[2]}")
    
    # MySQL 전용 정보
    if structure and 'indexes' in structure:
        print(f"\n🔍 인덱스:")
        for idx_name, idx_info in structure['indexes'].items():
            unique_str = " (UNIQUE)" if idx_info['unique'] else ""
            print(f"  - {idx_name}: {', '.join(idx_info['columns'])}{unique_str}")
    
    if structure and 'table_info' in structure and structure['table_info']:
        info = structure['table_info']
        print(f"\n⚙️  테이블 정보:")
        if len(info) >= 2:
            print(f"  - 엔진: {info[1]}")
        if len(info) >= 3:
            print(f"  - 콜레이션: {info[2]}")

def print_table_data(table_name, columns, rows):
    """테이블 샘플 데이터 출력"""
    if not rows:
        print(f"\n📝 샘플 데이터: 데이터가 없습니다.")
        return
    
    print(f"\n📝 샘플 데이터 (최대 5행):")
    try:
        # pandas로 예쁘게 출력
        df = pd.DataFrame(rows, columns=columns)
        print(df.to_string(index=False, max_cols=10, max_colwidth=20))
    except:
        # 수동 출력
        print(" | ".join([str(col)[:15] for col in columns]))
        print("-" * (len(columns) * 17))
        for row in rows[:5]:
            print(" | ".join([str(val)[:15] if val is not None else 'NULL' for val in row]))

def show_database_overview(engine, tables):
    """데이터베이스 전체 개요"""
    print(f"\n🏛️  데이터베이스 개요: {RDS_CONFIG['database']}")
    print(f"📊 엔진: {RDS_CONFIG['engine_type'].upper()}")
    print(f"🔗 호스트: {RDS_CONFIG['host']}")
    print(f"📋 총 테이블 수: {len(tables)}")
    
    if tables:
        print(f"\n📚 테이블 목록:")
        for i, table in enumerate(tables, 1):
            stats = get_table_stats(engine, table)
            print(f"  {i:2d}. {table:<20} ({stats['row_count']} rows, {stats['size']})")

def main():
    """메인 함수"""
    print("🚀 RDS 테이블 구조 조회 시작!")
    print("=" * 80)
    
    # 연결 정보 출력
    print(f"🔗 연결 정보:")
    print(f"  - 호스트: {RDS_CONFIG['host']}")
    print(f"  - 데이터베이스: {RDS_CONFIG['database']}")
    print(f"  - 엔진: {RDS_CONFIG['engine_type']}")
    
    # 데이터베이스 연결
    engine = create_connection()
    if not engine:
        return
    
    print("✅ 데이터베이스 연결 성공!")
    
    # 모든 테이블 조회
    tables = get_all_tables(engine)
    if not tables:
        print("❌ 테이블이 없거나 조회할 수 없습니다.")
        return
    
    # 데이터베이스 개요
    show_database_overview(engine, tables)
    
    # 각 테이블 상세 정보
    for table_name in tables:
        # 테이블 구조
        if RDS_CONFIG['engine_type'] == 'mysql':
            structure = get_table_structure_mysql(engine, table_name)
        else:
            structure = get_table_structure_postgresql(engine, table_name)
        
        print_table_structure(table_name, structure)
        
        # 테이블 통계
        stats = get_table_stats(engine, table_name)
        print(f"\n📈 통계: {stats['row_count']}행, 크기: {stats['size']}")
        
        # 샘플 데이터
        columns, rows = get_table_data_sample(engine, table_name)
        print_table_data(table_name, columns, rows)
    
    print(f"\n🎉 모든 테이블 조회 완료! (총 {len(tables)}개)")

def quick_connection_test():
    """빠른 연결 테스트"""
    print("🧪 빠른 연결 테스트...")
    
    # 여기에 직접 연결 정보 입력 가능
    HOST = "ella-nxtclass-mysql.cj24wem202yj.us-east-1.rds.amazonaws.com"
    DATABASE = "nxtclass"  # 올바른 데이터베이스 이름
    USERNAME = "admin"
    PASSWORD = input("비밀번호를 입력하세요: ")
    
    RDS_CONFIG.update({
        'host': HOST,
        'database': DATABASE,
        'username': USERNAME,
        'password': PASSWORD
    })
    
    main()

if __name__ == "__main__":
    # 환경변수가 설정되어 있으면 바로 실행
    if RDS_CONFIG['password'] != 'your_password':
        main()
    else:
        # 아니면 대화형으로 연결 정보 입력
        quick_connection_test()

# ============================================================
# 🔧 패키지 설치 (선택사항):
# pip install tabulate  # 테이블을 더 예쁘게 출력
# ============================================================