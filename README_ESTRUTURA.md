# Estrutura do Projeto de Redirecionamento WhatsApp

Este documento descreve a estrutura atual do projeto após a migração do SQLite para PostgreSQL e a reorganização das rotas.

## Estrutura de Diretórios

```
.
├── app/
│   ├── __init__.py             # Configuração principal da aplicação
│   ├── controllers/            # Controladores para lógica de negócios
│   ├── decorators/             # Decorators personalizados
│   ├── models/                 # Modelos de dados
│   ├── routes/                 # Definição de rotas em blueprints
│   └── services/               # Serviços (balanceamento, geolocalização, etc.)
├── config/
│   └── settings.py             # Configurações da aplicação
├── static/                     # Arquivos estáticos
├── templates/                  # Templates HTML
├── utils/
│   ├── db_adapter.py           # Adaptador de banco de dados para PostgreSQL
│   └── init_db.py              # Inicialização do banco de dados
├── app.py                      # Ponto de entrada principal da aplicação
├── main.py                     # Script alternativo para execução com argumentos
└── requirements.txt            # Dependências do projeto
```

## Banco de Dados

O sistema está configurado para usar exclusivamente PostgreSQL, com as seguintes configurações:

- Host: switchyard.proxy.rlwy.net
- Porta: 24583
- Banco: railway
- Usuário: postgres
- Senha: nsAgxYUGJuIRXTalVIdclsTDecKEsgpc

## Rotas Principais

As rotas estão organizadas em blueprints:

1. **auth_bp** (/auth) - Autenticação (login, logout)
2. **admin_bp** (/admin) - Administração e dashboard
3. **api_bp** (/api) - Endpoints da API para números e links
4. **redirect_bp** (/) - Redirecionamento para WhatsApp

## Como Executar

1. **Local:**
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar o servidor
python app.py
```

2. **Em produção (Railway):**
O sistema está configurado para ser implantado na Railway, usando as variáveis de ambiente definidas na plataforma.

## Funcionalidades Principais

1. **Redirecionamento para WhatsApp:** Permite criar links curtos que redirecionam para números de WhatsApp.
2. **Balanceamento de Carga:** Distribui o tráfego entre múltiplos números de WhatsApp.
3. **Estatísticas:** Rastreia redirecionamentos e fornece dashboards.
4. **Geolocalização:** Obtém informações de localização dos visitantes.

## Migrações do SQLite para PostgreSQL

Todas as funções foram migradas do SQLite para usar exclusivamente PostgreSQL. As principais alterações incluem:

1. Substituição de placeholders `?` por `%s` nas consultas SQL
2. Alteração nas chamadas de criação de tabelas
3. Implementação específica de PostgreSQL para timestamp e sequências
4. Remoção da lógica de escolha entre SQLite e PostgreSQL, usando apenas PostgreSQL 