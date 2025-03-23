# REDZAP - Sistema de Redirecionamento para WhatsApp

Um sistema web para gerenciar múltiplos números de WhatsApp e criar links de redirecionamento personalizados, distribuindo o fluxo de atendimento entre diferentes números.

## Funcionalidades

- **Gerenciamento de Números**: Cadastro e remoção de números de WhatsApp para atendimento
- **Links Personalizados**: Criação de links com nomes personalizados para diferentes campanhas
- **Mensagens Customizadas**: Definição de mensagens específicas para cada link
- **Balanceamento de Carga**: Distribuição automática de clientes entre os números cadastrados
- **Contador de Cliques**: Monitoramento do número de cliques em cada link
- **Autenticação de Usuários**: Sistema multi-usuário com login e controle de acesso
- **Interface Responsiva**: Adaptável para desktop e dispositivos móveis
- **Dashboard Analítico**: Visualização de métricas em gráficos detalhados
- **Estatísticas Avançadas**: Análise de cliques por período, país e horário
- **Filtros Personalizados**: Seleção de links e períodos para análise específica

## Dashboard

O sistema conta com um dashboard completo que oferece:

- **Gráfico de Evolução**: Visualização dos cliques ao longo do tempo
- **Mapa de Cliques**: Distribuição geográfica dos acessos
- **Análise por Período**: Horários com maior volume de acessos
- **Estatísticas Resumidas**: Total de cliques, média diária, links e números ativos
- **Atividade Recente**: Lista dos últimos redirecionamentos realizados
- **Filtros Personalizados**: Seleção de links específicos e intervalo de datas

## Tecnologias Utilizadas

- **Backend**: Python com Flask
- **Banco de Dados**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Framework CSS**: Bootstrap 5
- **Ícones**: Bootstrap Icons
- **Gráficos**: Chart.js para visualização de dados

## Requisitos do Sistema

- Python 3.6+
- Flask 2.0.1
- Werkzeug 2.0.3
- Gunicorn 20.1.0 (para deploy em produção)

## Instalação

1. Clone o repositório:
   ```
   git clone <url-do-repositório>
   ```

2. Crie e ative um ambiente virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Execute a aplicação:
   ```
   python app.py
   ```

5. Acesse a aplicação em:
   ```
   http://localhost:5000
   ```

## Uso

### Autenticação

1. Acesse a página de login `/login`
2. Use as credenciais padrão:
   - Usuário: `pedro`
   - Senha: `Vera123`

### Gerenciamento de Números

1. Na área administrativa, acesse a aba "Números de WhatsApp"
2. Adicione novos números no formato internacional (ex: 5511999998888)
3. Atribua uma descrição para identificação (opcional)

### Criação de Links Personalizados

1. Acesse a aba "Links Personalizados"
2. Clique em "Criar Novo Link"
3. Defina um nome para o link (ex: "promocao-verao")
4. Personalize a mensagem que será exibida antes do redirecionamento
5. Copie a URL gerada para compartilhar

### Página de Redirecionamento

Quando um usuário acessa um link personalizado:
1. A mensagem personalizada é exibida
2. Um contador regressivo de 5 segundos é iniciado
3. O usuário é redirecionado automaticamente para um dos números de WhatsApp cadastrados
4. O usuário também pode clicar no botão para redirecionamento imediato

## Estrutura do Projeto

- `app.py`: Aplicação principal Flask
- `instance/whatsapp_redirect.db`: Banco de dados SQLite
- `templates/`: Arquivos HTML
  - `index.html`: Página inicial
  - `login.html`: Página de login
  - `admin.html`: Painel administrativo
  - `redirect.html`: Página de redirecionamento
- `static/`: Arquivos estáticos (CSS, JS, imagens)
- `Procfile`: Configuração para deploy (Heroku)
- `requirements.txt`: Dependências do projeto

## Usuários Padrão

O sistema é inicializado com dois usuários administrativos:

1. **Pedro**
   - Usuário: `pedro`
   - Senha: `Vera123`

2. **Felipe**
   - Usuário: `felipe`
   - Senha: `123`

## Deploy em Produção

O projeto está configurado para deploy em plataformas como Heroku:

```
web: gunicorn app:app
```

## Documentação Adicional

Para informações mais detalhadas sobre o sistema, consulte:

- [Índice de Documentação](DOCUMENTACAO.md) - Visão geral de toda a documentação disponível
- [Documentação Técnica](DOCUMENTACAO_TECNICA.md) - Detalhes do funcionamento interno para desenvolvedores
- [Guia de Instalação](GUIA_INSTALACAO.md) - Instruções detalhadas para configuração do ambiente
- [Tutorial do Usuário](TUTORIAL_USUARIO.md) - Guia passo a passo para usuários finais
- [Changelog](CHANGELOG.md) - Histórico de alterações do projeto

## Licença

Este projeto é de uso privado e não possui licença pública. 