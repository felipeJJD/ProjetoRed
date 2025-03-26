# Guia de Migração: SQLite para PostgreSQL no Railway

Este guia explica como migrar sua aplicação "REDZAP" de SQLite para PostgreSQL no Railway.

## Passos para Migração

### 1. Exportar dados do SQLite para SQL

**✅ Já realizado:** Você já executou o script `migrar_para_railway_postgres.py` que gerou arquivos SQL na pasta `/export`.

### 2. Formatar SQL para PostgreSQL

Execute o script de preparação:

```bash
python importar_railway_alternativo.py
```

Este script vai gerar dois arquivos importantes:
- `postgres_import_XXXXXXXX_formatado.sql` - Script formatado para importação 
- `postgres_import_XXXXXXXX_verificacao.sql` - Script para verificar se a importação foi bem-sucedida

### 3. Importar SQL no PostgreSQL do Railway

1. **Acesse o dashboard do Railway**
2. **Vá para a aba "Data" do PostgreSQL**
3. **Use o painel SQL para executar os comandos:**
   - Abra o arquivo SQL formatado gerado
   - Cole os comandos um por um no editor SQL 
   - Execute cada comando

Alternativamente, se tiver o PostgreSQL instalado localmente:
```bash
psql [URL_DE_CONEXAO] -f [caminho_para_o_arquivo_formatado.sql]
```

### 4. Verificar a importação

1. Use o script de verificação:
   - Abra o arquivo `_verificacao.sql` gerado
   - Cole os comandos no editor SQL do Railway
   - Execute e verifique se os dados estão corretos

### 5. Configurar app.py para usar PostgreSQL

1. **Verifique se as alterações no app.py foram realizadas:**
   - As importações de PostgreSQL foram adicionadas
   - A função `get_db_connection()` foi adaptada
   - A função `execute_query()` foi adicionada

2. **Atualize as configurações:**
```python
# Altere para True para usar PostgreSQL
app.config['USE_POSTGRES'] = True  

# Atualize com a URL de conexão do Railway
app.config['DATABASE_URL'] = 'postgresql://postgres:SuaSenha@host:porta/railway'
```

3. **Instale a biblioteca psycopg2:**
```bash
pip install psycopg2-binary
```
Obs: Se tiver problemas com a instalação local, você pode fazer o deploy direto no Railway, que já terá as bibliotecas necessárias.

### 6. Testar a aplicação

1. **Localmente:**
```bash
python app.py
```

2. **No Railway:**
   - Faça commit das alterações e envie para o GitHub
   - O Railway fará o deploy automaticamente

## Resolução de Problemas

### Erro "pg_config executable not found"

Se você estiver no macOS e encontrar este erro ao instalar psycopg2, tente:
```bash
brew install postgresql
```

### Não consigo instalar psycopg2-binary

Para testar somente no Railway:
1. Faça commit das alterações no app.py
2. Defina `USE_POSTGRES = True`
3. Faça o deploy no Railway sem testar localmente

### Erros de SQL no Railway

Se encontrar erros ao executar os comandos SQL:
1. Execute um comando de cada vez
2. Verifique se há erros de sintaxe ou incompatibilidade
3. Adapte os comandos conforme necessário

## Benefícios do PostgreSQL

- Melhor desempenho para mais usuários simultâneos
- Recursos avançados (consultas complexas, índices, etc.)
- Melhor para ambientes de produção
- Escalabilidade para crescimento futuro

---

Se precisar de mais ajuda ou tiver dúvidas, contate o desenvolvedor. 