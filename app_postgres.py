"""
Módulo para migração e adaptação do SQLite para PostgreSQL 
Implementa funções para migrar dados e adaptar consultas do SQLite para PostgreSQL
"""
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import time
from db_config import get_sqlite_connection, get_postgres_connection, close_connections

def verificar_conexao_postgres():
    """Verifica se conseguimos conectar ao PostgreSQL"""
    print("\n===== Verificando conexão com PostgreSQL =====")
    try:
        conn = get_postgres_connection()
        if conn:
            print("✅ Conexão estabelecida com sucesso!")
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            versao = cursor.fetchone()
            print(f"📊 Versão do PostgreSQL: {versao['version']}")
            close_connections(pg_conn=conn)
            return True
        else:
            print("❌ Falha ao conectar com PostgreSQL")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {str(e)}")
        return False

def verificar_tabelas_postgres():
    """Verifica as tabelas existentes no PostgreSQL e retorna lista de tabelas"""
    print("\n===== Verificando tabelas no PostgreSQL =====")
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Consultar tabelas existentes
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tabelas = [row['table_name'] for row in cursor.fetchall()]
        
        print(f"📋 Tabelas encontradas ({len(tabelas)}):")
        for tabela in tabelas:
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM {tabela}
            """)
            count = cursor.fetchone()['count']
            print(f"  - {tabela}: {count} registros")
        
        close_connections(pg_conn=conn)
        return tabelas
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas no PostgreSQL: {str(e)}")
        return []

def verificar_tabelas_sqlite():
    """Verifica as tabelas existentes no SQLite e retorna lista de tabelas"""
    print("\n===== Verificando tabelas no SQLite =====")
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Consultar tabelas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        
        tabelas = [row['name'] for row in cursor.fetchall()]
        
        print(f"📋 Tabelas encontradas ({len(tabelas)}):")
        for tabela in tabelas:
            cursor.execute(f"SELECT COUNT(*) as count FROM {tabela}")
            count = cursor.fetchone()['count']
            print(f"  - {tabela}: {count} registros")
        
        close_connections(sqlite_conn=conn)
        return tabelas
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas no SQLite: {str(e)}")
        return []

def criar_estrutura_postgres():
    """Cria ou atualiza a estrutura de tabelas no PostgreSQL"""
    print("\n===== Criando/atualizando estrutura no PostgreSQL =====")
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # 1. Tabela plans (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                max_numbers INTEGER NOT NULL,
                max_links INTEGER NOT NULL,
                description TEXT
            )
        """)
        
        # 2. Tabela users (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                fullname TEXT,
                plan_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)
        
        # 3. Tabela whatsapp_numbers (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                redirect_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 4. Tabela custom_links (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_links (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                link_name TEXT NOT NULL,
                custom_message TEXT,
                is_active INTEGER DEFAULT 1,
                click_count INTEGER DEFAULT 0,
                prefix INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 5. Tabela redirect_logs (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS redirect_logs (
                id SERIAL PRIMARY KEY,
                link_id INTEGER NOT NULL,
                number_id INTEGER NOT NULL,
                redirect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                message TEXT,
                city TEXT,
                region TEXT,
                country TEXT,
                latitude FLOAT,
                longitude FLOAT,
                FOREIGN KEY (link_id) REFERENCES custom_links(id),
                FOREIGN KEY (number_id) REFERENCES whatsapp_numbers(id)
            )
        """)
        
        # 6. Tabela ip_geolocation_cache (se não existir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ip_geolocation_cache (
                ip_address TEXT PRIMARY KEY,
                city TEXT,
                region TEXT,
                country TEXT,
                latitude FLOAT,
                longitude FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Criar índices para otimização
        # Índices na tabela redirect_logs
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_redirect_logs_link_id ON redirect_logs(link_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_redirect_logs_number_id ON redirect_logs(number_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_redirect_logs_time ON redirect_logs(redirect_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_redirect_logs_link_time ON redirect_logs(link_id, redirect_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_redirect_logs_ip ON redirect_logs(ip_address)")
        
        # Índices nas outras tabelas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_numbers_user ON whatsapp_numbers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_links_user ON custom_links(user_id)")
        
        conn.commit()
        print("✅ Estrutura criada/atualizada com sucesso!")
        close_connections(pg_conn=conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao criar estrutura no PostgreSQL: {str(e)}")
        if conn:
            conn.rollback()
            close_connections(pg_conn=conn)
        return False

def migrar_plans():
    """Migra os dados de planos do SQLite para o PostgreSQL"""
    print("\n===== Migrando tabela plans =====")
    try:
        sqlite_conn = get_sqlite_connection()
        pg_conn = get_postgres_connection()
        
        # Verificar se existem planos no SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plans'")
        if not sqlite_cursor.fetchone():
            print("⚠️ Tabela 'plans' não existe no SQLite. Criando planos padrão no PostgreSQL...")
            
            # Criar planos padrão diretamente no PostgreSQL
            pg_cursor = pg_conn.cursor()
            
            # Verificar se já existem planos no PostgreSQL
            pg_cursor.execute("SELECT COUNT(*) as count FROM plans")
            if pg_cursor.fetchone()['count'] == 0:
                # Inserir planos padrão
                pg_cursor.execute("""
                    INSERT INTO plans (name, max_numbers, max_links, description) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, ('basic', 2, 1, 'Plano Básico'))
                
                pg_cursor.execute("""
                    INSERT INTO plans (name, max_numbers, max_links, description) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, ('intermediary', 5, 5, 'Plano Intermediário'))
                
                pg_cursor.execute("""
                    INSERT INTO plans (name, max_numbers, max_links, description) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, ('advanced', 15, -1, 'Plano Avançado'))
                
                pg_cursor.execute("""
                    INSERT INTO plans (name, max_numbers, max_links, description) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, ('unlimited', -1, -1, 'Plano Ilimitado'))
                
                pg_conn.commit()
                print("✅ Planos padrão criados no PostgreSQL!")
            else:
                print("⚠️ Já existem planos no PostgreSQL. Pulando criação de planos padrão.")
        else:
            # Migrar planos do SQLite para PostgreSQL
            sqlite_cursor.execute("SELECT * FROM plans")
            plans = sqlite_cursor.fetchall()
            
            if plans:
                pg_cursor = pg_conn.cursor()
                for plan in plans:
                    # Converter para dicionário
                    plan_dict = dict(plan)
                    
                    # Inserir no PostgreSQL com tratamento para conflitos
                    pg_cursor.execute("""
                        INSERT INTO plans (id, name, max_numbers, max_links, description) 
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO UPDATE SET 
                            max_numbers = EXCLUDED.max_numbers,
                            max_links = EXCLUDED.max_links,
                            description = EXCLUDED.description
                    """, (
                        plan_dict['id'], 
                        plan_dict['name'], 
                        plan_dict['max_numbers'], 
                        plan_dict['max_links'], 
                        plan_dict.get('description')
                    ))
                
                pg_conn.commit()
                print(f"✅ Migrados {len(plans)} planos do SQLite para PostgreSQL!")
            else:
                print("⚠️ Não há planos no SQLite para migrar.")
        
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao migrar planos: {str(e)}")
        if pg_conn:
            pg_conn.rollback()
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return False

def migrar_users():
    """Migra os dados de usuários do SQLite para o PostgreSQL"""
    print("\n===== Migrando tabela users =====")
    try:
        sqlite_conn = get_sqlite_connection()
        pg_conn = get_postgres_connection()
        
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # Obter usuários do SQLite
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        if users:
            count_migrados = 0
            for user in users:
                # Converter para dicionário
                user_dict = dict(user)
                
                # Verificar se o plano existe
                plan_id = user_dict.get('plan_id', 1)  # Plano padrão = 1 (basic)
                
                # Tratar campo is_admin (não existe no SQLite)
                is_admin = False
                if user_dict.get('username') in ['pedro', 'felipe']:
                    is_admin = True
                
                # Inserir no PostgreSQL com tratamento para conflitos
                try:
                    pg_cursor.execute("""
                        INSERT INTO users (id, username, password, fullname, plan_id, created_at, is_admin) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username) DO UPDATE SET 
                            password = EXCLUDED.password,
                            fullname = EXCLUDED.fullname,
                            plan_id = EXCLUDED.plan_id,
                            is_admin = EXCLUDED.is_admin
                    """, (
                        user_dict['id'], 
                        user_dict['username'], 
                        user_dict['password'], 
                        user_dict.get('fullname'), 
                        plan_id,
                        user_dict.get('created_at', datetime.now()),
                        is_admin
                    ))
                    count_migrados += 1
                except Exception as e:
                    print(f"⚠️ Erro ao migrar usuário {user_dict['username']}: {str(e)}")
            
            pg_conn.commit()
            print(f"✅ Migrados {count_migrados} usuários do SQLite para PostgreSQL!")
        else:
            print("⚠️ Não há usuários no SQLite para migrar.")
        
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao migrar usuários: {str(e)}")
        if pg_conn:
            pg_conn.rollback()
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return False

def migrar_whatsapp_numbers():
    """Migra os números de WhatsApp do SQLite para o PostgreSQL"""
    print("\n===== Migrando tabela whatsapp_numbers =====")
    try:
        sqlite_conn = get_sqlite_connection()
        pg_conn = get_postgres_connection()
        
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # Obter números do SQLite
        sqlite_cursor.execute("SELECT * FROM whatsapp_numbers")
        numbers = sqlite_cursor.fetchall()
        
        if numbers:
            count_migrados = 0
            for number in numbers:
                # Converter para dicionário
                number_dict = dict(number)
                
                # Inserir no PostgreSQL com tratamento para conflitos
                try:
                    pg_cursor.execute("""
                        INSERT INTO whatsapp_numbers (
                            id, user_id, phone_number, description, 
                            is_active, last_used, redirect_count
                        ) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            user_id = EXCLUDED.user_id,
                            phone_number = EXCLUDED.phone_number,
                            description = EXCLUDED.description,
                            is_active = EXCLUDED.is_active,
                            last_used = EXCLUDED.last_used,
                            redirect_count = EXCLUDED.redirect_count
                    """, (
                        number_dict['id'], 
                        number_dict['user_id'], 
                        number_dict['phone_number'], 
                        number_dict.get('description'), 
                        number_dict.get('is_active', 1),
                        number_dict.get('last_used'),
                        number_dict.get('redirect_count', 0)
                    ))
                    count_migrados += 1
                except Exception as e:
                    print(f"⚠️ Erro ao migrar número {number_dict['phone_number']}: {str(e)}")
            
            pg_conn.commit()
            print(f"✅ Migrados {count_migrados} números do SQLite para PostgreSQL!")
        else:
            print("⚠️ Não há números no SQLite para migrar.")
        
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao migrar números: {str(e)}")
        if pg_conn:
            pg_conn.rollback()
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return False

def migrar_custom_links():
    """Migra os links personalizados do SQLite para o PostgreSQL"""
    print("\n===== Migrando tabela custom_links =====")
    try:
        sqlite_conn = get_sqlite_connection()
        pg_conn = get_postgres_connection()
        
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # Obter links do SQLite
        sqlite_cursor.execute("SELECT * FROM custom_links")
        links = sqlite_cursor.fetchall()
        
        if links:
            count_migrados = 0
            for link in links:
                # Converter para dicionário
                link_dict = dict(link)
                
                # Inserir no PostgreSQL com tratamento para conflitos
                try:
                    pg_cursor.execute("""
                        INSERT INTO custom_links (
                            id, user_id, link_name, custom_message, 
                            is_active, click_count, prefix
                        ) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            user_id = EXCLUDED.user_id,
                            link_name = EXCLUDED.link_name,
                            custom_message = EXCLUDED.custom_message,
                            is_active = EXCLUDED.is_active,
                            click_count = EXCLUDED.click_count,
                            prefix = EXCLUDED.prefix
                    """, (
                        link_dict['id'], 
                        link_dict['user_id'], 
                        link_dict['link_name'], 
                        link_dict.get('custom_message'), 
                        link_dict.get('is_active', 1),
                        link_dict.get('click_count', 0),
                        link_dict.get('prefix', 1)
                    ))
                    count_migrados += 1
                except Exception as e:
                    print(f"⚠️ Erro ao migrar link {link_dict['link_name']}: {str(e)}")
            
            pg_conn.commit()
            print(f"✅ Migrados {count_migrados} links do SQLite para PostgreSQL!")
        else:
            print("⚠️ Não há links no SQLite para migrar.")
        
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao migrar links: {str(e)}")
        if pg_conn:
            pg_conn.rollback()
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return False

def migrar_logs_redirecionamento(limite=100000, lote=1000):
    """
    Migra os logs de redirecionamento do SQLite para o PostgreSQL.
    
    Args:
        limite: Limite máximo de registros a migrar (0 = sem limite)
        lote: Quantidade de registros em cada lote
    """
    print(f"\n===== Migrando tabela redirect_logs (limite={limite}, lote={lote}) =====")
    
    try:
        sqlite_conn = get_sqlite_connection()
        pg_conn = get_postgres_connection()
        
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # Verificar último ID migrado no PostgreSQL
        pg_cursor.execute("SELECT MAX(id) as last_id FROM redirect_logs")
        result = pg_cursor.fetchone()
        ultimo_id_migrado = result['last_id'] if result and result['last_id'] else 0
        
        print(f"🔍 Último ID migrado: {ultimo_id_migrado}")
        
        # Contar registros a migrar
        sqlite_cursor.execute(f"SELECT COUNT(*) as count FROM redirect_logs WHERE id > {ultimo_id_migrado}")
        total_a_migrar = sqlite_cursor.fetchone()['count']
        
        if limite > 0 and total_a_migrar > limite:
            print(f"⚠️ Limitando migração a {limite} registros dos {total_a_migrar} disponíveis")
            total_a_migrar = limite
        
        print(f"📊 Total de registros a migrar: {total_a_migrar}")
        
        if total_a_migrar == 0:
            print("✅ Nenhum novo registro para migrar!")
            close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
            return True
        
        # Calcular número de lotes
        num_lotes = (total_a_migrar + lote - 1) // lote  # Arredondamento para cima
        
        total_migrados = 0
        inicio_migracao = time.time()
        
        for i in range(num_lotes):
            offset = i * lote
            limit_atual = min(lote, total_a_migrar - offset)
            
            print(f"\n📦 Processando lote {i+1}/{num_lotes} ({offset+1}-{offset+limit_atual} de {total_a_migrar})")
            inicio_lote = time.time()
            
            # Obter lote de logs do SQLite
            sqlite_cursor.execute(f"""
                SELECT * FROM redirect_logs 
                WHERE id > {ultimo_id_migrado} 
                ORDER BY id ASC
                LIMIT {limit_atual} OFFSET {offset}
            """)
            
            logs = sqlite_cursor.fetchall()
            count_lote = 0
            
            # Inserir cada log no PostgreSQL
            for log in logs:
                log_dict = dict(log)
                
                try:
                    pg_cursor.execute("""
                        INSERT INTO redirect_logs (
                            id, link_id, number_id, redirect_time, 
                            ip_address, user_agent
                        ) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        log_dict['id'], 
                        log_dict['link_id'], 
                        log_dict['number_id'], 
                        log_dict.get('redirect_time', datetime.now()), 
                        log_dict.get('ip_address'),
                        log_dict.get('user_agent')
                    ))
                    count_lote += 1
                except Exception as e:
                    print(f"⚠️ Erro ao migrar log ID {log_dict['id']}: {str(e)}")
            
            # Confirmar transação a cada lote
            pg_conn.commit()
            
            total_migrados += count_lote
            tempo_lote = time.time() - inicio_lote
            registros_por_segundo = count_lote / tempo_lote if tempo_lote > 0 else 0
            
            print(f"✅ Lote {i+1}: {count_lote} registros migrados em {tempo_lote:.2f}s ({registros_por_segundo:.2f} reg/s)")
            
            # Verificar se atingimos o limite
            if limite > 0 and total_migrados >= limite:
                break
        
        tempo_total = time.time() - inicio_migracao
        registros_por_segundo = total_migrados / tempo_total if tempo_total > 0 else 0
        
        print(f"\n🎉 Migração concluída! {total_migrados} registros migrados em {tempo_total:.2f}s ({registros_por_segundo:.2f} reg/s)")
        
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return True
    except Exception as e:
        print(f"❌ Erro ao migrar logs de redirecionamento: {str(e)}")
        if pg_conn:
            pg_conn.rollback()
        close_connections(sqlite_conn=sqlite_conn, pg_conn=pg_conn)
        return False

