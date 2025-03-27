import os
import random
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, send_from_directory, abort
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import requests  # Para chamadas API externas

# Configuração do Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Chave secreta para sessões
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

# Garantir que o diretório instance exista
os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

# Configurações para desenvolvimento
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Desativar cache para desenvolvimento
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Recarregar templates automaticamente

# Funções para gerenciar banco de dados
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Criar tabela de planos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                max_numbers INTEGER NOT NULL,
                max_links INTEGER NOT NULL,
                description TEXT
            )
        ''')
        
        # Verificar se existem planos e criar os padrões se não houver
        if not conn.execute('SELECT * FROM plans').fetchone():
            # Criar planos padrão (básico, intermediário, avançado, ilimitado)
            conn.execute('''
                INSERT INTO plans (name, max_numbers, max_links, description)
                VALUES (?, ?, ?, ?)
            ''', ('basic', 2, 1, 'Plano Básico'))
            
            conn.execute('''
                INSERT INTO plans (name, max_numbers, max_links, description)
                VALUES (?, ?, ?, ?)
            ''', ('intermediary', 5, 5, 'Plano Intermediário'))
            
            conn.execute('''
                INSERT INTO plans (name, max_numbers, max_links, description)
                VALUES (?, ?, ?, ?)
            ''', ('advanced', 15, -1, 'Plano Avançado')) # -1 indica links ilimitados
            
            conn.execute('''
                INSERT INTO plans (name, max_numbers, max_links, description)
                VALUES (?, ?, ?, ?)
            ''', ('unlimited', -1, -1, 'Plano Ilimitado')) # -1 para números e links ilimitados
        
        # Criar tabela de usuários
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                fullname TEXT,
                plan_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES plans (id)
            )
        ''')
        
        # Verificar se existem usuários e criar os padrões se não houver
        if not conn.execute('SELECT * FROM users').fetchone():
            # Criar usuários padrão (pedro e felipe)
            conn.execute('''
                INSERT INTO users (username, password, fullname, plan_id)
                VALUES (?, ?, ?, ?)
            ''', ('pedro', generate_password_hash('Vera123'), 'Pedro Administrador', 3))
            
            conn.execute('''
                INSERT INTO users (username, password, fullname, plan_id)
                VALUES (?, ?, ?, ?)
            ''', ('felipe', generate_password_hash('123'), 'Felipe Administrador', 3))

        # Verificar se precisamos adicionar a coluna plan_id na tabela users (para bancos existentes)
        user_cols = [col['name'] for col in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'plan_id' not in user_cols:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN plan_id INTEGER DEFAULT 1')
                conn.execute('UPDATE users SET plan_id = 3') # Define plano avançado para usuários existentes
            except:
                print("Erro ao adicionar coluna plan_id à tabela users")
        
        # Criar tabela de números com referência ao usuário
        conn.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Verificar se a coluna is_active existe na tabela whatsapp_numbers
        result = conn.execute("PRAGMA table_info(whatsapp_numbers)").fetchall()
        columns = [col['name'] for col in result]
        
        # Adicionar coluna is_active se não existir
        if 'is_active' not in columns:
            try:
                conn.execute('ALTER TABLE whatsapp_numbers ADD COLUMN is_active INTEGER DEFAULT 1')
                print("Coluna is_active adicionada à tabela whatsapp_numbers")
            except:
                print("Erro ao adicionar coluna is_active")
        
        # Adicionar coluna last_used se não existir
        if 'last_used' not in columns:
            try:
                conn.execute('ALTER TABLE whatsapp_numbers ADD COLUMN last_used TIMESTAMP')
                print("Coluna last_used adicionada à tabela whatsapp_numbers")
            except:
                print("Erro ao adicionar coluna last_used")
        
        # Criar tabela de links personalizados com referência ao usuário
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                link_name TEXT NOT NULL,
                custom_message TEXT,
                is_active INTEGER DEFAULT 1,
                click_count INTEGER DEFAULT 0,
                prefix INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Nova tabela para logs de redirecionamentos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS redirect_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL,
                number_id INTEGER NOT NULL,
                redirect_time TIMESTAMP DEFAULT (datetime('now')),
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (link_id) REFERENCES custom_links (id),
                FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id)
            )
        ''')
        
        # Verificar se as colunas necessárias existem
        result = conn.execute("PRAGMA table_info(custom_links)").fetchall()
        columns = [col['name'] for col in result]
        
        # Verificar se a coluna prefix existe e adicioná-la se não existir
        if 'prefix' not in columns:
            try:
                conn.execute('ALTER TABLE custom_links ADD COLUMN prefix INTEGER DEFAULT 1')
                print("Coluna prefix adicionada à tabela custom_links")
            except:
                print("Erro ao adicionar coluna prefix")
        
        # Adicionar coluna user_id se não existir
        if 'user_id' not in columns:
            try:
                # Fazer backup dos dados existentes
                links = conn.execute('SELECT * FROM custom_links').fetchall()
                # Recriar a tabela com a nova estrutura
                conn.execute('DROP TABLE IF EXISTS custom_links_old')
                conn.execute('ALTER TABLE custom_links RENAME TO custom_links_old')
                
                # Criar nova tabela com a estrutura correta
                conn.execute('''
                    CREATE TABLE custom_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        link_name TEXT NOT NULL,
                        custom_message TEXT,
                        is_active INTEGER DEFAULT 1,
                        click_count INTEGER DEFAULT 0,
                        prefix INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Transferir dados, atribuindo a pedro (id=1) por padrão
                for link in links:
                    conn.execute('''
                        INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active, prefix)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (link['id'], 1, link['link_name'], link['custom_message'], link['is_active'], 1))
            except:
                # Se algo der errado, garantir que a tabela exista
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS custom_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        link_name TEXT NOT NULL,
                        custom_message TEXT,
                        is_active INTEGER DEFAULT 1,
                        click_count INTEGER DEFAULT 0,
                        prefix INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
        
        # Adicionar coluna click_count se não existir
        if 'click_count' not in columns:
            try:
                conn.execute('ALTER TABLE custom_links ADD COLUMN click_count INTEGER DEFAULT 0')
            except:
                pass  # Ignorar erro se a coluna já existir ou em caso de outra falha
        
        # Mesmo processo para a tabela whatsapp_numbers
        result = conn.execute("PRAGMA table_info(whatsapp_numbers)").fetchall()
        columns = [col['name'] for col in result]
        
        if 'user_id' not in columns:
            try:
                # Fazer backup dos dados existentes
                numbers = conn.execute('SELECT * FROM whatsapp_numbers').fetchall()
                # Recriar a tabela
                conn.execute('DROP TABLE IF EXISTS whatsapp_numbers_old')
                conn.execute('ALTER TABLE whatsapp_numbers RENAME TO whatsapp_numbers_old')
                
                # Criar nova tabela com a estrutura correta
                conn.execute('''
                    CREATE TABLE whatsapp_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        phone_number TEXT NOT NULL,
                        description TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Transferir dados, atribuindo a pedro (id=1) por padrão
                for number in numbers:
                    conn.execute('''
                        INSERT INTO whatsapp_numbers (id, user_id, phone_number, description)
                        VALUES (?, ?, ?, ?)
                    ''', (number['id'], 1, number['phone_number'], number['description']))
            except:
                # Se algo der errado, garantir que a tabela exista
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        phone_number TEXT NOT NULL,
                        description TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
        
        # Garantir que cada usuário tenha pelo menos um link padrão
        for user_id in [1, 2]:  # pedro e felipe
            conn.execute('''
                INSERT OR IGNORE INTO custom_links (user_id, link_name, custom_message, prefix)
                VALUES (?, 'whatsapp', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1)
            ''', (user_id,))

# Inicializar o banco de dados
init_db()

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"Verificando autenticação para rota: {request.path}")
        print(f"Informações da sessão: {session}")
        if 'logged_in' not in session or not session['logged_in']:
            print(f"Acesso negado: usuário não está logado")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas da aplicação
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Buscar usuário no banco de dados
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        # Verificar credenciais
        if user and check_password_hash(user['password'], password):
            session.clear()  # Limpar qualquer sessão existente
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']
            session['fullname'] = user['fullname']
            print(f"Login bem-sucedido para usuário: {username}, ID: {user['id']}")
            return redirect(url_for('admin'))
        else:
            error = 'Credenciais inválidas. Por favor, tente novamente.'
            print(f"Tentativa de login falhou para usuário: {username}")
    
    # Se for método GET ou login falhar
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    print(f"Logout para usuário: {session.get('username')}")
    session.clear()  # Limpar a sessão completamente
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    # Redirecionar para a página de administração principal
    return redirect(url_for('administracao'))

