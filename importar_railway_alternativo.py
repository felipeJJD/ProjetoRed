import os
import sys
import time
import json
import subprocess
import re
from urllib.parse import urlparse

def limpar_terminal():
    """Limpa o terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def preparar_script_sql(sql_file_path):
    """
    Lê o arquivo SQL e divide em comandos menores para facilitar a execução
    
    Args:
        sql_file_path: Caminho para o arquivo SQL
    
    Returns:
        Lista de comandos SQL
    """
    print(f"Lendo arquivo SQL: {sql_file_path}")
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Remover comentários SQL
        sql_content = re.sub(r'--.*?\n', '\n', sql_content)
        
        # Dividir por ponto e vírgula, mantendo apenas comandos não vazios
        commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
        
        print(f"Arquivo SQL lido com sucesso. Encontrados {len(commands)} comandos.")
        return commands
    
    except Exception as e:
        print(f"Erro ao ler arquivo SQL: {e}")
        return []

def salvar_comandos_separados(commands, output_path):
    """Salva os comandos em um arquivo texto para facilitar a execução manual"""
    with open(output_path, 'w', encoding='utf-8') as file:
        for i, cmd in enumerate(commands):
            file.write(f"-- Comando {i+1}\n")
            file.write(cmd)
            file.write(";\n\n")
    
    print(f"\nComandos SQL salvos em: {output_path}")

def exibir_instrucoes_railway(connection_url, commands_path):
    """Exibe instruções para executar os comandos no Railway"""
    print("\n" + "="*70)
    print("INSTRUÇÕES PARA IMPORTAR OS DADOS NO RAILWAY")
    print("="*70)
    
    # Extrair host e database da URL
    parsed_url = urlparse(connection_url)
    host = parsed_url.hostname or "seu-host"
    database = parsed_url.path.lstrip('/') or "railway"
    
    print("\n1. Acesse o painel do Railway e vá para a aba 'Data' do seu PostgreSQL")
    print("\n2. Use o Editor SQL disponível para executar os comandos manualmente")
    print("   - Cole cada comando do arquivo gerado e execute um por vez")
    print(f"   - Os comandos estão no arquivo: {commands_path}")
    
    print("\n3. Alternativamente, se tiver o PostgreSQL instalado localmente:")
    print(f"   psql {connection_url} -f {commands_path}")
    
    print("\n4. Após importar os dados, atualize seu app.py:")
    print("   - Descomente as importações de PostgreSQL")
    print("   - Altere USE_POSTGRES para True")
    print("   - Atualize DATABASE_URL com a URL fornecida pelo Railway")
    
    print("\n" + "="*70)

def extrair_tabelas_do_sql(sql_content):
    """Extrai os nomes de tabelas do conteúdo SQL para verificação"""
    create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)'
    return re.findall(create_table_pattern, sql_content, re.IGNORECASE)

def criar_script_verificacao(tabelas, output_path):
    """Cria um script SQL para verificar se as tabelas foram criadas corretamente"""
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write("-- Script para verificar se as tabelas foram criadas corretamente\n\n")
        
        # Consulta para listar todas as tabelas
        file.write("-- Listar todas as tabelas\n")
        file.write("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';\n\n")
        
        # Consultas para contar registros em cada tabela
        for tabela in tabelas:
            file.write(f"-- Contar registros na tabela {tabela}\n")
            file.write(f"SELECT '{tabela}' AS tabela, COUNT(*) AS registros FROM {tabela};\n\n")
        
        # Consulta para verificar os usuários
        if 'users' in tabelas:
            file.write("-- Verificar usuários\n")
            file.write("SELECT id, username, fullname FROM users;\n\n")
    
    print(f"\nScript de verificação gerado em: {output_path}")

if __name__ == "__main__":
    limpar_terminal()
    print("=== Preparar SQL para PostgreSQL no Railway ===\n")
    
    # Obter URL de conexão
    connection_url = input("Cole a URL de conexão do PostgreSQL (formato: postgresql://usuario:senha@host:porta/banco): ")
    
    # Validar URL básica
    if not connection_url.startswith("postgresql://"):
        print("Erro: A URL de conexão deve começar com 'postgresql://'")
        sys.exit(1)
    
    # Obter caminho do arquivo SQL
    default_export_dir = os.path.join(os.path.dirname(__file__), 'export')
    
    # Listar arquivos SQL disponíveis
    sql_files = []
    if os.path.exists(default_export_dir):
        sql_files = [f for f in os.listdir(default_export_dir) if f.endswith('.sql')]
    
    if sql_files:
        print("\nArquivos SQL encontrados:")
        for i, file in enumerate(sql_files):
            print(f"{i+1}. {file}")
        
        choice = input("\nEscolha o número do arquivo SQL ou digite um caminho personalizado: ")
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(sql_files):
                sql_file_path = os.path.join(default_export_dir, sql_files[index])
            else:
                sql_file_path = choice
        except:
            sql_file_path = choice
    else:
        sql_file_path = input("\nDigite o caminho completo para o arquivo SQL: ")
    
    # Verificar se o arquivo existe
    if not os.path.exists(sql_file_path):
        print(f"Erro: Arquivo SQL não encontrado: {sql_file_path}")
        sys.exit(1)
    
    # Ler arquivo SQL e dividir em comandos
    sql_commands = preparar_script_sql(sql_file_path)
    
    if not sql_commands:
        print("Erro: Não foi possível extrair comandos SQL do arquivo.")
        sys.exit(1)
    
    # Gerar nome para o arquivo de saída
    output_dir = os.path.dirname(sql_file_path)
    base_name = os.path.basename(sql_file_path).replace('.sql', '')
    commands_path = os.path.join(output_dir, f"{base_name}_formatado.sql")
    
    # Salvar comandos em arquivo formatado
    salvar_comandos_separados(sql_commands, commands_path)
    
    # Extrair tabelas para verificação
    with open(sql_file_path, 'r', encoding='utf-8') as file:
        sql_content = file.read()
    
    tabelas = extrair_tabelas_do_sql(sql_content)
    
    # Criar script de verificação
    verificacao_path = os.path.join(output_dir, f"{base_name}_verificacao.sql")
    criar_script_verificacao(tabelas, verificacao_path)
    
    # Exibir instruções para o usuário
    exibir_instrucoes_railway(connection_url, commands_path)
    
    print("\nProcesso concluído!")
    print(f"Agora você pode seguir as instruções acima para importar os dados no Railway.") 