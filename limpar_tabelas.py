import sqlite3
import os

# Caminho para o banco de dados
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

def limpar_tabelas():
    """Limpa os registros das tabelas principais"""
    print("\n===== LIMPANDO TABELAS DO BANCO DE DADOS =====")
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Limpar tabela de logs de redirecionamento
        cursor.execute("DELETE FROM redirect_logs")
        logs_removidos = cursor.rowcount
        print(f"✅ Tabela redirect_logs: {logs_removidos} registros removidos")
        
        # 2. Resetar contadores de cliques nos links
        cursor.execute("UPDATE custom_links SET click_count = 0")
        links_resetados = cursor.rowcount
        print(f"✅ Tabela custom_links: {links_resetados} contadores de cliques resetados")
        
        # 3. Resetar timestamp de último uso nos números
        cursor.execute("UPDATE whatsapp_numbers SET last_used = NULL")
        numeros_resetados = cursor.rowcount
        print(f"✅ Tabela whatsapp_numbers: {numeros_resetados} timestamps de último uso resetados")
        
        # Confirmar as alterações
        conn.commit()
        print("\n✅ Limpeza concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Confirmação antes de executar
    print("🚨 ATENÇÃO: Esta operação irá remover TODOS os registros de acessos/cliques e resetar contadores! 🚨")
    print("Esta ação NÃO PODE ser desfeita! Todos os dados de estatísticas serão perdidos.")
    
    resposta = input("\nDigite 'SIM' para confirmar a limpeza: ")
    
    if resposta.upper() == "SIM":
        limpar_tabelas()
    else:
        print("\n❌ Operação cancelada pelo usuário.") 