import sqlite3
import os
import shutil
import datetime

# Definir caminhos
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB = os.path.join(CURRENT_DIR, '..', 'ProjetoRed', 'instance', 'whatsapp_redirect.db')
TARGET_DB = os.path.join(CURRENT_DIR, 'instance', 'whatsapp_redirect.db')
BACKUP_DB = os.path.join(CURRENT_DIR, 'instance_backup', 'whatsapp_redirect.db')

def criar_backup():
    """Criar um backup adicional com timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(CURRENT_DIR, f'backup_{timestamp}.db')
    
    print(f"\n=== Criando backup adicional: {backup_path} ===")
    try:
        shutil.copy2(TARGET_DB, backup_path)
        print(f"✅ Backup criado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {str(e)}")
        return False

def migrar_dados():
    """Migrar dados do banco de origem para o banco de destino"""
    print("\n=== MIGRAÇÃO DE BANCO DE DADOS ===")
    print(f"Origem: {SOURCE_DB}")
    print(f"Destino: {TARGET_DB}")
    print(f"Backup: {BACKUP_DB}")
    
    # Verificar se os arquivos existem
    if not os.path.exists(SOURCE_DB):
        print(f"❌ Banco de dados de origem não encontrado: {SOURCE_DB}")
        return False
    
    if not os.path.exists(TARGET_DB):
        print(f"❌ Banco de dados de destino não encontrado: {TARGET_DB}")
        return False
    
    if not os.path.exists(BACKUP_DB):
        print(f"⚠️ Aviso: Backup não encontrado: {BACKUP_DB}")
        
    # Criar backup com timestamp antes de prosseguir
    if not criar_backup():
        print("❌ Falha ao criar backup, operação cancelada!")
        return False
    
    try:
        # Conectar aos bancos de dados
        source_conn = sqlite3.connect(SOURCE_DB)
        source_conn.row_factory = sqlite3.Row
        target_conn = sqlite3.connect(TARGET_DB)
        target_conn.row_factory = sqlite3.Row
        
        # Obter tabelas do banco de origem
        source_cursor = source_conn.cursor()
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        source_tables = source_cursor.fetchall()
        
        print(f"\n=== Tabelas encontradas no banco de origem ===")
        for table in source_tables:
            table_name = table['name']
            if table_name.startswith('sqlite_'):
                continue
            
            # Contar registros na origem
            source_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            source_count = source_cursor.fetchone()['count']
            
            # Contar registros no destino
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            target_count = target_cursor.fetchone()['count']
            
            print(f"  - {table_name}: {source_count} registros na origem, {target_count} registros no destino")
        
        print("\n=== Confirmação de migração ===")
        resposta = input("Deseja copiar o banco de dados da origem para o destino? (SIM/não): ")
        
        if resposta.upper() != "SIM":
            print("❌ Operação cancelada pelo usuário!")
            return False
        
        print("\n=== Copiando banco de dados ===")
        source_conn.close()
        target_conn.close()
        
        # Copiar o arquivo completo
        shutil.copy2(SOURCE_DB, TARGET_DB)
        print("✅ Banco de dados copiado com sucesso!")
        
        return True
    
    except Exception as e:
        print(f"❌ Erro durante a migração: {str(e)}")
        print("⚠️ Considere restaurar o backup manualmente se necessário.")
        return False

def atualizar_configuracoes_railway():
    """Atualizar configurações de Railway no app.py"""
    app_py_path = os.path.join(CURRENT_DIR, 'app.py')
    
    print("\n=== Atualizando configurações do Railway ===")
    
    try:
        with open(app_py_path, 'r') as file:
            content = file.read()
        
        # Localizar e substituir a configuração do servidor
        if "if __name__ == '__main__'" in content:
            new_config = """if __name__ == '__main__':
    # Inicializar verificação de consistência de dados
    with app.app_context():
        with get_db_connection() as conn:
            fix_data_inconsistencies(conn)
    
    # Configuração para desenvolvimento local
    # app.run(debug=True, port=5002)
    
    # Configuração para produção (Railway)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
"""
            
            # Substituir o bloco if __name__
            import re
            pattern = r"if __name__ == '__main__'[\s\S]*?app\.run\(.*?\)"
            updated_content = re.sub(pattern, new_config.strip(), content)
            
            # Salvar o arquivo modificado
            with open(app_py_path, 'w') as file:
                file.write(updated_content)
            
            print("✅ Configurações do Railway atualizadas com sucesso!")
            
            # Atualizar o Procfile
            procfile_path = os.path.join(CURRENT_DIR, 'Procfile')
            with open(procfile_path, 'w') as file:
                file.write("web: gunicorn app:app")
            
            print("✅ Procfile atualizado com sucesso!")
            
            return True
        else:
            print("❌ Não foi possível localizar o bloco de configuração do servidor!")
            return False
    
    except Exception as e:
        print(f"❌ Erro ao atualizar configurações: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== FERRAMENTA DE MIGRAÇÃO DE DADOS E CONFIGURAÇÕES =====")
    print("Esta ferramenta irá migrar dados do banco de dados de origem para o destino")
    print("e atualizar as configurações do Railway no arquivo app.py.")
    print("\n⚠️ ATENÇÃO: Certifique-se de ter feito backup antes de prosseguir.")
    
    # Migrar banco de dados
    if migrar_dados():
        # Atualizar configurações do Railway
        atualizar_configuracoes_railway()
        
        print("\n===== MIGRAÇÃO CONCLUÍDA =====")
        print("✅ Dados migrados e configurações atualizadas com sucesso!")
        print("⚠️ Lembre-se de verificar se tudo está funcionando corretamente.")
        print("📝 Se precisar restaurar o backup, use um dos seguintes arquivos:")
        print(f"   - {BACKUP_DB}")
        print(f"   - {os.path.join(CURRENT_DIR, 'backup_*.db')}")
    else:
        print("\n===== MIGRAÇÃO FALHOU =====")
        print("❌ Processo de migração não foi concluído com sucesso.")
        print("⚠️ Verifique os logs acima para mais detalhes.") 