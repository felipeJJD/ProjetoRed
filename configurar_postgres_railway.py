import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# URL de conexão do PostgreSQL
DB_URL = "postgresql://postgres:nsAgxYUGJuIRXTalVIdclsTDecKEsgpc@switchyard.proxy.rlwy.net:24583/railway"

def inicializar_db():
    """Cria as tabelas básicas no PostgreSQL"""
    try:
        # Conectar ao PostgreSQL
        print("Conectando ao PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("Conexão estabelecida!")
        
        # Criar tabela de usuários
        print("\nCriando tabela de usuários...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                fullname TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verificar se já existem usuários
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Criar usuários padrão se não existirem
        if user_count == 0:
            print("Criando usuários padrão...")
            from werkzeug.security import generate_password_hash
            
            # Usuário pedro
            cursor.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (%s, %s, %s)
            ''', ('pedro', generate_password_hash('Vera123'), 'Pedro Administrador'))
            
            # Usuário felipe
            cursor.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (%s, %s, %s)
            ''', ('felipe', generate_password_hash('123'), 'Felipe Administrador'))
        
        # Criar tabela de números de WhatsApp
        print("Criando tabela de números de WhatsApp...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Criar tabela de links personalizados
        print("Criando tabela de links personalizados...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_links (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                link_name TEXT NOT NULL,
                custom_message TEXT,
                is_active INTEGER DEFAULT 1,
                click_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, link_name)
            )
        ''')
        
        # Criar tabela de logs de redirecionamento
        print("Criando tabela de logs de redirecionamento...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS redirect_logs (
                id SERIAL PRIMARY KEY,
                link_id INTEGER NOT NULL,
                number_id INTEGER NOT NULL,
                redirect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (link_id) REFERENCES custom_links (id),
                FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id)
            )
        ''')
        
        # Verificar se as tabelas foram criadas
        print("\nVerificando tabelas criadas:")
        cursor.execute('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        ''')
        
        tabelas = cursor.fetchall()
        for tabela in tabelas:
            print(f"- {tabela[0]}")
        
        # Criar links padrão para cada usuário
        print("\nCriando links padrão...")
        cursor.execute('''
            INSERT INTO custom_links (user_id, link_name, custom_message)
            SELECT id, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...'
            FROM users
            WHERE NOT EXISTS (
                SELECT 1 FROM custom_links c WHERE c.user_id = users.id AND c.link_name = 'padrao'
            )
        ''')
        
        print("\n✅ Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro ao inicializar banco de dados: {e}")
        return False
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()
    
    return True

if __name__ == "__main__":
    print("=== Configuração do PostgreSQL no Railway ===\n")
    
    # Confirmar antes de prosseguir
    resposta = input("Isso irá criar as tabelas básicas no PostgreSQL. Continuar? (S/N): ")
    
    if resposta.upper() != "S":
        print("Operação cancelada.")
        sys.exit(0)
    
    # Inicializar banco de dados
    inicializar_db() 