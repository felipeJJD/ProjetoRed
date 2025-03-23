#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import argparse
from datetime import datetime, timedelta

# Configuração
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'whatsapp_redirect.db')

def get_db_connection():
    """Estabelece conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def test_data_consistency(conn, user_id, link_id='all', start_date=None, end_date=None):
    """
    Testa a consistência dos dados entre diferentes consultas
    """
    print("\n===== TESTE DE CONSISTÊNCIA DE DADOS =====")
    print(f"Usuário: {user_id}")
    print(f"Link: {link_id}")
    print(f"Data inicial: {start_date or 'Não especificada'}")
    print(f"Data final: {end_date or 'Não especificada'}")
    
    # Construir condições para filtros
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
    
    # Consulta 1: Total de logs de redirecionamento (Redirecionamentos brutos)
    query1 = f"""
        SELECT COUNT(*) as total
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        WHERE {link_condition} {date_condition}
    """
    
    # Consulta 2: Total de logs com junção em números (Usado em atividades recentes)
    query2 = f"""
        SELECT COUNT(*) as total
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        JOIN whatsapp_numbers wn ON rl.number_id = wn.id
        WHERE {link_condition} {date_condition}
    """
    
    # Consulta 3: Total por número, igual à consulta de "Acessos a Chip"
    query3 = f"""
        SELECT wn.id, wn.phone_number, COUNT(*) as count
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        JOIN whatsapp_numbers wn ON rl.number_id = wn.id
        WHERE {link_condition} {date_condition}
        GROUP BY wn.id, wn.phone_number
    """
    
    # Executar consultas
    total1 = conn.execute(query1, params).fetchone()['total']
    total2 = conn.execute(query2, params).fetchone()['total']
    
    number_stats = conn.execute(query3, params).fetchall()
    total3 = sum(row['count'] for row in number_stats)
    
    # Consulta 4: Contagem de acessos no mapa
    map_query = f"""
        SELECT COUNT(*) as total
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        WHERE {link_condition} {date_condition}
    """
    
    total_map = conn.execute(map_query, params).fetchone()['total']
    
    # Exibir resultados
    print("\n===== RESULTADOS =====")
    print(f"1. Total de redirecionamentos (logs brutos): {total1}")
    print(f"2. Total de redirecionamentos com números válidos: {total2}")
    print(f"3. Soma de acessos por chip: {total3}")
    print(f"4. Total de acessos no mapa: {total_map}")
    
    # Verificar consistência
    if total1 == total2 == total3 == total_map:
        print("\n✅ CONSISTÊNCIA CONFIRMADA: Todos os totais são idênticos")
    else:
        print("\n⚠️ INCONSISTÊNCIA DETECTADA:")
        if total1 != total2:
            print(f"  - Discrepância entre logs brutos e logs com números: {total1} vs {total2}")
        if total1 != total3:
            print(f"  - Discrepância entre logs brutos e soma por chips: {total1} vs {total3}")
        if total1 != total_map:
            print(f"  - Discrepância entre logs brutos e mapa: {total1} vs {total_map}")
        
        # Verificar se há registros orfãos (sem número válido)
        orphan_query = f"""
            SELECT rl.id, rl.number_id, rl.redirect_time 
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition} AND wn.id IS NULL
        """
        
        orphans = conn.execute(orphan_query, params).fetchall()
        if orphans:
            print(f"\n🔴 Encontrados {len(orphans)} registros órfãos (com números inválidos):")
            for orphan in orphans[:5]:  # Mostrar primeiros 5 como exemplo
                print(f"  - ID: {orphan['id']}, Number ID: {orphan['number_id']}, Data: {orphan['redirect_time']}")
            if len(orphans) > 5:
                print(f"  - ... e mais {len(orphans) - 5} registros")
    
    # Exibir detalhes dos acessos por chip
    print("\n===== DETALHE POR CHIP =====")
    for num in number_stats:
        print(f"Chip {num['phone_number']}: {num['count']} acessos")
    
    return {
        "total_logs": total1,
        "total_with_numbers": total2,
        "total_by_chip_sum": total3,
        "total_map": total_map,
        "orphan_count": len(orphans) if 'orphans' in locals() else 0,
        "chip_details": [dict(num) for num in number_stats]
    }

def fix_orphan_records(conn, user_id):
    """
    Corrige registros órfãos que apontam para números de WhatsApp inexistentes
    """
    print("\n===== CORREÇÃO DE REGISTROS ÓRFÃOS =====")
    
    # Identificar registros órfãos
    orphan_query = """
        SELECT rl.id, rl.link_id, cl.user_id
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
        WHERE cl.user_id = ? AND wn.id IS NULL
    """
    
    orphans = conn.execute(orphan_query, [user_id]).fetchall()
    
    if not orphans:
        print("✅ Nenhum registro órfão encontrado!")
        return 0
    
    print(f"Encontrados {len(orphans)} registros órfãos.")
    print("Buscando números válidos para substituição...")
    
    # Para cada registro órfão, buscar um número válido do mesmo usuário
    fixed_count = 0
    for orphan in orphans:
        link_id = orphan['link_id']
        user_id = orphan['user_id']
        
        # Buscar um número válido deste usuário
        valid_number = conn.execute("""
            SELECT id FROM whatsapp_numbers 
            WHERE user_id = ? 
            LIMIT 1
        """, (user_id,)).fetchone()
        
        if valid_number:
            # Atualizar o registro para apontar para um número válido
            conn.execute("""
                UPDATE redirect_logs
                SET number_id = ?
                WHERE id = ?
            """, (valid_number['id'], orphan['id']))
            fixed_count += 1
        else:
            # Se não houver número válido, remover o registro
            conn.execute('DELETE FROM redirect_logs WHERE id = ?', (orphan['id'],))
            print(f"Removido registro ID {orphan['id']} (sem número válido disponível)")
    
    conn.commit()
    print(f"✅ Corrigidos {fixed_count} registros órfãos!")
    
    return fixed_count

def test_specific_date_range(conn, user_id, month=None, year=None):
    """
    Testa especificamente o período do dia 15 ao dia 15
    """
    print("\n===== TESTE DE PERÍODO ESPECÍFICO (15 a 15) =====")
    
    # Determinar o mês e ano a usar (padrão: mês atual)
    if not month or not year:
        current_date = datetime.now()
        month = month or current_date.month
        year = year or current_date.year
    
    # Criar datas de início e fim (15 do mês anterior ao 15 do mês atual)
    if month == 1:
        start_month, start_year = 12, year - 1
    else:
        start_month, start_year = month - 1, year
    
    start_date = f"{start_year}-{start_month:02d}-15"
    end_date = f"{year}-{month:02d}-15"
    
    print(f"Período a testar: {start_date} a {end_date}")
    
    # Executar o teste de consistência para este período
    results = test_data_consistency(conn, user_id, 'all', start_date, end_date)
    
    print("\n===== RESUMO DO TESTE 15 a 15 =====")
    print(f"Período: {start_date} a {end_date}")
    print(f"Total de acessos nos logs: {results['total_logs']}")
    print(f"Total na visão de 'Acessos a Chip': {results['total_by_chip_sum']}")
    print(f"Total no mapa: {results['total_map']}")
    
    return results
    
def main():
    parser = argparse.ArgumentParser(description='Teste de consistência de dados no sistema de redirecionamento')
    parser.add_argument('--user', type=int, default=1, help='ID do usuário (padrão: 1)')
    parser.add_argument('--link', default='all', help='ID do link (padrão: todos)')
    parser.add_argument('--fix', action='store_true', help='Corrigir registros órfãos')
    parser.add_argument('--start-date', help='Data inicial (formato: AAAA-MM-DD)')
    parser.add_argument('--end-date', help='Data final (formato: AAAA-MM-DD)')
    parser.add_argument('--test-15-to-15', action='store_true', help='Testar período de 15 a 15')
    parser.add_argument('--month', type=int, help='Mês para teste 15 a 15 (1-12)')
    parser.add_argument('--year', type=int, help='Ano para teste 15 a 15')
    
    args = parser.parse_args()
    
    try:
        with get_db_connection() as conn:
            print(f"Conectado ao banco de dados: {DB_PATH}")
            
            if args.fix:
                fix_orphan_records(conn, args.user)
            
            if args.test_15_to_15:
                test_specific_date_range(conn, args.user, args.month, args.year)
            else:
                test_data_consistency(conn, args.user, args.link, args.start_date, args.end_date)
                
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 