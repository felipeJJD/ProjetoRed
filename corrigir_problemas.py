import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Configuração do banco de dados
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

def get_db_connection():
    """Obtém uma conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fix_orphan_records():
    """
    Corrige registros órfãos no banco de dados, fazendo-os apontar
    para números de WhatsApp válidos
    """
    print("\n=== CORREÇÃO DE REGISTROS ÓRFÃOS ===")
    
    with get_db_connection() as conn:
        # Identificar registros órfãos
        orphans = conn.execute('''
            SELECT rl.id, rl.number_id, cl.user_id
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE wn.id IS NULL
        ''').fetchall()
        
        if not orphans:
            print("✅ Nenhum registro órfão encontrado. Banco de dados consistente!")
            return 0
        
        print(f"🔍 Encontrados {len(orphans)} registros órfãos para correção")
        fixed_count = 0
        removed_count = 0
        
        # Para cada registro órfão, encontrar um número válido do mesmo usuário
        for orphan in orphans:
            user_id = orphan['user_id']
            
            # Buscar um número válido para este usuário
            valid_number = conn.execute('''
                SELECT id FROM whatsapp_numbers 
                WHERE user_id = ? 
                LIMIT 1
            ''', (user_id,)).fetchone()
            
            if valid_number:
                # Atualizar o registro para apontar para um número válido
                conn.execute('''
                    UPDATE redirect_logs
                    SET number_id = ?
                    WHERE id = ?
                ''', (valid_number['id'], orphan['id']))
                fixed_count += 1
                print(f"  ✓ Corrigido: log ID {orphan['id']} → número ID {valid_number['id']}")
            else:
                # Se não houver um número válido para este usuário, remover o registro
                conn.execute('DELETE FROM redirect_logs WHERE id = ?', (orphan['id'],))
                removed_count += 1
                print(f"  ✗ Removido: log ID {orphan['id']} (sem número válido disponível)")
        
        conn.commit()
        print(f"\n✅ Conclusão: {fixed_count} registros corrigidos, {removed_count} registros removidos")
        return fixed_count + removed_count

def check_specific_dates(start_date, end_date):
    """
    Verifica e corrige inconsistências para um período de datas específico
    """
    print(f"\n=== VERIFICAÇÃO DE CONSISTÊNCIA: {start_date} a {end_date} ===")
    
    with get_db_connection() as conn:
        # Obter todos os usuários
        users = conn.execute('SELECT id, username FROM users').fetchall()
        
        for user in users:
            user_id = user['id']
            username = user['username']
            print(f"\n>> Verificando dados para usuário: {username} (ID: {user_id})")
            
            # Primeiro, verificar pela consulta básica (sem JOIN em whatsapp_numbers)
            basic_query = '''
                SELECT COUNT(*) as total
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE cl.user_id = ? 
                  AND date(rl.redirect_time) >= date(?)
                  AND date(rl.redirect_time) <= date(?)
            '''
            
            # Depois, verificar com JOIN em whatsapp_numbers (como na consulta de atividades recentes)
            join_query = '''
                SELECT COUNT(*) as total
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                JOIN whatsapp_numbers wn ON rl.number_id = wn.id
                WHERE cl.user_id = ? 
                  AND date(rl.redirect_time) >= date(?)
                  AND date(rl.redirect_time) <= date(?)
            '''
            
            params = [user_id, start_date, end_date]
            
            basic_total = conn.execute(basic_query, params).fetchone()['total']
            join_total = conn.execute(join_query, params).fetchone()['total']
            
            print(f"  - Total básico (sem JOIN em números): {basic_total}")
            print(f"  - Total com JOIN em números: {join_total}")
            
            # Se houver discrepância, corrigir os registros
            if basic_total != join_total:
                print(f"  ⚠️ DISCREPÂNCIA DETECTADA: {basic_total} vs {join_total}")
                
                # Identificar registros problemáticos
                orphan_query = '''
                    SELECT rl.id, rl.number_id
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
                    WHERE cl.user_id = ? 
                      AND date(rl.redirect_time) >= date(?)
                      AND date(rl.redirect_time) <= date(?)
                      AND wn.id IS NULL
                '''
                
                orphans = conn.execute(orphan_query, params).fetchall()
                
                if orphans:
                    print(f"  🔍 Encontrados {len(orphans)} registros problemáticos")
                    
                    # Procurar um número válido para este usuário
                    valid_number = conn.execute('''
                        SELECT id FROM whatsapp_numbers 
                        WHERE user_id = ? 
                        LIMIT 1
                    ''', (user_id,)).fetchone()
                    
                    if valid_number:
                        # Corrigir todos os registros
                        for orphan in orphans:
                            conn.execute('''
                                UPDATE redirect_logs
                                SET number_id = ?
                                WHERE id = ?
                            ''', (valid_number['id'], orphan['id']))
                            print(f"    ✓ Corrigido: log ID {orphan['id']} → número ID {valid_number['id']}")
                    else:
                        # Se não houver número válido, remover os registros
                        for orphan in orphans:
                            conn.execute('DELETE FROM redirect_logs WHERE id = ?', (orphan['id'],))
                            print(f"    ✗ Removido: log ID {orphan['id']} (sem número válido)")
                    
                    conn.commit()
                    
                    # Verificar novamente após correção
                    basic_total = conn.execute(basic_query, params).fetchone()['total']
                    join_total = conn.execute(join_query, params).fetchone()['total']
                    
                    if basic_total == join_total:
                        print(f"  ✅ CORREÇÃO BEM-SUCEDIDA: Agora ambas as consultas retornam {basic_total}")
                    else:
                        print(f"  ❌ AINDA HÁ DISCREPÂNCIA: {basic_total} vs {join_total}")
                else:
                    print("  ❓ Não foram encontrados registros órfãos específicos para este período")
            else:
                print("  ✅ Dados consistentes para este usuário e período")

if __name__ == "__main__":
    print("\n===== FERRAMENTA DE CORREÇÃO DE INCONSISTÊNCIAS =====")
    print("Esta ferramenta corrige registros problemáticos no banco de dados")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ ERRO: Banco de dados não encontrado em {DATABASE_PATH}")
        sys.exit(1)
    
    # Corrigir todos os registros órfãos primeiro
    print("\nEtapa 1: Correção geral de registros órfãos")
    num_fixed = fix_orphan_records()
    
    # Verificar especificamente o período de 15 a 15
    print("\nEtapa 2: Verificação do período específico de 15 a 15")
    
    # Determinar o período de 15 a 15 com base na data atual
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Verificar especificamente o período mencionado (15 a 15)
    start_date = "2023-03-15"  # Use a data específica mencionada pelo usuário
    end_date = "2023-04-15"    # Use a data específica mencionada pelo usuário
    
    check_specific_dates(start_date, end_date)
    
    # Se o usuário mencionou especificamente o dia 15, testamos também o período atual
    if hoje.day >= 15:
        # Estamos na segunda metade do mês
        current_start = f"{ano_atual}-{mes_atual:02d}-15"
        current_end = hoje.strftime("%Y-%m-%d")
    else:
        # Estamos na primeira metade do mês
        mes_anterior = 12 if mes_atual == 1 else mes_atual - 1
        ano_anterior = ano_atual - 1 if mes_atual == 1 else ano_atual
        current_start = f"{ano_anterior}-{mes_anterior:02d}-15"
        current_end = f"{ano_atual}-{mes_atual:02d}-14"
    
    print(f"\nEtapa 3: Verificação do período atual de 15 a 15 ({current_start} a {current_end})")
    check_specific_dates(current_start, current_end)
    
    print("\n===== CONCLUSÃO =====")
    print("Verificação e correção concluídas. O sistema deve estar consistente agora.")
    print("Se o problema persistir, verifique o código das consultas no frontend e backend") 