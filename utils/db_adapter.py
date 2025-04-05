import psycopg2
import logging
from psycopg2.extras import RealDictCursor
from config.settings import active_config

class DBAdapter:
    """
    Adaptador de banco de dados para PostgreSQL
    """
    def __init__(self):
        self.connection = None
        self.app = None
        self.use_postgres = True  # Definir como True pois o sistema agora usa apenas PostgreSQL
        
    def init_app(self, app):
        """
        Inicializa o adaptador com a aplicação Flask
        """
        self.app = app
        self.use_postgres = True  # Garantir que sempre seja True
        logging.info("Adaptador de banco de dados inicializado com a aplicação Flask (PostgreSQL)")
    
    def init_db(self):
        """
        Inicializa o banco de dados chamando o script init_database
        """
        from utils.init_db import init_database
        init_database()
        
    def get_db_connection(self):
        """
        Retorna uma conexão com o banco de dados PostgreSQL.
        """
        try:
            connection = psycopg2.connect(
                dbname=active_config.POSTGRES_DB,
                user=active_config.POSTGRES_USER,
                password=active_config.POSTGRES_PASSWORD,
                host=active_config.POSTGRES_HOST,
                port=active_config.POSTGRES_PORT,
                cursor_factory=RealDictCursor
            )
            logging.info(f"Conectado com sucesso ao PostgreSQL no host: {active_config.POSTGRES_HOST}")
            return connection
        except Exception as e:
            logging.error(f"Erro ao conectar ao PostgreSQL: {str(e)}")
            logging.error(f"Configuração PostgreSQL: host={active_config.POSTGRES_HOST}, port={active_config.POSTGRES_PORT}, dbname={active_config.POSTGRES_DB}, user={active_config.POSTGRES_USER}")
            raise
    
    def execute_query(self, query, params=None, fetch_all=False, commit=False):
        """
        Executa uma consulta no banco de dados e retorna os resultados.
        
        Args:
            query (str): Consulta SQL a ser executada
            params (tuple, optional): Parâmetros para a consulta. Defaults to None.
            fetch_all (bool, optional): Se True, retorna todos os resultados. Defaults to False.
            commit (bool, optional): Se True, faz commit da transação. Defaults to False.
            
        Returns:
            list: Resultados da consulta para SELECT ou queries com RETURNING
            None: Para operações de modificação como UPDATE/DELETE/INSERT sem RETURNING
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Executar a consulta
            cursor.execute(query, params)
            
            # Verificar o tipo de operação SQL
            operation = query.strip().upper().split()[0]
            has_returning = 'RETURNING' in query.upper()
            
            # Processar resultados apenas para SELECT ou queries com RETURNING
            result = None
            if operation == 'SELECT' or has_returning:
                if fetch_all:
                    result = cursor.fetchall()
                else:
                    # Verificar se há resultados antes de chamar fetchone()
                    if cursor.rowcount > 0:
                        result = cursor.fetchone()
            elif operation in ['UPDATE', 'DELETE', 'INSERT'] and not has_returning:
                # Para operações de modificação sem RETURNING, apenas retornar o número de linhas afetadas
                result = cursor.rowcount
                
            # Commit se necessário
            if commit:
                conn.commit()
                
            return result
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao executar consulta: {str(e)}")
            logging.error(f"Query: {query}")
            logging.error(f"Params: {params}")
            raise
        finally:
            conn.close()
    
    def get_placeholder(self):
        """
        Retorna o placeholder correto para o banco de dados atual.
        
        Returns:
            str: '%s' para PostgreSQL, '?' para SQLite
        """
        return '%s'  # Sempre retorna %s para PostgreSQL
    
    def get_current_timestamp(self):
        """
        Retorna a expressão SQL para o timestamp atual no formato correto.
        
        Returns:
            str: Expressão SQL para o timestamp atual
        """
        return 'CURRENT_TIMESTAMP'  # Para PostgreSQL
    
    def get_last_insert_id(self, table_name):
        """
        Retorna o ID do último registro inserido em uma tabela no PostgreSQL.
        
        Args:
            table_name (str): Nome da tabela
            
        Returns:
            int: ID do último registro inserido
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT currval(pg_get_serial_sequence('{table_name}', 'id'))")
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def create_tables(self):
        """
        Cria as tabelas necessárias no banco de dados PostgreSQL se não existirem.
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Tabelas para PostgreSQL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    max_numbers INTEGER DEFAULT 1,
                    max_links INTEGER DEFAULT 3,
                    price NUMERIC(10, 2) DEFAULT 0.00
                )
            ''')
            
            # Adicione aqui as demais tabelas conforme necessário
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao criar tabelas: {str(e)}")
        finally:
            conn.close()

# Instanciar o adaptador para uso em toda a aplicação
db_adapter = DBAdapter()