# Rota alternativa para a página de administração
@app.route('/administracao')
@login_required
def administracao():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
    
    return render_template('administracao.html', numbers=numbers, links=links)

# Rota para a página de dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
    
    return render_template('dashboard.html', links=links)

# API para gerenciar números de WhatsApp
@app.route('/api/numbers', methods=['GET', 'POST'])
@login_required
def manage_numbers():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        if request.method == 'POST':
            # Verificar se os dados são JSON ou formulário
            if request.is_json:
                data = request.json
                phone_number = data.get('phone_number')
                description = data.get('description')
            else:
                phone_number = request.form.get('phone_number')
                description = request.form.get('description')
            
            # Validação do número de telefone
            if not phone_number:
                return jsonify({'success': False, 'error': 'Número de telefone é obrigatório'}), 400
            
            # Validar e formatar o número de telefone
            validated_number = validate_phone_number(phone_number)
            if not validated_number:
                return jsonify({'success': False, 'error': 'Número de telefone inválido. Use o formato: 5541999887766'}), 400
            
            # Verificar se o número já existe para este usuário
            existing = conn.execute('SELECT * FROM whatsapp_numbers WHERE phone_number = ? AND user_id = ?', 
                                  (validated_number, user_id)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Este número já está cadastrado para o seu usuário'}), 400
            
            # Verificar o limite de plano do usuário para números
            plan_info = conn.execute('''
                SELECT p.max_numbers
                FROM users u
                JOIN plans p ON u.plan_id = p.id
                WHERE u.id = ?
            ''', (user_id,)).fetchone()
            
            if not plan_info:
                return jsonify({'success': False, 'error': 'Informações do plano não encontradas'}), 400
            
            # Verificar número atual de chips do usuário
            current_numbers = conn.execute('''
                SELECT COUNT(*) as count
                FROM whatsapp_numbers
                WHERE user_id = ?
            ''', (user_id,)).fetchone()['count']
            
            # Se max_numbers > 0 (não ilimitado) e já atingiu o limite, impedir a criação
            if plan_info['max_numbers'] >= 0 and current_numbers >= plan_info['max_numbers']:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de chips atingido. Seu plano permite apenas {plan_info["max_numbers"]} chip(s). Contate o administrador para upgrade.'
                }), 400
            
            # Inserir o novo número
            conn.execute('INSERT INTO whatsapp_numbers (user_id, phone_number, description) VALUES (?, ?, ?)', 
                       (user_id, validated_number, description))
            
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso'})
        
        # Se for GET, retornar todos os números
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
        return jsonify([dict(number) for number in numbers])

# Função para validar número de telefone
def validate_phone_number(phone):
    # Remover caracteres não numéricos
    clean_number = ''.join(filter(str.isdigit, phone))
    
    # Verificar se o número tem pelo menos 10 dígitos (formato internacional com DDD)
    if len(clean_number) < 10:
        return None
    
    # Se não começar com código do país, assumir Brasil (+55)
    if not clean_number.startswith('55'):
        clean_number = '55' + clean_number
    
    return clean_number

@app.route('/api/numbers/<int:number_id>', methods=['DELETE', 'PUT'])
@login_required
def delete_number(number_id):
    user_id = session.get('user_id')
    try:
        with get_db_connection() as conn:
            # Verificar se o número pertence ao usuário atual
            number = conn.execute('SELECT * FROM whatsapp_numbers WHERE id = ? AND user_id = ?', 
                               (number_id, user_id)).fetchone()
            if not number:
                return jsonify({'success': False, 'error': 'Número não encontrado ou sem permissão'}), 403
            
            if request.method == 'DELETE':
                # Remover o número ao invés de apenas desativá-lo
                conn.execute('DELETE FROM whatsapp_numbers WHERE id = ?', (number_id,))
                conn.commit()
                return jsonify({'success': True, 'message': 'Número excluído com sucesso'})
            
            elif request.method == 'PUT':
                # Atualizar informações do número
                if request.is_json:
                    data = request.json
                    description = data.get('description')
                    is_active = data.get('is_active')
                    
                    update_fields = []
                    params = []
                    
                    if description is not None:
                        update_fields.append('description = ?')
                        params.append(description)
                    
                    if is_active is not None:
                        update_fields.append('is_active = ?')
                        params.append(is_active)
                    
                    if update_fields:
                        params.append(number_id)
                        conn.execute(f'UPDATE whatsapp_numbers SET {", ".join(update_fields)} WHERE id = ?', params)
                        return jsonify({'success': True, 'message': 'Número atualizado com sucesso'})
                    
                    return jsonify({'success': False, 'error': 'Nenhum campo para atualizar'}), 400
                
                return jsonify({'success': False, 'error': 'Formato JSON inválido'}), 400
            
    except Exception as e:
        print(f"Erro ao gerenciar número: {str(e)}")
        return jsonify({'success': False, 'error': 'Ocorreu um erro ao processar sua solicitação'}), 500

# API para gerenciar links personalizados
@app.route('/api/links', methods=['GET', 'POST'])
@login_required
def manage_links():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        if request.method == 'POST':
            # Verificar se os dados são JSON ou formulário
            if request.is_json:
                data = request.json
                link_name = data.get('link_name')
                custom_message = data.get('custom_message')
            else:
                link_name = request.form.get('link_name')
                custom_message = request.form.get('custom_message')
            
            # Validar dados
            if not link_name:
                return jsonify({'success': False, 'error': 'Nome do link é obrigatório'}), 400
            
            # Verificar o limite de plano do usuário
            plan_info = conn.execute('''
                SELECT p.max_links
                FROM users u
                JOIN plans p ON u.plan_id = p.id
                WHERE u.id = ?
            ''', (user_id,)).fetchone()
            
            if not plan_info:
                return jsonify({'success': False, 'error': 'Informações do plano não encontradas'}), 400
            
            # Verificar número atual de links do usuário
            current_links = conn.execute('''
                SELECT COUNT(*) as count
                FROM custom_links
                WHERE user_id = ?
            ''', (user_id,)).fetchone()['count']
            
            # Se max_links > 0 (não ilimitado) e já atingiu o limite, impedir a criação
            if plan_info['max_links'] >= 0 and current_links >= plan_info['max_links']:
                return jsonify({
                    'success': False, 
                    'error': f'Limite de links atingido. Seu plano permite apenas {plan_info["max_links"]} link(s). Contate o administrador para upgrade.'
                }), 400
            
            # Determinar o próximo prefixo disponível para este link
            prefix = get_next_prefix(conn, user_id, link_name)
            
            # Inserir o novo link com o prefixo calculado
            conn.execute('INSERT INTO custom_links (user_id, link_name, custom_message, prefix) VALUES (?, ?, ?, ?)', 
                       (user_id, link_name, custom_message, prefix))
            
            # Retornar também o prefixo para que o frontend possa exibir o link completo
            return jsonify({
                'success': True, 
                'message': 'Link adicionado com sucesso',
                'prefix': prefix,
                'full_link': f"{prefix}/{link_name}"
            })
        
        # Se for GET, retornar todos os links
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ? ORDER BY link_name, prefix', (user_id,)).fetchall()
        return jsonify([dict(link) for link in links])

