import os
import sqlite3
import sys
import traceback
import json
import datetime
import re

# Este script prepara os dados do SQLite em um formato que pode ser importado no PostgreSQL do Railway

class CustomEncoder(json.JSONEncoder):
    """Encoder personalizado para converter tipos não JSON-serializáveis"""
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, sqlite3.Row):
            return dict(obj)
        return super().default(obj)

def get_sqlite_connection(db_path):
    """Conecta ao banco SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_table_data(conn, table_name):
    """Extrai dados de uma tabela específica"""
    print(f"Extraindo dados da tabela: {table_name}")
    
    # Obter informações das colunas
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    
    # Imprimir informações das colunas
    print(f"  Colunas da tabela {table_name}:")
    for col in columns_info:
        col_name = col['name']
        col_type = col['type']
        print(f"    - {col_name} ({col_type})")
    
    # Obter dados da tabela
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Converter para formato serializável
    serializable_rows = []
    for row in rows:
        # Converter cada Row para dict explicitamente
        row_dict = {col['name']: row[col['name']] for col in columns_info}
        serializable_rows.append(row_dict)
    
    print(f"  Total de registros: {len(serializable_rows)}")
    return {
        'columns': [{'name': col['name'], 'type': col['type']} for col in columns_info],
        'rows': serializable_rows
    }

def export_sqlite_to_json(sqlite_db_path, output_json_path):
    """Exporta todo o banco SQLite para um arquivo JSON"""
    try:
        conn = get_sqlite_connection(sqlite_db_path)
        
        # Obter lista de tabelas
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
        
        print(f"Tabelas encontradas: {', '.join(tables)}")
        
        # Extrair dados de cada tabela
        data = {}
        for table in tables:
            data[table] = extract_table_data(conn, table)
        
        # Escrever para arquivo JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=CustomEncoder, indent=2)
        
        print(f"\nDados exportados com sucesso para {output_json_path}")
        return True
        
    except Exception as e:
        print(f"Erro ao exportar dados: {e}")
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def generate_postgres_sql(json_data_path, output_sql_path):
    """Gera um script SQL para importação no PostgreSQL"""
    try:
        # Carregar dados JSON
        with open(json_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Gerando script SQL para PostgreSQL...")
        
        with open(output_sql_path, 'w', encoding='utf-8') as f:
            # Cabeçalho do arquivo
            f.write("-- Script gerado para importação no PostgreSQL\n")
            f.write("-- Gerado em: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            # Iniciar uma transação
            f.write("BEGIN;\n\n")
            
            # Para cada tabela
            for table_name, table_data in data.items():
                f.write(f"-- Tabela: {table_name}\n")
                
                # Criar tabela
                columns = table_data['columns']
                create_table_sql = generate_create_table_sql(table_name, columns)
                f.write(create_table_sql + "\n\n")
                
                # Inserir dados
                rows = table_data['rows']
                if rows:
                    f.write(f"-- Inserir dados na tabela {table_name}\n")
                    
                    # Obter nomes das colunas
                    column_names = [col['name'] for col in columns]
                    
                    # Para cada linha de dados
                    for row in rows:
                        # Processar valores
                        values = []
                        for col_name in column_names:
                            value = row.get(col_name)
                            # Tratar NULL
                            if value is None:
                                values.append("NULL")
                            # Tratar strings
                            elif isinstance(value, str):
                                # Escapar aspas
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            # Tratar datas ISO
                            elif isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
                                values.append(f"'{value}'::timestamp")
                            # Outros valores
                            else:
                                values.append(str(value))
                        
                        # Criar comando INSERT
                        insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(values)});"
                        f.write(insert_sql + "\n")
                    
                    f.write("\n")
                
                # Redefinir sequência de autoincremento se a tabela tiver ID
                if 'id' in [col['name'] for col in columns]:
                    f.write(f"-- Resetar sequência do ID para {table_name}\n")
                    f.write(f"SELECT setval('{table_name}_id_seq', (SELECT MAX(id) FROM {table_name}));\n\n")
            
            # Finalizar a transação
            f.write("COMMIT;\n")
        
        print(f"Script SQL gerado com sucesso em {output_sql_path}")
        return True
        
    except Exception as e:
        print(f"Erro ao gerar script SQL: {e}")
        traceback.print_exc()
        return False

def generate_create_table_sql(table_name, columns):
    """Gera o SQL CREATE TABLE adaptado para PostgreSQL"""
    # Mapear tipos de SQLite para PostgreSQL
    type_map = {
        'INTEGER PRIMARY KEY': 'SERIAL PRIMARY KEY',
        'INTEGER PRIMARY KEY AUTOINCREMENT': 'SERIAL PRIMARY KEY',
        'INTEGER': 'INTEGER',
        'TEXT': 'TEXT',
        'TIMESTAMP': 'TIMESTAMP',
        'REAL': 'FLOAT'
    }
    
    column_definitions = []
    foreign_keys = []
    
    for column in columns:
        col_name = column['name']
        col_type = column['type']
        
        # Checar e substituir tipos para PostgreSQL
        for sqlite_type, pg_type in type_map.items():
            if col_type.upper().startswith(sqlite_type):
                col_type = pg_type
                break
        
        # Adicionar definição da coluna
        column_definitions.append(f"    {col_name} {col_type}")
    
    # Construir SQL
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    sql += ",\n".join(column_definitions)
    
    # Adicionar foreign keys, se houver
    if foreign_keys:
        sql += ",\n" + ",\n".join(foreign_keys)
    
    sql += "\n);"
    
    return sql

def generate_railway_instructions(json_path, sql_path):
    """Gera instruções para importar os dados no Railway"""
    with open('railway_import_instructions.txt', 'w', encoding='utf-8') as f:
        f.write("===== INSTRUÇÕES PARA IMPORTAR DADOS NO RAILWAY =====\n\n")
        
        f.write("1. Acesse o dashboard do Railway: https://railway.app/dashboard\n")
        f.write("2. Selecione seu projeto 'ProjetoRed'\n")
        f.write("3. Crie um novo serviço PostgreSQL clicando em 'New' → 'Database' → 'PostgreSQL'\n")
        f.write("4. Após a criação, vá para a aba 'Connect' e copie a URL de conexão\n")
        f.write("5. Abra o arquivo 'app.py' e atualize a variável DATABASE_URL com a URL obtida\n")
        f.write("6. No painel Railway, vá para a aba 'Data'\n")
        f.write("7. Cole o conteúdo do arquivo SQL gerado e execute\n")
        f.write(f"   (O arquivo SQL está em: {sql_path})\n\n")
        
        f.write("8. Alternativamente, use a linha de comando para importar:\n")
        f.write("   psql [URL_DE_CONEXAO] < " + sql_path + "\n\n")
        
        f.write("9. Após importar os dados, edite seu app.py e siga estes passos:\n")
        f.write("   a. Descomente as importações de PostgreSQL\n")
        f.write("   b. Altere 'USE_POSTGRES' para True\n")
        f.write("   c. Atualize DATABASE_URL com a URL de conexão\n\n")
        
        f.write("10. Para garantir que a conexão está funcionando, você pode testar localmente:\n")
        f.write("    python -c \"import psycopg2; conn=psycopg2.connect('SUA_URL_AQUI'); print('Conexão bem-sucedida!');\"\n\n")
        
        f.write("11. Após confirmar que tudo está funcionando, faça o commit das alterações e envie para o Railway\n")
    
    print(f"\nInstruções geradas em 'railway_import_instructions.txt'")

if __name__ == "__main__":
    # Caminhos dos arquivos
    sqlite_db_path = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')
    export_dir = os.path.join(os.path.dirname(__file__), 'export')
    
    # Criar diretório de exportação se não existir
    os.makedirs(export_dir, exist_ok=True)
    
    # Nomes de arquivos com timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(export_dir, f'sqlite_export_{timestamp}.json')
    sql_path = os.path.join(export_dir, f'postgres_import_{timestamp}.sql')
    
    print("=== Migração SQLite para PostgreSQL Railway ===")
    print(f"Banco de dados SQLite: {sqlite_db_path}")
    
    # Verificar se o banco SQLite existe
    if not os.path.exists(sqlite_db_path):
        print(f"Erro: Banco de dados SQLite não encontrado em {sqlite_db_path}")
        sys.exit(1)
    
    # Exportar dados para JSON
    print("\nPasso 1: Exportando dados do SQLite para JSON...")
    if export_sqlite_to_json(sqlite_db_path, json_path):
        # Gerar script SQL para PostgreSQL
        print("\nPasso 2: Gerando script SQL para PostgreSQL...")
        if generate_postgres_sql(json_path, sql_path):
            # Gerar instruções para importação no Railway
            print("\nPasso 3: Gerando instruções para importação no Railway...")
            generate_railway_instructions(json_path, sql_path)
            
            print("\n=== Processo concluído com sucesso! ===")
            print(f"1. Dados exportados para JSON: {json_path}")
            print(f"2. Script SQL gerado: {sql_path}")
            print("3. Siga as instruções em 'railway_import_instructions.txt'")
    
    print("\nObrigado por usar o migrador SQLite → PostgreSQL!") 