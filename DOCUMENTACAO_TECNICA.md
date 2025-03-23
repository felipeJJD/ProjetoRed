# Documentação Técnica - Sistema de Redirecionamento WhatsApp

Esta documentação destina-se a desenvolvedores e detalha os aspectos técnicos do funcionamento interno da aplicação.

## Arquitetura do Sistema

O sistema segue uma arquitetura MVC (Model-View-Controller) simplificada usando Flask:

- **Models**: Implementados como funções SQL no arquivo `app.py`
- **Views**: Templates HTML na pasta `templates/`
- **Controllers**: Rotas Flask no arquivo `app.py`

## Banco de Dados

A aplicação utiliza SQLite com as seguintes tabelas:

### Tabela `users`
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    fullname TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Tabela `whatsapp_numbers`
```sql
CREATE TABLE whatsapp_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```

### Tabela `custom_links`
```sql
CREATE TABLE custom_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    link_name TEXT NOT NULL,
    custom_message TEXT,
    is_active INTEGER DEFAULT 1,
    click_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, link_name)
)
```

### Tabela `redirect_logs`
```sql
CREATE TABLE redirect_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    number_id INTEGER NOT NULL,
    redirect_time TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (link_id) REFERENCES custom_links (id),
    FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id)
)
```

## Fluxo de Funcionamento

### Inicialização da Aplicação

1. O Flask é inicializado com as configurações necessárias
2. A função `init_db()` é chamada para criar o banco de dados, se não existir
3. Usuários padrão são criados se não existirem (pedro e felipe)
4. Links padrão são inicializados para cada usuário

### Autenticação

O sistema utiliza sessions do Flask para autenticação:

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verificação de credenciais e criação da sessão
    if user and check_password_hash(user['password'], password):
        session['logged_in'] = True
        session['username'] = username
        session['user_id'] = user['id']
        session['fullname'] = user['fullname']
```

A função decoradora `@login_required` protege as rotas que requerem autenticação:

```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

### API RESTful

A aplicação implementa uma API RESTful para gerenciar números e links:

#### Gerenciamento de Números
- `GET /api/numbers`: Lista números
- `POST /api/numbers`: Adiciona número
- `DELETE /api/numbers/<id>`: Remove número

#### Gerenciamento de Links
- `GET /api/links`: Lista links
- `POST /api/links`: Adiciona link
- `DELETE /api/links/<id>`: Remove link
- `PUT /api/links/<id>`: Atualiza link

#### Logs de Redirecionamento
- `GET /api/redirects/recent`: Lista os redirecionamentos mais recentes

### Algoritmo de Redirecionamento

O redirecionamento é feito pela rota `/redirect/<link_name>` que:

1. Busca o link personalizado pelo nome
2. Incrementa o contador de cliques
3. Recupera todos os números de WhatsApp do usuário
4. Seleciona aleatoriamente um número da lista
5. Registra o redirecionamento na tabela `redirect_logs` com:
   - ID do link
   - ID do número selecionado
   - Timestamp atual (no fuso horário local)
   - Endereço IP do cliente
   - User-Agent do navegador
6. Formata a URL do WhatsApp com o número selecionado
7. Renderiza a página de redirecionamento com:
   - Mensagem personalizada do link
   - URL do WhatsApp para redirecionamento

```python
@app.route('/redirect/<link_name>')
def redirect_whatsapp(link_name):
    # Buscar o link no banco de dados
    with get_db_connection() as conn:
        link = conn.execute('SELECT * FROM custom_links WHERE link_name = ?', (link_name,)).fetchone()
        
        # Se o link existir
        if link:
            # Incrementar contador de cliques
            conn.execute('UPDATE custom_links SET click_count = click_count + 1 WHERE id = ?', (link['id'],))
            conn.commit()
            
            # Buscar todos os números de WhatsApp do mesmo usuário
            numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (link['user_id'],)).fetchall()
            
            # Se houver números cadastrados
            if numbers:
                # Selecionar um número aleatoriamente
                selected_number = random.choice(numbers)
                phone = selected_number['phone_number']
                
                # Registrar o log de redirecionamento
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent', '')
                
                conn.execute('''
                    INSERT INTO redirect_logs (link_id, number_id, ip_address, user_agent)
                    VALUES (?, ?, ?, ?)
                ''', (link['id'], selected_number['id'], ip_address, user_agent))
                conn.commit()
                
                # Formatar a URL do WhatsApp
                whatsapp_url = f"https://wa.me/{phone}"
                
                # Renderizar a página de redirecionamento
                return render_template('redirect.html', 
                                      whatsapp_url=whatsapp_url, 
                                      custom_message=link['custom_message'])
```

## Frontend

### Componentes JavaScript

O frontend utiliza JavaScript vanilla para comunicação com a API:

1. **Gerenciamento de Números**:
   - Adição de números via AJAX para a rota `/api/numbers`
   - Remoção de números com confirmação do usuário

2. **Gerenciamento de Links**:
   - Criação/edição de links via AJAX
   - Validação de formato do nome do link (sem caracteres especiais)
   - Função para copiar o link para a área de transferência

3. **Página de Redirecionamento**:
   - Contador regressivo implementado em JavaScript
   - Redirecionamento automático após 5 segundos
   - Botão para redirecionamento manual

## Segurança

### Autenticação e Autorização
- Senhas armazenadas com hash usando `werkzeug.security.generate_password_hash`
- Sessions do Flask para manter o estado de autenticação
- Decorator `@login_required` para proteger rotas restritas

### Validação de Dados
- Validação do lado do servidor para todas as entradas
- Verificação de propriedade dos recursos (usuário só acessa seus próprios números/links)

### Proteção contra SQL Injection
- Uso de consultas parametrizadas em todas as operações SQL

## Limitações Conhecidas

1. A aplicação não possui recuperação de senha
2. Não há validação do formato de número de telefone além da UI
3. Não existe paginação para grandes quantidades de números/links
4. Ausência de logs detalhados para auditoria

## Extensões Possíveis

1. **Estatísticas Avançadas**
   - Rastreamento de origem dos cliques
   - Gráficos de desempenho por link

2. **Integrações**
   - Integração com CRM
   - API para criação programática de links

3. **Segurança**
   - Implementação de OAuth 2.0
   - Autenticação de dois fatores

4. **Mensagens**
   - Modelo de mensagens predefinidas
   - Variáveis dinâmicas nas mensagens 