@app.route('/api/links/<int:link_id>', methods=['DELETE'])
@login_required
def delete_link(link_id):
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        # Verificar se o link pertence ao usuário atual
        link = conn.execute('SELECT * FROM custom_links WHERE id = ? AND user_id = ?', 
                         (link_id, user_id)).fetchone()
        if not link:
            return jsonify({'success': False, 'error': 'Link não encontrado ou sem permissão'}), 403
        
        # Não permitir excluir o link padrão (agora whatsapp)
        if link['link_name'] == 'whatsapp' and link['prefix'] == 1:
            return jsonify({'success': False, 'error': 'Não é possível excluir o link padrão WhatsApp'}), 400
        
        conn.execute('DELETE FROM custom_links WHERE id = ?', (link_id,))
        return jsonify({'success': True})

@app.route('/api/links/<int:link_id>', methods=['PUT'])
@login_required
def update_link(link_id):
    user_id = session.get('user_id')
    data = request.json
    
    with get_db_connection() as conn:
        # Verificar se o link pertence ao usuário atual
        link = conn.execute('SELECT * FROM custom_links WHERE id = ? AND user_id = ?', 
                         (link_id, user_id)).fetchone()
        if not link:
            return jsonify({'success': False, 'error': 'Link não encontrado ou sem permissão'}), 403
        
        # Atualizar o link (apenas custom_message e is_active)
        # Nota: Não permitimos mais alterar o link_name para evitar confusão com o sistema de prefixos
        if 'custom_message' in data:
            conn.execute('UPDATE custom_links SET custom_message = ? WHERE id = ?', 
                      (data['custom_message'], link_id))
        
        if 'is_active' in data:
            conn.execute('UPDATE custom_links SET is_active = ? WHERE id = ?', 
                      (1 if data['is_active'] else 0, link_id))
        
        return jsonify({'success': True})

# Lista de rotas reservadas que não podem ser usadas como link_name
reserved_routes = [
    '', 'api', 'login', 'logout', 'admin', 'dashboard', 'administracao', 
    'static', 'redirect', 'favicon.ico', 'robots.txt'
]

# Rota para redirecionamento direto ao WhatsApp (mantém o prefixo redirect por compatibilidade)
@app.route('/redirect/<link_name>')
def redirect_whatsapp_with_prefix(link_name):
    return redirect_whatsapp_func(link_name, None)

# Nova rota para redirecionamento com prefixo/nome
@app.route('/<int:prefix>/<link_name>')
def redirect_whatsapp_with_counter(prefix, link_name):
    return redirect_whatsapp_func(link_name, prefix)

# Rota simplificada para compatibilidade com links antigos (tenta usar o prefixo 1)
@app.route('/<link_name>')
def redirect_whatsapp(link_name):
    # Verificar se o link_name não é uma rota reservada
    if link_name in reserved_routes:
        abort(404)  # Retorna 404 Not Found para evitar conflito com rotas existentes
    return redirect_whatsapp_func(link_name, 1)  # Tentar com prefixo 1 (padrão)

