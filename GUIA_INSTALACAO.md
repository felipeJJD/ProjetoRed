# Guia de Instalação para Desenvolvedores

Este guia fornece instruções detalhadas para configurar o ambiente de desenvolvimento do Sistema de Redirecionamento para WhatsApp.

## Pré-requisitos

- Python 3.6 ou superior
- Pip (gerenciador de pacotes do Python)
- Git

## Passo 1: Clonar o Repositório

```bash
# Clone o repositório
git clone <url-do-repositório>

# Entre no diretório do projeto
cd <diretório-do-projeto>
```

## Passo 2: Configurar o Ambiente Virtual

### No Windows:

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente virtual
venv\Scripts\activate
```

### No macOS/Linux:

```bash
# Criar o ambiente virtual
python3 -m venv venv

# Ativar o ambiente virtual
source venv/bin/activate
```

## Passo 3: Instalar as Dependências

```bash
# Instalar os pacotes necessários
pip install -r requirements.txt
```

## Passo 4: Inicializar o Banco de Dados

O banco de dados será inicializado automaticamente na primeira execução da aplicação. Não são necessários comandos adicionais.

## Passo 5: Executar a Aplicação

```bash
# Iniciar o servidor de desenvolvimento
python app.py
```

A aplicação estará disponível em `http://localhost:5000`.

## Passo 6: Acessar o Sistema

1. Abra seu navegador e acesse `http://localhost:5000`
2. Para acessar a área administrativa, vá para `http://localhost:5000/login`
3. Use as credenciais padrão:
   - Usuário: `pedro`
   - Senha: `Vera123`

## Solução de Problemas Comuns

### Erro ao iniciar o aplicativo

Se você encontrar um erro ao iniciar o aplicativo, verifique:

1. Se o Python está na versão correta:
```bash
python --version
```

2. Se todas as dependências foram instaladas:
```bash
pip list
```

3. Se o ambiente virtual está ativado (o prompt deve mostrar `(venv)` no início).

### Erro de permissão no banco de dados

Se ocorrerem erros de permissão ao acessar o banco de dados:

1. Verifique se o diretório `instance` foi criado
2. Verifique se o usuário que executa a aplicação tem permissão de escrita nesse diretório

### Erro ao adicionar números ou links

Se ocorrerem erros ao adicionar números ou links:

1. Verifique se o formato do número está correto (somente dígitos)
2. Verifique se o nome do link contém apenas caracteres válidos (letras, números e hífens)

## Configuração para Desenvolvimento

### Modo de Depuração

Para ativar o modo de depuração durante o desenvolvimento, modifique o arquivo `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=True)
```

### Estrutura de Arquivos Recomendada

Para organizar seu ambiente de desenvolvimento:

```
projeto/
│
├── venv/               # Ambiente virtual
├── instance/           # Banco de dados
│   └── whatsapp_redirect.db
│
├── static/             # Arquivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
│
├── templates/          # Templates HTML
│
├── app.py              # Aplicação principal
├── requirements.txt    # Dependências
├── README.md           # Documentação principal
└── .gitignore          # Arquivos ignorados pelo Git
```

## Próximos Passos

Após a instalação bem-sucedida:

1. Familiarize-se com a estrutura do código
2. Consulte a documentação técnica em `DOCUMENTACAO_TECNICA.md`
3. Adicione números de teste para desenvolvimento
4. Explore as funcionalidades de criação de links personalizados 