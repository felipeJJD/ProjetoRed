import logging
from utils.db_adapter import db_adapter


def init_database():
    """
    Inicializa o banco de dados criando todas as tabelas necessárias
    se elas ainda não existirem.
    """
    logging.info("Inicializando banco de dados...")
    
    try:
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Verificamos apenas se as tabelas existem, sem recriar (usando PostgreSQL)
        cursor.execute("SELECT to_regclass('public.users')")
        result = cursor.fetchone()
        users_exists = result and result['to_regclass'] is not None
        
        if not users_exists:
            logging.warning("A tabela de usuários não existe. Criando tabelas...")
            # Criar tabelas chamando o método de criação
            db_adapter.create_tables()
        else:
            logging.info("Tabelas já existem, verificando usuários...")
            
            # Verificar se o usuário de teste 'felipe' existe (PostgreSQL)
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('felipe',))
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
            if count == 0:
                logging.info("Criando usuário de teste 'felipe'...")
                from werkzeug.security import generate_password_hash
                # Usando hash para a senha '123'
                password_hash = generate_password_hash('123')
                
                cursor.execute(
                    "INSERT INTO users (username, password, plan_id) VALUES (%s, %s, %s)",
                    ('felipe', password_hash, 1)
                )
                logging.info("Usuário de teste 'felipe' criado com sucesso!")
        
        conn.commit()
        logging.info("Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro ao inicializar banco de dados: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Inicializar banco de dados
    init_database()