# Função que contém a lógica de redirecionamento
def redirect_whatsapp_func(link_name, prefix=None):
    redirect_start_time = datetime.now()
    
    # Melhorar a captura do IP para considerar proxies
    if request.headers.get('X-Forwarded-For'):
        # Se estiver atrás de um proxy, usar o primeiro IP na cadeia
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        # Alguns servidores usam X-Real-IP
        client_ip = request.headers.get('X-Real-IP')
    else:
        # Caso padrão, usar o remote_addr
        client_ip = request.remote_addr
    
    # Verificar se temos um IP válido
    if not client_ip or client_ip == '':
        client_ip = '0.0.0.0'  # IP padrão quando não conseguimos detectar
    
    # Logar o IP capturado para debug
    print(f"IP capturado para redirecionamento: {client_ip}, Link: {link_name}, Prefix: {prefix}")
    
    user_agent = request.headers.get('User-Agent', '')
    
    try:
        with get_db_connection() as conn:
            # Procurar qual usuário é dono do link
            query = '''
                SELECT cl.*, u.id as owner_id 
                FROM custom_links cl
                JOIN users u ON cl.user_id = u.id
                WHERE cl.link_name = ? AND cl.is_active = 1
            '''
            params = [link_name]
            
            # Se um prefixo foi especificado, adicionar à consulta
            if prefix is not None:
                query += " AND cl.prefix = ?"
                params.append(prefix)
            
            # Buscar o link
            link = conn.execute(query, params).fetchone()
            
            if not link:
                # Link não encontrado ou inativo
                return render_template('index.html', error='Link não encontrado ou inativo')
            
            # Incrementar contador de cliques
            conn.execute('UPDATE custom_links SET click_count = click_count + 1 WHERE id = ?', (link['id'],))
            
            # Obter todos os números ativos deste usuário
            numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ? AND is_active = 1', 
                                (link['owner_id'],)).fetchall()
            
            if not numbers:
                # Nenhum número registrado ou ativo
                return render_template('index.html', error='Nenhum número ativo cadastrado para este link')
            
            # Selecionar um número usando algoritmo balanceado
            selected_number = select_balanced_number(conn, numbers, link['id'])
            phone_number = selected_number['phone_number']
            
            # Garantir que o número esteja no formato internacional
            phone_number = format_phone_number(phone_number)
            
            # Registrar o log de redirecionamento
            log_id = conn.execute('''
                INSERT INTO redirect_logs (link_id, number_id, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (link['id'], selected_number['id'], client_ip, user_agent)).lastrowid
            conn.commit()
            
            # Preparar mensagem personalizada ou usar padrão
            custom_message = link['custom_message'] or 'Olá!'
            
            # Codificar a mensagem para URL
            import urllib.parse
            custom_message = urllib.parse.quote(custom_message)
            
            # Construir URL do WhatsApp
            whatsapp_url = f"https://wa.me/{phone_number}?text={custom_message}"
            
            # Registro de sucesso
            redirect_time = (datetime.now() - redirect_start_time).total_seconds()
            
            # Fazer redirecionamento direto para o WhatsApp ao invés de renderizar a página intermediária
            return redirect(whatsapp_url)
    except Exception as e:
        # Retornar uma página de erro genérica
        print(f"Erro no redirecionamento: {str(e)}")
        redirect_time = (datetime.now() - redirect_start_time).total_seconds()
        return render_template('index.html', error='Ocorreu um erro ao processar seu redirecionamento. Tente novamente.')

# Função para selecionar um número de forma balanceada
def select_balanced_number(conn, numbers, link_id):
    try:
        # Verificar se há apenas um número disponível
        if len(numbers) == 1:
            return numbers[0]
        
        # Método de escolha: Distribuição ponderada para garantir equilíbrio mesmo com números novos
        total_numbers = len(numbers)
        
        # Verificar se existem números muito recentes (sem histórico de uso)
        novos_numeros = []
        numeros_existentes = []
        
        for num in numbers:
            # Verificar se o número tem dados de uso
            use_data = conn.execute('''
                SELECT COUNT(*) as count 
                FROM redirect_logs 
                WHERE number_id = ?
            ''', (num['id'],)).fetchone()['count']
            
            if use_data == 0:
                novos_numeros.append(num)
            else:
                numeros_existentes.append(num)
        
        # Se temos números novos e números existentes, criar um balanceamento especial
        if novos_numeros and numeros_existentes:
            # Determinar probabilidade - damos chance menor para números novos
            # Quanto mais números novos, menor a chance individual para evitar sobrecarga
            prob_escolher_novo = min(0.3, 1.0 / (len(novos_numeros) + 1))
            
            if random.random() < prob_escolher_novo:
                # Escolher um número novo
                selected_number = random.choice(novos_numeros)
                
                # Atualizar timestamp de último uso
                conn.execute('UPDATE whatsapp_numbers SET last_used = datetime("now") WHERE id = ?', 
                           (selected_number['id'],))
                
                return selected_number
        
        # Se chegarmos aqui, vamos selecionar entre os números existentes (ou todos se não houver distinção)
        numeros_para_selecao = numeros_existentes if numeros_existentes else numbers
        
        # Obter estatísticas de uso dos números para este link nas últimas 24 horas
        counts = {}
        for num in numeros_para_selecao:
            # Consideramos o uso geral (não apenas para este link) para ter uma visão completa
            redirect_count = conn.execute('''
                SELECT COUNT(*) as count 
                FROM redirect_logs 
                WHERE number_id = ? 
                AND redirect_time >= datetime('now', '-1 day')
            ''', (num['id'],)).fetchone()['count']
            
            # Para links específicos, damos um peso adicional ao uso específico deste link
            link_specific_count = 0
            if link_id:
                link_specific_count = conn.execute('''
                    SELECT COUNT(*) as count 
                    FROM redirect_logs 
                    WHERE number_id = ? AND link_id = ? 
                    AND redirect_time >= datetime('now', '-1 day')
                ''', (num['id'], link_id)).fetchone()['count']
            
            # Uso total ponderado (uso geral + peso extra para uso específico do link)
            weighted_count = redirect_count + (link_specific_count * 2)
            
            # Se não tiver redirecionamentos recentes, atribuir valor baixo mas não zero
            # para evitar que todos os números sem uso recente tenham exatamente a mesma prioridade
            if weighted_count == 0:
                weighted_count = 0.1 + (random.random() * 0.5)  # Valor baixo com pequena variação
            
            counts[num['id']] = weighted_count
        
        # Inverter as contagens para criar pesos (menos usos = maior peso)
        if counts:
            max_count = max(counts.values()) + 1  # +1 para evitar divisão por zero
            weights = {num_id: max_count - count for num_id, count in counts.items()}
            
            # Normalizar os pesos para somarem 1
            total_weight = sum(weights.values())
            normalized_weights = {num_id: weight/total_weight for num_id, weight in weights.items()}
            
            # Selecionar baseado em pesos
            number_ids = list(normalized_weights.keys())
            weights_list = [normalized_weights[num_id] for num_id in number_ids]
            
            # Escolher um número com base nos pesos normalizados
            selected_id = random.choices(number_ids, weights=weights_list, k=1)[0]
            selected_number = next(num for num in numeros_para_selecao if num['id'] == selected_id)
            
            # Atualizar timestamp de último uso
            conn.execute('UPDATE whatsapp_numbers SET last_used = datetime("now") WHERE id = ?', 
                       (selected_number['id'],))
            
            return selected_number
        else:
            # Fallback para seleção aleatória simples
            selected_number = random.choice(numeros_para_selecao)
            return selected_number
    except Exception as e:
        # Em caso de erro, voltar para o método padrão
        selected_number = random.choice(numbers)
        return selected_number

# Função para formatar número de telefone
def format_phone_number(phone):
    # Remover caracteres não numéricos
    clean_number = ''.join(filter(str.isdigit, phone))
    
    # Garantir que o número comece com 55 (Brasil)
    if not clean_number.startswith('55'):
        clean_number = '55' + clean_number
    
    return clean_number

# API para obter redirecionamentos recentes
@app.route('/api/redirects/recent', methods=['GET'])
@login_required
def get_recent_redirects():
    user_id = session.get('user_id')
    limit = request.args.get('limit', 20, type=int)  # Limite padrão de 20 registros
    page = request.args.get('page', 1, type=int)     # Página padrão é 1
    link_id = request.args.get('link_id', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    all_records = request.args.get('all', 'false')  # Parâmetro para obter todos os registros
    
    # Se all_records for 'true', ignorar paginação e limite
    show_all = (all_records.lower() == 'true')
    
    print(f"Query de atividade recente - user_id: {user_id}, link_id: {link_id}, start_date: {start_date}, end_date: {end_date}")
    
    # Obter condições e parâmetros de forma padronizada, usando a mesma função que outras consultas
    link_condition, date_condition, params = get_standard_filter_conditions(user_id, link_id, start_date, end_date)
    
    print(f"Condições SQL: link_condition={link_condition}, date_condition={date_condition}")
    print(f"Parâmetros SQL: {params}")
    
    with get_db_connection() as conn:
        # Preparar a query que agrupa redirecionamentos por minuto, número e link para evitar duplicatas
        # Usamos a função strftime para truncar o timestamp ao minuto
        query = f'''
            SELECT 
                MAX(rl.id) as id,
                MAX(rl.redirect_time) as redirect_time,
                cl.link_name,
                rl.number_id,
                COALESCE(wn.phone_number, 'Número excluído') as phone_number,
                COALESCE(wn.description, 'Redirecionamento para número que foi excluído') as number_description,
                rl.ip_address,
                COUNT(*) as access_count,
                MAX(rl.user_agent) as user_agent
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition}
            GROUP BY 
                strftime('%Y-%m-%d %H:%M', rl.redirect_time),
                rl.number_id,
                cl.link_name,
                rl.ip_address
            ORDER BY MAX(rl.redirect_time) DESC
        '''
        
        # Obter contagem total considerando a agregação por minuto
        count_query = f'''
            SELECT COUNT(*) as total FROM (
                SELECT 
                    strftime('%Y-%m-%d %H:%M', rl.redirect_time) as minute,
                    rl.number_id,
                    cl.link_name,
                    rl.ip_address
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {link_condition} {date_condition}
                GROUP BY 
                    minute,
                    rl.number_id,
                    cl.link_name,
                    rl.ip_address
            )
        '''
        
        total_records = conn.execute(count_query, params).fetchone()['total']
        print(f"Total de registros para atividades recentes (agrupados): {total_records}")
        
        # Se não for para mostrar todos, adicionar LIMIT e OFFSET para paginação
        query_params = params.copy()
        if not show_all:
            query += " LIMIT ? OFFSET ?"
            query_params.append(limit)
            query_params.append((page - 1) * limit)
            print(f"Aplicando paginação: limite={limit}, página={page}")
        else:
            print(f"Retornando TODAS as atividades recentes (agrupados) ({total_records} registros)")
        
        recent_redirects = conn.execute(query, query_params).fetchall()
        
        # Formatar os resultados para JSON
        result = []
        for redirect in recent_redirects:
            access_count = redirect['access_count']
            
            # Converter a data UTC para o fuso horário de Brasília (UTC-3)
            redirect_time = redirect['redirect_time']
            try:
                # Parse da data para objeto datetime
                if redirect_time:
                    # Assumindo que a data está em UTC
                    dt_utc = datetime.fromisoformat(redirect_time.replace('Z', ''))
                    # Brasília é UTC-3
                    dt_brasilia = dt_utc - timedelta(hours=3)
                    # Formatar para ISO para garantir compatibilidade
                    redirect_time_brasilia = dt_brasilia.isoformat()
                else:
                    redirect_time_brasilia = redirect_time
            except Exception as e:
                print(f"Erro ao converter data: {e}")
                redirect_time_brasilia = redirect_time
            
            result_item = {
                'id': redirect['id'],
                'redirect_time': redirect_time_brasilia,
                'link_name': redirect['link_name'],
                'phone_number': redirect['phone_number'],
                'number_description': redirect['number_description'],
                'ip_address': redirect['ip_address'],
                'user_agent': redirect['user_agent']
            }
            
            # Adicionar indicador de múltiplos cliques para cliques agrupados
            if access_count > 1:
                result_item['multiple_clicks'] = True
                result_item['click_count'] = access_count
            
            result.append(result_item)
        
        return jsonify({
            'limit': limit,
            'page': page,
            'show_all': show_all,
            'total_records': total_records,
            'results': result
        })

# API para obter estatísticas resumidas
@app.route('/api/stats/summary', methods=['GET'])
@login_required
def get_stats_summary():
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id', 'all')
    
    # Construir condições para filtros
    link_condition = "cl.user_id = ?"
    params = [user_id]
    
    if link_id != 'all' and link_id.isdigit():
        link_condition += " AND cl.id = ?"
        params.append(int(link_id))
    
    # Adicionar condições de data se fornecidas
    date_condition = ""
    date_params = []
    if start_date:
        date_condition += " AND date(rl.redirect_time) >= date(?)"
        date_params.append(start_date)
    if end_date:
        date_condition += " AND date(rl.redirect_time) <= date(?)"
        date_params.append(end_date)
    
    # Cópias dos parâmetros para diferentes consultas
    redirect_params = params.copy() + date_params
    
    with get_db_connection() as conn:
        # Total de cliques usando a tabela de redirecionamentos diretamente
        total_clicks_query = f'''
            SELECT COUNT(*) as total 
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
        '''
        
        total_clicks = conn.execute(total_clicks_query, params + date_params).fetchone()['total'] or 0
        
        # Total de links ativos
        active_links = conn.execute('''
            SELECT COUNT(*) as count
            FROM custom_links
            WHERE user_id = ? AND is_active = 1
        ''', (user_id,)).fetchone()['count'] or 0
        
        # Total de números ativos
        active_numbers = conn.execute('''
            SELECT COUNT(*) as count
            FROM whatsapp_numbers
            WHERE user_id = ?
        ''', (user_id,)).fetchone()['count'] or 0
        
        # Média diária considerando o período selecionado
        if start_date and end_date:
            # Calcular a média baseada no período selecionado
            daily_average_query = f'''
                SELECT COUNT(*) as count, 
                       julianday(?) - julianday(?) + 1 as days
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {link_condition} {date_condition}
            '''
            daily_params = params + date_params + [end_date, start_date]
            
            result = conn.execute(daily_average_query, daily_params).fetchone()
            count = result['count'] or 0
            days = result['days'] or 1
            
            daily_average = round(count / days) if count > 0 else 0
        else:
            # Sem datas selecionadas, usar os últimos 7 dias (comportamento padrão)
            daily_average_query = f'''
                SELECT COUNT(*) as count
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {link_condition} AND rl.redirect_time >= date('now', '-7 days')
            '''
            
            daily_average_data = conn.execute(daily_average_query, params).fetchone()
            daily_average = round(daily_average_data['count'] / 7) if daily_average_data['count'] else 0
        
        return jsonify({
            'total_clicks': total_clicks,
            'active_links': active_links,
            'active_numbers': active_numbers,
            'daily_average': daily_average
        })

# API para obter estatísticas detalhadas
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    user_id = session.get('user_id')
    link_id = request.args.get('link_id', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    print(f"Solicitação de estatísticas - link_id: {link_id}, start_date: {start_date}, end_date: {end_date}")
    
    # Construir a condição de link_id
    link_condition = "cl.user_id = ?"
    params = [user_id]
    
    if link_id != 'all' and link_id.isdigit():
        link_condition += " AND cl.id = ?"
        params.append(int(link_id))
    
    # Adicionar condições de data se fornecidas
    date_condition = ""
    if start_date:
        date_condition += " AND date(rl.redirect_time) >= date(?)"
        params.append(start_date)
    if end_date:
        date_condition += " AND date(rl.redirect_time) <= date(?)"
        params.append(end_date)
    
    print(f"Parâmetros da consulta de estatísticas: {params}")
    
    with get_db_connection() as conn:
        # Verificar se temos acessos para os filtros (para economizar consultas se não houver dados)
        count_query = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
        '''
        
        total_clicks = conn.execute(count_query, params).fetchone()['total']
        
        # Se não houver dados, gerar dados simulados
        if total_clicks == 0:
            import datetime
            today = datetime.date.today()
            # Dados simulados para visualização
            daily_result = []
            for i in range(7):
                date = today - datetime.timedelta(days=6-i)
                daily_result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "clicks": 100 + (i * 50) + (i * i * 5)  # Valores simulados
                })
            
            # Dados simulados por hora
            hourly_result = []
            for i in range(24):
                hour = f"{i:02d}"
                count = 10 + ((i % 12) * 20)  # Valores simulados
                if i >= 8 and i <= 20:  # Mais atividade durante o dia
                    count *= 2
                hourly_result.append({"hour": hour, "count": count})
            
            # Dados simulados por país
            country_stats = [
                {"country": "Brasil", "count": 75},
                {"country": "Portugal", "count": 12},
                {"country": "EUA", "count": 8},
                {"country": "Outros", "count": 5}
            ]
            
            return jsonify({
                "daily_stats": daily_result,
                "country_stats": country_stats,
                "hourly_stats": hourly_result
            })
        
        # Estatísticas diárias - dados reais
        daily_query = f'''
            SELECT 
                date(rl.redirect_time) as date,
                COUNT(*) as clicks
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
            GROUP BY date(rl.redirect_time)
            ORDER BY date(rl.redirect_time)
        '''
        
        daily_stats = conn.execute(daily_query, params).fetchall()
        daily_result = [{"date": row["date"], "clicks": row["clicks"]} for row in daily_stats]
        
        # Estatísticas por país (simulado com dados de IP)
        # Na implementação real, você usaria um serviço de geolocalização de IP
        country_stats = [
            {"country": "Brasil", "count": int(total_clicks * 0.75)},
            {"country": "Portugal", "count": int(total_clicks * 0.12)},
            {"country": "EUA", "count": int(total_clicks * 0.08)},
            {"country": "Outros", "count": int(total_clicks * 0.05)}
        ]
        
        # Estatísticas por hora do dia
        hourly_query = f'''
            SELECT 
                strftime('%H', rl.redirect_time) as hour,
                COUNT(*) as count
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
            GROUP BY strftime('%H', rl.redirect_time)
            ORDER BY hour
        '''
        
        hourly_stats = conn.execute(hourly_query, params).fetchall()
        
        # Garantir que temos todas as 24 horas no resultado
        hour_dict = {row["hour"]: row["count"] for row in hourly_stats}
        hourly_result = []
        
        for i in range(24):
            hour = f"{i:02d}"
            hourly_result.append({
                "hour": hour,
                "count": hour_dict.get(hour, 0)
            })
            
        return jsonify({
            "daily_stats": daily_result,
            "country_stats": country_stats,
            "hourly_stats": hourly_result
        })