def executar_migracao_completa():
    """Executa a migração completa do SQLite para o PostgreSQL"""
    print("\n===== INICIANDO MIGRAÇÃO COMPLETA =====")
    print(f"📅 Data e hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar conexões
    if not verificar_conexao_postgres():
        print("❌ Não foi possível conectar ao PostgreSQL. Abortando migração.")
        return False
    
    # 1. Verificar tabelas
    tabelas_sqlite = verificar_tabelas_sqlite()
    tabelas_postgres = verificar_tabelas_postgres()
    
    # 2. Criar estrutura no PostgreSQL
    if not criar_estrutura_postgres():
        print("❌ Falha ao criar estrutura no PostgreSQL. Abortando migração.")
        return False
    
    # 3. Migrar dados de cada tabela
    if not migrar_plans():
        print("⚠️ Problema na migração de planos.")
    
    if not migrar_users():
        print("⚠️ Problema na migração de usuários.")
    
    if not migrar_whatsapp_numbers():
        print("⚠️ Problema na migração de números.")
    
    if not migrar_custom_links():
        print("⚠️ Problema na migração de links.")
    
    # 4. Migrar logs de redirecionamento (com limite para evitar sobrecarga)
    # Por padrão, limitamos a 100.000 registros por execução
    if not migrar_logs_redirecionamento(limite=100000, lote=1000):
        print("⚠️ Problema na migração de logs de redirecionamento.")
    
    print("\n✅ Migração concluída com sucesso!")
    return True

if __name__ == "__main__":
    # Executar migração completa quando o script for chamado diretamente
    executar_migracao_completa()
