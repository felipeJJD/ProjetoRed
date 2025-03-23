import sqlite3
import os
import sys
from datetime import datetime, timedelta
import json

# Configuração do banco de dados
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

def get_db_connection():
    """Obtém uma conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def test_data_consistency(user_id, link_id='all', start_date=None, end_date=None):
    """
    Testa a consistência dos dados entre diferentes consultas
    para verificar se os totais são iguais
    """
    print(f"\n=== TESTE DE CONSISTÊNCIA DE DADOS ===")
    print(f"Parâmetros: user_id={user_id}, link_id={link_id}, start_date={start_date}, end_date={end_date}")
    
    # Construir condições SQL padronizadas
    link_condition = "cl.user_id = ?"
    params = [user_id]
    
    if link_id != 'all' and str(link_id).isdigit():
        link_condition += " AND cl.id = ?"
        params.append(int(link_id))
    
    # Adicionar condições de data se fornecidas
    date_condition = ""
    if start_date:
        date_condition += " AND date(rl.redirect_time) >= date(?)"
        params.append(start_date)
    if end_date:
        date_condition += " AND date(rl.redirect_time) <= date(?)"
        params.append(end_date)
    
    print(f"Condições SQL: link_condition={link_condition}, date_condition={date_condition}")
    print(f"Parâmetros SQL: {params}")
    
    with get_db_connection() as conn:
        # 1. Consulta básica (usada em redirect_logs)
        query1 = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
        '''
        
        # 2. Consulta com JOIN em whatsapp_numbers (usada em atividades recentes)
        query2 = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition}
        '''
        
        # 3. Consulta por chip (soma de todas as contagens por número)
        query3_base = f'''
            SELECT rl.number_id, COUNT(*) as count
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
            GROUP BY rl.number_id
        '''
        
        # Executar consultas e coletar resultados
        total1 = conn.execute(query1, params).fetchone()['total']
        total2 = conn.execute(query2, params).fetchone()['total']
        
        # Contagem por número e soma
        numbers_count = conn.execute(query3_base, params).fetchall()
        total3 = sum(row['count'] for row in numbers_count)
        
        # Verificar registros órfãos (logs que referenciam números que não existem mais)
        orphan_query = f'''
            SELECT rl.id, rl.number_id, rl.redirect_time 
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition} AND wn.id IS NULL
        '''
        
        orphans = list(conn.execute(orphan_query, params).fetchall())
        num_orphans = len(orphans)
        
        # Resultado detalhado das atividades recentes (para diagnóstico)
        recent_query = f'''
            SELECT 
                rl.id,
                rl.redirect_time,
                cl.link_name,
                rl.number_id,
                cl.user_id
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
            ORDER BY rl.redirect_time DESC
            LIMIT 20
        '''
        
        recent_logs = list(conn.execute(recent_query, params).fetchall())
        
        # Estatísticas dos números de telefone encontrados
        numbers_info = []
        for number_row in numbers_count:
            number_id = number_row['number_id']
            number_info = conn.execute(
                'SELECT id, phone_number, description FROM whatsapp_numbers WHERE id = ?',
                [number_id]
            ).fetchone()
            
            if number_info:
                numbers_info.append({
                    'id': number_id,
                    'phone': number_info['phone_number'],
                    'desc': number_info['description'],
                    'count': number_row['count']
                })
            else:
                numbers_info.append({
                    'id': number_id,
                    'phone': 'DESCONHECIDO (ÓRFÃO)',
                    'desc': 'Número excluído',
                    'count': number_row['count']
                })
        
        # Exibir resultados
        print("\n=== RESULTADOS DAS CONSULTAS ===")
        print(f"1. Total de registros (redirect_logs): {total1}")
        print(f"2. Total com JOIN em whatsapp_numbers: {total2}")
        print(f"3. Soma de contagens por número: {total3}")
        print(f"4. Registros órfãos encontrados: {num_orphans}")
        
        # Conclusão sobre consistência
        is_consistent = (total1 == total2 == total3)
        
        print("\n=== ANÁLISE DE CONSISTÊNCIA ===")
        if is_consistent:
            print("✅ DADOS CONSISTENTES: Todas as consultas retornam o mesmo total")
        else:
            print("❌ DADOS INCONSISTENTES: As consultas retornam totais diferentes")
            print(f"  - Total básico vs. com números: {total1} vs {total2} (diferença: {abs(total1-total2)})")
            print(f"  - Total básico vs. soma por chip: {total1} vs {total3} (diferença: {abs(total1-total3)})")
            
            if num_orphans > 0:
                print(f"\n🔴 PROBLEMA DETECTADO: {num_orphans} logs apontam para números de telefone inexistentes")
                for i, orphan in enumerate(orphans[:5]):  # Mostrar até 5 exemplos
                    orphan_time = orphan['redirect_time']
                    print(f"  - ID {orphan['id']}: número_id={orphan['number_id']}, data={orphan_time}")
                if len(orphans) > 5:
                    print(f"  - ... e mais {len(orphans) - 5} registros órfãos")
        
        print("\n=== ESTATÍSTICAS POR NÚMERO DE TELEFONE ===")
        for info in sorted(numbers_info, key=lambda x: x['count'], reverse=True):
            print(f"  - ID {info['id']}: {info['phone']} ({info['desc']}): {info['count']} registros")
        
        print("\n=== AMOSTRA DE LOGS RECENTES ===")
        for i, log in enumerate(recent_logs[:10]):  # Mostrar até 10 exemplos
            log_time = log['redirect_time']
            print(f"  - ID {log['id']}: link={log['link_name']}, número_id={log['number_id']}, data={log_time}")
        
        return {
            'consistent': is_consistent,
            'totals': {
                'basic_query': total1,
                'with_numbers': total2,
                'sum_by_number': total3
            },
            'orphans': num_orphans,
            'numbers_count': len(numbers_info)
        }

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

def test_specific_date_range():
    """Testa especificamente o período de 15 a 15"""
    # Pegar o mês atual
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Preparar as datas para o período de 15 a 15
    if hoje.day >= 15:
        # Estamos na segunda metade do mês, testar de 15 deste mês até hoje
        start_date = f"{ano_atual}-{mes_atual:02d}-15"
        end_date = hoje.strftime("%Y-%m-%d")
    else:
        # Estamos na primeira metade do mês, testar de 15 do mês passado até 14 deste mês
        mes_anterior = 12 if mes_atual == 1 else mes_atual - 1
        ano_anterior = ano_atual - 1 if mes_atual == 1 else ano_atual
        start_date = f"{ano_anterior}-{mes_anterior:02d}-15"
        end_date = f"{ano_atual}-{mes_atual:02d}-14"
    
    print(f"\n=== TESTE ESPECÍFICO: PERÍODO DE 15 A 15 ===")
    print(f"Período: {start_date} até {end_date}")
    
    # Testar para todos os usuários
    with get_db_connection() as conn:
        users = conn.execute('SELECT id, username FROM users').fetchall()
        
        for user in users:
            print(f"\n>> Testando para usuário: {user['username']} (ID: {user['id']})")
            
            # Testar para todos os links
            result_todos = test_data_consistency(user['id'], 'all', start_date, end_date)
            
            # Testar para links individuais
            links = conn.execute('SELECT id, link_name FROM custom_links WHERE user_id = ?', 
                               [user['id']]).fetchall()
            
            for link in links:
                print(f"\n>> Testando link: {link['link_name']} (ID: {link['id']})")
                result_link = test_data_consistency(user['id'], link['id'], start_date, end_date)

if __name__ == "__main__":
    print("\n===== SCRIPT DE TESTE DE CONSISTÊNCIA DE DADOS =====")
    print("Este script verifica discrepâncias entre consultas no banco de dados")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ ERRO: Banco de dados não encontrado em {DATABASE_PATH}")
        sys.exit(1)
    
    # Corrigir registros órfãos primeiro
    num_fixed = fix_orphan_records()
    
    # Se houve correções, testar novamente para ver se resolveu
    if num_fixed > 0:
        print("\n⚠️ Registros corrigidos. Verificando consistência novamente...")
    
    # Testar o período específico de 15 a 15
    test_specific_date_range() 