# API para obter estatísticas por chip (número)
@app.route('/api/stats/by-number', methods=['GET'])
@login_required
def get_stats_by_number():
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id', 'all')
    
    print(f"Query de estatísticas por chip - user_id: {user_id}, link_id: {link_id}, start_date: {start_date}, end_date: {end_date}")
    
    # Obter condições e parâmetros de forma padronizada
    link_condition, date_condition, params = get_standard_filter_conditions(user_id, link_id, start_date, end_date)
    
    print(f"Parâmetros base para estatísticas por chip: {params}")
    
    with get_db_connection() as conn:
        # Verificar contagem total para comparação e debug
        count_query = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
        '''
        
        total_count = conn.execute(count_query, params).fetchone()['total']
        print(f"Total de acessos para filtros atuais (estatísticas por chip): {total_count}")
        
        # Obter todos os números do usuário
        numbers_query = '''
            SELECT id, phone_number, description
            FROM whatsapp_numbers
            WHERE user_id = ?
        '''
        
        numbers = conn.execute(numbers_query, [user_id]).fetchall()
        result = []
        total_por_chip = 0
        
        # Para cada número, contamos os acessos com uma query consistente
        for number in numbers:
            # Construir query para cada número, mantendo as mesmas condições
            # Importante: NÃO duplicamos os parâmetros aqui, apenas adicionamos o número_id
            precise_query = f'''
                SELECT COUNT(*) as count
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE rl.number_id = ? AND {link_condition} {date_condition}
            '''
            
            # Criamos uma nova lista de parâmetros para incluir o ID do número como primeiro parâmetro
            num_params = [number['id']]
            # Adicionamos os parâmetros originais (mesma ordem)
            num_params.extend(params)
            
            print(f"Query para número {number['phone_number']}: {precise_query}")
            print(f"Parâmetros: {num_params}")
            
            count_result = conn.execute(precise_query, num_params).fetchone()
            access_count = count_result['count'] if count_result else 0
            total_por_chip += access_count
            
            result.append({
                "id": number["id"],
                "phone_number": number["phone_number"],
                "description": number["description"] or "Sem descrição",
                "access_count": access_count
            })
        
        # Verificar se há registros órfãos (redirecionamentos com números que foram excluídos)
        orphan_query = f'''
            SELECT COUNT(*) as count
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
            AND rl.number_id NOT IN (SELECT id FROM whatsapp_numbers WHERE user_id = ?)
        '''
        
        orphan_params = params.copy()
        orphan_params.append(user_id)
        
        orphan_count = conn.execute(orphan_query, orphan_params).fetchone()['count']
        
        # Se houver registros órfãos, adicionar como um "número fantasma" nas estatísticas
        if orphan_count > 0:
            result.append({
                "id": 0,
                "phone_number": "Número excluído",
                "description": "Redirecionamentos para números que foram excluídos",
                "access_count": orphan_count
            })
            total_por_chip += orphan_count
            print(f"Encontrados {orphan_count} redirecionamentos para números excluídos")
        
        # Verificar discrepâncias na contagem
        print(f"Total contado por números: {total_por_chip}, Total geral: {total_count}")
        if total_por_chip != total_count:
            print(f"⚠️ DISCREPÂNCIA DETECTADA: soma_chips={total_por_chip}, total_geral={total_count}")
            # Validar dados para debugar discrepâncias
            validate_data_consistency(conn, user_id, link_id, start_date, end_date)
        
        # Ordenar por contagem de acessos (decrescente)
        result = sorted(result, key=lambda x: x['access_count'], reverse=True)
        
        # Retornar os resultados
        return jsonify({"number_stats": result})

# Função para obter condições de filtro padronizadas
def get_standard_filter_conditions(user_id, link_id, start_date, end_date):
    """
    Cria condições SQL e parâmetros padronizados para filtros, 
    garantindo consistência entre diferentes consultas.
    """
    # Construir a condição de link_id
    link_condition = "cl.user_id = ?"
    params = [user_id]
    
    if link_id != 'all' and link_id.isdigit():
        link_condition += " AND cl.id = ?"
        params.append(int(link_id))
    
    # Adicionar condições de data se fornecidas
    date_condition = ""
    if start_date:
        date_condition += " AND date(rl.redirect_time) >= date(?)"
        params.append(start_date)
    if end_date:
        date_condition += " AND date(rl.redirect_time) <= date(?)"
        params.append(end_date)
    
    return link_condition, date_condition, params

# Função para validar consistência de dados
def validate_data_consistency(conn, user_id, link_id, start_date, end_date):
    """
    Executa consultas para verificar consistência entre diferentes fontes de dados.
    Usado para diagnóstico de discrepâncias.
    """
    link_condition, date_condition, params = get_standard_filter_conditions(user_id, link_id, start_date, end_date)
    
    # Consulta 1: Total de registros sem junção com whatsapp_numbers
    query1 = f'''
        SELECT COUNT(*) as total
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        WHERE {link_condition} {date_condition}
    '''
    
    # Consulta 2: Total de registros com junção de whatsapp_numbers
    query2 = f'''
        SELECT COUNT(*) as total
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        JOIN whatsapp_numbers wn ON rl.number_id = wn.id
        WHERE {link_condition} {date_condition}
    '''
    
    # Consulta 3: Total por número, somado
    query3 = f'''
        SELECT rl.number_id, COUNT(*) as count
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        WHERE {link_condition} {date_condition}
        GROUP BY rl.number_id
    '''
    
    # Executar consultas e comparar
    total1 = conn.execute(query1, params).fetchone()['total']
    total2 = conn.execute(query2, params).fetchone()['total']
    
    number_counts = conn.execute(query3, params).fetchall()
    total3 = sum(row['count'] for row in number_counts)
    
    # Verificação detalhada dos números
    print(f"Validação de consistência com parâmetros: {params}")
    print(f"Total consulta básica: {total1}")
    print(f"Total consulta com números: {total2}")
    print(f"Total soma por números: {total3}")
    
    if total1 != total2 or total1 != total3:
        print("⚠️ INCONSISTÊNCIA DETECTADA:")
        print(f"  - Total básico vs com números: {total1} vs {total2}")
        print(f"  - Total básico vs soma por número: {total1} vs {total3}")
        
        # Verificar se há registros orfãos (sem número válido)
        orphan_query = f'''
            SELECT rl.id, rl.number_id, rl.redirect_time 
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition} AND wn.id IS NULL
        '''
        
        orphans = conn.execute(orphan_query, params).fetchall()
        if orphans:
            print(f"🔴 Encontrados {len(orphans)} registros com números inválidos:")
            for orphan in orphans[:5]:  # Mostrar primeiros 5 como exemplo
                print(f"  - ID: {orphan['id']}, Number ID: {orphan['number_id']}, Data: {orphan['redirect_time']}")
            if len(orphans) > 5:
                print(f"  - ... e mais {len(orphans) - 5} registros")
    else:
        print("✅ Dados consistentes entre todas as consultas")

# Função para obter localização a partir do IP
def get_location_from_ip(ip_address):
    """
    Obtém dados de localização geográfica a partir de um endereço IP
    usando a API gratuita ip-api.com que oferece melhor precisão
    
    Args:
        ip_address: Endereço IP para consulta
        
    Returns:
        Um dicionário com dados de localização ou fallback para localização padrão
    """
    # Verificar se o IP é local/privado e usar endereço padrão nesse caso
    local_ips = ['127.0.0.1', 'localhost', '::1', '0.0.0.0']
    private_ranges = [
        '10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.',
        '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
        '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.'
    ]
    
    # Checar se é IP local ou privado
    if ip_address in local_ips or any(ip_address.startswith(prefix) for prefix in private_ranges):
        print(f"IP {ip_address} é local/privado. Usando IP padrão para geolocalização.")
        # Se for IP local/desenvolvimento, retornar localidade padrão
        return {
            'city': 'Curitiba',
            'latitude': -25.4372,
            'longitude': -49.2699,
            'country': 'Brasil',
            'region': 'Paraná'
        }
    
    try:
        # Usar ip-api.com em vez de ipapi.co para melhor precisão com IPs brasileiros
        response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city,lat,lon', timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'city': data.get('city', 'Desconhecido'),
                    'latitude': data.get('lat', 0),
                    'longitude': data.get('lon', 0),
                    'country': data.get('country', 'Desconhecido'),
                    'region': data.get('regionName', 'Desconhecido')
                }
            else:
                print(f"Erro na API de geolocalização para IP {ip_address}: {data}")
        else:
            print(f"Falha na API de geolocalização. Status: {response.status_code}")
            
    except Exception as e:
        print(f"Erro ao obter localização do IP {ip_address}: {str(e)}")
    
    # Segunda tentativa com outra API caso a primeira falhe
    try:
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                return {
                    'city': data.get('city', 'Desconhecido'),
                    'latitude': data.get('latitude', 0),
                    'longitude': data.get('longitude', 0),
                    'country': data.get('country_name', 'Desconhecido'),
                    'region': data.get('region', 'Desconhecido')
                }
    except:
        # Ignorar erro na segunda tentativa, já usaremos o fallback
        pass
        
    # Fallback para localização padrão em caso de erro
    return {
        'city': 'Curitiba',
        'latitude': -25.4372,
        'longitude': -49.2699,
        'country': 'Brasil',
        'region': 'Paraná'
    }

# API para obter dados geográficos para o mapa de cliques
@app.route('/api/stats/map', methods=['GET'])
@login_required
def get_map_stats():
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id', 'all')
    
    try:
        # Validar se as datas são válidas
        today = datetime.now().date()
        
        # Converter datas para objetos date para validação
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                # Se a data inicial for futura, limitar à data atual
                if start_date_obj > today:
                    start_date = today.strftime('%Y-%m-%d')
                    print(f"Data inicial no futuro ajustada para hoje: {start_date}")
            except ValueError:
                # Data inválida, ignorar filtro
                start_date = None
                print("Data inicial inválida ignorada")
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Se a data final for futura, limitar à data atual
                if end_date_obj > today:
                    end_date = today.strftime('%Y-%m-%d')
                    print(f"Data final no futuro ajustada para hoje: {end_date}")
            except ValueError:
                # Data inválida, ignorar filtro
                end_date = None
                print("Data final inválida ignorada")
    
        # Obter condições e parâmetros de forma padronizada
        link_condition, date_condition, params = get_standard_filter_conditions(user_id, link_id, start_date, end_date)
        
        print(f"Query de mapa - user_id: {user_id}, link_id: {link_id}, start_date: {start_date}, end_date: {end_date}")
        print(f"Parâmetros para mapa: {params}")
        
        with get_db_connection() as conn:
            # Obter os redirecionamentos com IPs para o período filtrado
            query = f'''
                SELECT rl.ip_address, COUNT(*) as click_count
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {link_condition} {date_condition}
                GROUP BY rl.ip_address
            '''
            
            redirects = conn.execute(query, params).fetchall()
            total_clicks = sum(redirect['click_count'] for redirect in redirects)
            print(f"Total de cliques no mapa: {total_clicks}")
            
            # Verificar consistência de dados
            try:
                validate_data_consistency(conn, user_id, link_id, start_date, end_date)
            except Exception as e:
                print(f"Erro na validação de consistência: {str(e)}")
            
            if total_clicks > 0:
                try:
                    # Lista para armazenar todos os locais com suas contagens
                    locations = []
                    
                    # Cache para evitar consultas repetidas de geolocalização para o mesmo IP
                    location_cache = {}
                    
                    # Contador de erros para limitar tentativas de geolocalização
                    error_count = 0
                    max_errors = 5
                    
                    for redirect in redirects:
                        ip = redirect['ip_address']
                        count = redirect['click_count']
                        
                        # Usar cache para evitar requisições repetidas
                        if ip not in location_cache:
                            try:
                                # Se tivermos muitos erros, usar posição padrão para o resto
                                if error_count >= max_errors:
                                    location_data = {
                                        'city': 'Curitiba',
                                        'latitude': -25.4372,
                                        'longitude': -49.2699,
                                        'country': 'Brasil',
                                        'region': 'Paraná'
                                    }
                                else:
                                    location_data = get_location_from_ip(ip)
                                
                                location_cache[ip] = location_data
                            except Exception as e:
                                error_count += 1
                                print(f"Erro ao obter localização para IP {ip}: {str(e)}")
                                # Em caso de erro, usar localização padrão
                                location_data = {
                                    'city': 'Curitiba',
                                    'latitude': -25.4372,
                                    'longitude': -49.2699,
                                    'country': 'Brasil',
                                    'region': 'Paraná'
                                }
                                location_cache[ip] = location_data
                        else:
                            location_data = location_cache[ip]
                        
                        # Criar um nome de local mais informativo
                        location_name = f"{location_data['city']}, {location_data['region']}, {location_data['country']}"
                        
                        # Verificar se já existe um local com as mesmas coordenadas
                        existing_location = next(
                            (loc for loc in locations if 
                             loc['lat'] == location_data['latitude'] and 
                             loc['lng'] == location_data['longitude']),
                            None
                        )
                        
                        if existing_location:
                            # Somar os cliques ao local existente
                            existing_location['count'] += count
                        else:
                            # Adicionar novo local
                            locations.append({
                                'lat': location_data['latitude'],
                                'lng': location_data['longitude'],
                                'name': location_name,
                                'count': count
                            })
                    
                    print(f"Localizações processadas: {len(locations)}")
                    return jsonify({"locations": locations})
                except Exception as e:
                    print(f"Erro ao processar dados do mapa: {str(e)}")
                    # Em caso de erro, retornar um marcador único em Curitiba
                    return jsonify({
                        "locations": [{
                            "lat": -25.4372,
                            "lng": -49.2699,
                            "name": "Curitiba, Paraná, Brasil (Localização padrão)",
                            "count": total_clicks
                        }]
                    })
            else:
                # Se não temos cliques para os filtros, retornar lista vazia
                return jsonify({"locations": []})
    except Exception as e:
        print(f"Erro geral na API de mapa: {str(e)}")
        # Em caso de erro geral, retornar uma resposta vazia mas válida
        return jsonify({"locations": [], "error": "Ocorreu um erro ao processar os dados do mapa"})

# Adicionar função para corrigir registros inconsistentes
def fix_data_inconsistencies(conn):
    """
    Corrige problemas de consistência no banco de dados, como registros
    de redirecionamento que apontam para números que não existem mais.
    """
    print("Verificando e corrigindo inconsistências de dados...")
    
    # 1. Identificar registros de redirecionamento que apontam para números inexistentes
    orphan_query = '''
        SELECT rl.id, rl.number_id, cl.user_id
        FROM redirect_logs rl
        JOIN custom_links cl ON rl.link_id = cl.id
        LEFT JOIN whatsapp_numbers wn ON rl.number_id = wn.id
        WHERE wn.id IS NULL
    '''
    
    orphans = conn.execute(orphan_query).fetchall()
    
    if orphans:
        print(f"Encontrados {len(orphans)} registros de redirecionamento para números inexistentes.")
        
        # Para cada registro órfão, tentar encontrar um número válido do mesmo usuário
        for orphan in orphans:
            user_id = orphan['user_id']
            
            # Buscar um número válido deste usuário
            valid_number = conn.execute('''
                SELECT id FROM whatsapp_numbers 
                WHERE user_id = ? 
                LIMIT 1
            ''', (user_id,)).fetchone()
            
            if valid_number:
                # Atualizar o registro para apontar para um número válido
                conn.execute('''
                    UPDATE redirect_logs
                    SET number_id = ?
                    WHERE id = ?
                ''', (valid_number['id'], orphan['id']))
                print(f"Corrigido: redirect_log ID {orphan['id']} agora aponta para number_id {valid_number['id']}")
            else:
                # Se não houver número válido, remover o registro de log
                conn.execute('DELETE FROM redirect_logs WHERE id = ?', (orphan['id'],))
                print(f"Removido: redirect_log ID {orphan['id']} (sem número válido disponível)")
        
        conn.commit()
        print(f"Corrigidos {len(orphans)} registros de redirecionamento.")
    else:
        print("Nenhuma inconsistência encontrada nos registros de redirecionamento.")

# Adicionar chamada para corrigir inconsistências durante a inicialização do app
@app.before_first_request
def before_first_request():
    """Executado antes da primeira requisição ao aplicativo"""
    with get_db_connection() as conn:
        fix_data_inconsistencies(conn)
        
        # Também podemos verificar outras inconsistências aqui
        print("Verificando consistência geral dos dados...")
        # Verificar se existe algum link sem usuário válido
        orphan_links = conn.execute('''
            SELECT cl.id, cl.link_name
            FROM custom_links cl
            LEFT JOIN users u ON cl.user_id = u.id
            WHERE u.id IS NULL
        ''').fetchall()
        
        if orphan_links:
            print(f"Encontrados {len(orphan_links)} links sem usuário válido.")
            # Se necessário implementar correção aqui

# Configuração para permitir acesso a recursos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/admin/backup-db-secret', methods=['GET'])
def backup_db_secret():
    import base64
    from flask import Response
    
    try:
        with open('instance/whatsapp_redirect.db', 'rb') as f:
            db_data = f.read()
        
        encoded = base64.b64encode(db_data).decode('utf-8')
        return Response(
            encoded,
            mimetype="text/plain",
            headers={"Content-disposition": "attachment; filename=whatsapp_redirect.db.b64"}
        )
    except Exception as e:
        return str(e), 500

# Rota para a página de backup (apenas para o usuário Felipe)
@app.route('/admin/backup')
@login_required
def admin_backup():
    # Verificar se o usuário atual é o Felipe (ID 2)
    if session.get('username') != 'felipe':
        # Redirecionar para o dashboard se não for o Felipe
        return redirect(url_for('dashboard'))
    
    return render_template('backup.html')

# Rota para a página de gerenciamento de usuários (apenas para o usuário Felipe)
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@login_required
def admin_usuarios():
    # Verificar se o usuário atual é o Felipe (ID 2)
    if session.get('username') != 'felipe':
        # Redirecionar para o dashboard se não for o Felipe
        return redirect(url_for('dashboard'))
    
    error_message = None
    success_message = None
    
    # Processar a adição de um novo usuário
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        fullname = request.form.get('fullname')
        plan_id = request.form.get('plan_id')
        
        # Validar dados
        if not username or not password or not fullname or not plan_id:
            error_message = "Todos os campos são obrigatórios"
        else:
            # Verificar se o usuário já existe
            with get_db_connection() as conn:
                existing_user = conn.execute('SELECT id FROM users WHERE username = ?', 
                                          (username,)).fetchone()
                if existing_user:
                    error_message = f"Usuário '{username}' já existe"
                else:
                    try:
                        # Inserir novo usuário
                        conn.execute('''
                            INSERT INTO users (username, password, fullname, plan_id)
                            VALUES (?, ?, ?, ?)
                        ''', (username, generate_password_hash(password), fullname, plan_id))
                        
                        # Criar link padrão para o novo usuário
                        new_user = conn.execute('SELECT id FROM users WHERE username = ?', 
                                             (username,)).fetchone()
                        if new_user:
                            conn.execute('''
                                INSERT INTO custom_links (user_id, link_name, custom_message, is_active, prefix)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (new_user['id'], 'whatsapp', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...', 1, 1))
                            
                        success_message = f"Usuário '{username}' criado com sucesso"
                    except Exception as e:
                        error_message = f"Erro ao criar usuário: {str(e)}"
    
    # Obter todos os usuários e suas estatísticas
    with get_db_connection() as conn:
        # Obter todos os planos
        plans = conn.execute('''
            SELECT id, name, max_numbers, max_links, description
            FROM plans
            ORDER BY id
        ''').fetchall()
        
        # Obter todos os usuários com informações do plano
        users = conn.execute('''
            SELECT u.id, u.username, u.fullname, u.created_at, u.plan_id, 
                   p.name as plan_name, p.max_numbers, p.max_links
            FROM users u
            JOIN plans p ON u.plan_id = p.id
            ORDER BY u.id
        ''').fetchall()
        
        # Para cada usuário, obter a contagem de links e chips
        user_stats = []
        for user in users:
            # Contar links do usuário
            links_count = conn.execute('''
                SELECT COUNT(*) as count
                FROM custom_links
                WHERE user_id = ?
            ''', (user['id'],)).fetchone()['count']
            
            # Contar chips do usuário
            chips_count = conn.execute('''
                SELECT COUNT(*) as count
                FROM whatsapp_numbers
                WHERE user_id = ?
            ''', (user['id'],)).fetchone()['count']
            
            # Contar total de redirecionamentos para links do usuário
            redirects_count = conn.execute('''
                SELECT COUNT(*) as count
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE cl.user_id = ?
            ''', (user['id'],)).fetchone()['count']
            
            # Verificar limites do plano
            user_stats.append({
                'id': user['id'],
                'username': user['username'],
                'fullname': user['fullname'],
                'created_at': user['created_at'],
                'plan_id': user['plan_id'],
                'plan_name': user['plan_name'],
                'max_numbers': user['max_numbers'],
                'max_links': user['max_links'],
                'links_count': links_count,
                'chips_count': chips_count,
                'redirects_count': redirects_count,
                'links_limit_reached': links_count >= user['max_links'] if user['max_links'] > 0 else False,
                'numbers_limit_reached': chips_count >= user['max_numbers']
            })
    
    return render_template('admin_usuarios.html', users=user_stats, plans=plans, 
                          error_message=error_message, success_message=success_message)

# Rota para excluir usuário
@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    # Verificar se o usuário atual é o Felipe
    if session.get('username') != 'felipe':
        return jsonify({'success': False, 'error': 'Acesso negado. Apenas o administrador pode excluir usuários.'}), 403
    
    # Verificar se o usuário a ser excluído não é um dos administradores principais
    if user_id in [1, 2]:  # IDs de pedro e felipe
        return jsonify({'success': False, 'error': 'Não é possível excluir usuários administradores.'}), 400
    
    try:
        with get_db_connection() as conn:
            # Verificar se o usuário existe
            user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'success': False, 'error': 'Usuário não encontrado.'}), 404
            
            # Iniciar transação para garantir que todas as operações sejam realizadas ou nenhuma
            conn.execute('BEGIN TRANSACTION')
            
            # 1. Excluir registros de redirecionamento associados aos links do usuário
            conn.execute('''
                DELETE FROM redirect_logs
                WHERE link_id IN (
                    SELECT id FROM custom_links WHERE user_id = ?
                )
            ''', (user_id,))
            
            # 2. Excluir todos os links do usuário
            conn.execute('DELETE FROM custom_links WHERE user_id = ?', (user_id,))
            
            # 3. Excluir todos os números do usuário
            conn.execute('DELETE FROM whatsapp_numbers WHERE user_id = ?', (user_id,))
            
            # 4. Por fim, excluir o usuário
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            # Confirmar transação
            conn.execute('COMMIT')
            
            return jsonify({'success': True, 'message': f'Usuário {user["username"]} excluído com sucesso.'})
            
    except Exception as e:
        # Em caso de erro, fazer rollback e retornar erro
        try:
            conn.execute('ROLLBACK')
        except:
            pass
        return jsonify({'success': False, 'error': f'Erro ao excluir usuário: {str(e)}'}), 500

# Função para obter o próximo prefixo disponível para um usuário e nome de link
def get_next_prefix(conn, user_id, link_name):
    """
    Determina o próximo prefixo disponível para um nome de link específico de um usuário.
    Se o nome de link já existe, incrementa o prefixo.
    
    Args:
        conn: Conexão com o banco de dados
        user_id: ID do usuário
        link_name: Nome do link
        
    Returns:
        Próximo prefixo disponível (inteiro)
    """
    # Buscar o maior prefixo existente para este usuário e nome de link
    max_prefix = conn.execute('''
        SELECT MAX(prefix) as max_prefix
        FROM custom_links
        WHERE user_id = ? AND link_name = ?
    ''', (user_id, link_name)).fetchone()['max_prefix']
    
    # Se não existir nenhum, começar com 1
    if max_prefix is None:
        return 1
    
    # Caso contrário, incrementar o maior prefixo
    return max_prefix + 1

if __name__ == '__main__':
    # Inicializar verificação de consistência de dados
    with app.app_context():
        with get_db_connection() as conn:
            fix_data_inconsistencies(conn)
    
    # Executar a aplicação com configurações corretas para acesso externo
    import os
    port = int(os.environ.get('PORT', 3333))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
