import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

# Configuração SQLite
SQLITE_DATABASE = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

# Configuração PostgreSQL Railway
POSTGRES_CONFIG = {
    'dbname': 'railway',
    'user': 'postgres',
    'password': 'nsAgxYUGJuIRXTalVIdclsTDecKEsgpc',
    'host': 'postgres.railway.internal',
    'port': '5432'
}

# URL público para acesso externo
POSTGRES_PUBLIC_URL = 'postgresql://postgres:nsAgxYUGJuIRXTalVIdclsTDecKEsgpc@switchyard.proxy.rlwy.net:24583/railway'

# Inicialização do pool de conexões (valor None inicialmente)
pg_pool = None

def init_connection_pool():
    """Inicializa o pool de conexões PostgreSQL"""
    global pg_pool
    try:
        # Criação do pool de conexões usando a configuração padrão
        pg_pool = ThreadedConnectionPool(
            minconn=5,
            maxconn=20,
            dbname=POSTGRES_CONFIG['dbname'],
            user=POSTGRES_CONFIG['user'],
            password=POSTGRES_CONFIG['password'],
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG['port'],
            cursor_factory=RealDictCursor
        )
        print("Pool de conexões PostgreSQL inicializado com sucesso")
        return True
    except Exception as e:
        print(f"Erro ao inicializar pool de conexões PostgreSQL: {e}")
        # Tentar inicializar com URL pública
        try:
            pg_pool = ThreadedConnectionPool(
                minconn=3,
                maxconn=10,
                dsn=POSTGRES_PUBLIC_URL,
                cursor_factory=RealDictCursor
            )
            print("Pool de conexões PostgreSQL (URL pública) inicializado com sucesso")
            return True
        except Exception as e2:
            print(f"Erro ao inicializar pool com URL pública: {e2}")
            return False

def get_sqlite_connection():
    """Retorna uma conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(SQLITE_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    """Retorna uma conexão com o banco de dados PostgreSQL do pool de conexões"""
    global pg_pool
    
    # Se o pool não foi inicializado, tenta inicializá-lo
    if pg_pool is None:
        init_connection_pool()
    
    # Se ainda for None, falhou a inicialização, tenta conexão direta
    if pg_pool is None:
        try:
            conn = psycopg2.connect(
                dbname=POSTGRES_CONFIG['dbname'],
                user=POSTGRES_CONFIG['user'],
                password=POSTGRES_CONFIG['password'],
                host=POSTGRES_CONFIG['host'],
                port=POSTGRES_CONFIG['port'],
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            print(f"Erro ao conectar ao PostgreSQL: {e}")
            # Fallback para conexão pública (em caso de execução local)
            try:
                conn = psycopg2.connect(POSTGRES_PUBLIC_URL, cursor_factory=RealDictCursor)
                return conn
            except Exception as e:
                print(f"Erro ao conectar usando URL pública: {e}")
                return None
    
    # Obtém uma conexão do pool
    try:
        return pg_pool.getconn()
    except Exception as e:
        print(f"Erro ao obter conexão do pool: {e}")
        return None

def close_connections(sqlite_conn=None, pg_conn=None):
    """Fecha conexões com os bancos de dados"""
    if sqlite_conn:
        try:
            sqlite_conn.close()
        except Exception as e:
            print(f"Erro ao fechar conexão SQLite: {e}")
    
    if pg_conn:
        try:
            # Se temos um pool, devolvemos a conexão ao pool em vez de fechá-la
            if pg_pool is not None:
                pg_pool.putconn(pg_conn)
            else:
                pg_conn.close()
        except Exception as e:
            print(f"Erro ao fechar conexão PostgreSQL: {e}")

def shutdown_pool():
    """Encerra o pool de conexões ao finalizar a aplicação"""
    global pg_pool
    if pg_pool is not None:
        pg_pool.closeall()
        print("Pool de conexões PostgreSQL encerrado")
