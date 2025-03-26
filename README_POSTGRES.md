# REDZAP - Versão PostgreSQL

Esta versão do REDZAP está configurada para usar PostgreSQL como banco de dados. Abaixo estão as instruções para configuração e uso.

## Configuração do PostgreSQL no Railway

1. Acesse o painel do Railway e configure o PostgreSQL:
   - Crie um novo serviço PostgreSQL
   - Obtenha a URL de conexão na aba "Connect"
   - Atualize o valor de `DATABASE_URL` no arquivo `app.py`

2. Importe o esquema e dados:
   - Acesse a aba "Data" do PostgreSQL no Railway
   - Execute os comandos SQL formatados gerados pelo script
   - Verifique se os dados foram importados corretamente

## Arquivos Importantes

- `app.py` - Aplicação principal, configurada para usar PostgreSQL
- `export/` - Contém os arquivos SQL para importação
- `INSTRUCOES_POSTGRESQL_RAILWAY.md` - Guia detalhado de migração

## Variáveis de Configuração

```python
# Ativar PostgreSQL (já está configurado como True)
app.config['USE_POSTGRES'] = True

# URL de conexão do PostgreSQL (substitua pela sua URL real)
app.config['DATABASE_URL'] = 'postgresql://postgres:sua_senha@host:porta/railway'
```

## Funcionamento

A aplicação verifica a configuração `USE_POSTGRES` e escolhe automaticamente o driver de banco de dados apropriado.

Se `USE_POSTGRES` for `True`, a aplicação usará PostgreSQL através do módulo `psycopg2`.
Caso contrário, usará SQLite (útil para desenvolvimento local).

## Dependências

Para o PostgreSQL, é necessário:
```
psycopg2-binary
```

Esta dependência já está configurada para ser instalada automaticamente no Railway. 