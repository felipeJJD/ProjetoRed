# Changelog - Sistema de Redirecionamento WhatsApp

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.2.0] - 2024-06-25

### Adicionado
- Dashboard completo com gráficos e métricas visuais
- Gráfico de evolução de visitas ao longo do tempo
- Gráfico de acessos por país
- Gráfico de visitas por período do dia
- Mapa visual de cliques
- Cards com estatísticas resumidas (cliques totais, média diária, links ativos, números ativos)
- Filtros de data e link para análises personalizadas
- Novas APIs para fornecer dados estatísticos
- Design moderno com tema verde e preto
- Interface responsiva e intuitiva para monitoramento

## [1.1.0] - 2024-06-22

### Adicionado
- Nova tabela `redirect_logs` para registrar todos os redirecionamentos com timestamp local
- Nova aba "Métricas e Logs" no painel administrativo
- API para consultar registros de redirecionamentos recentes
- Visualização detalhada dos redirecionamentos com data/hora correta, link, número e IP
- Armazenamento do User-Agent do cliente para melhor análise

### Corrigido
- Problema nos horários de redirecionamento que não estavam sendo registrados
- Timestamp agora usa o fuso horário local em vez de UTC

## [1.0.0] - 2024-06-14

### Adicionado
- Versão inicial do sistema
- Autenticação de usuários com múltiplos perfis
- Gerenciamento de números de WhatsApp
- Criação e edição de links personalizados
- Mensagens customizáveis para cada link
- Contagem de cliques para cada link
- Sistema de redirecionamento aleatório entre números
- Interface administrativa responsiva
- Documentação completa do sistema

## [0.9.0] - 2024-06-01

### Adicionado
- Funcionalidade de redirecionamento básica
- Estrutura inicial do banco de dados
- Protótipo da interface administrativa

### Corrigido
- Problemas de compatibilidade com diferentes navegadores

## [0.8.0] - 2024-05-15

### Adicionado
- Desenvolvimento da interface administrativa
- Implementação do sistema de autenticação
- Criação das rotas básicas da API

## [0.7.0] - 2024-05-01

### Adicionado
- Planejamento inicial do projeto
- Definição de requisitos
- Modelagem do banco de dados
- Criação do ambiente de desenvolvimento

## Guia de Versionamento

- **MAJOR (X.0.0)**: Mudanças incompatíveis com versões anteriores
- **MINOR (0.X.0)**: Adição de funcionalidades compatíveis com versões anteriores
- **PATCH (0.0.X)**: Correções de bugs compatíveis com versões anteriores 