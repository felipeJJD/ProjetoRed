import os
import random
import sqlite3
import logging
import datetime
from flask import Flask, render_template, request, redirect, jsonify, url_for, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Flask
app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.instance_path, 'whatsapp_redirect.db')
app.secret_key = 'chave_secreta_para_sessoes_do_flask'  # Chave necessária para sessões

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('whatsapp_redirect')

# Garantir que o diretório instance exista
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Funções para gerenciar banco de dados
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Criar tabela de usuários
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                fullname TEXT,
                is_superadmin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Criar tabela de logs do sistema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                user_id INTEGER,
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Criar tabela de números com referência ao usuário
        conn.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Criar tabela de links personalizados com referência ao usuário
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                link_name TEXT NOT NULL,
                custom_message TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, link_name)
            )
        ''')
        
        # Verificar se existem usuários e criar os padrões se não houver
        if not conn.execute('SELECT * FROM users').fetchone():
            # Criar usuário super administrador (você)
            conn.execute('''
                INSERT INTO users (username, password, fullname, is_superadmin)
                VALUES (?, ?, ?, ?)
            ''', ('admin', generate_password_hash('admin123'), 'Super Administrador', 1))
            
            # Criar usuários padrão (pedro e felipe)
            conn.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (?, ?, ?)
            ''', ('pedro', generate_password_hash('Vera123'), 'Pedro Administrador'))
            
            conn.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (?, ?, ?)
            ''', ('felipe', generate_password_hash('123'), 'Felipe Administrador'))
            
            # Registrar log de criação de usuários
            conn.execute('''
                INSERT INTO system_logs (level, message)
                VALUES (?, ?)
            ''', ('INFO', 'Usuários iniciais criados durante a inicialização do sistema'))

# Inicializar o banco de dados
init_db()

# Função para adicionar log ao sistema
def add_log(level, message, user_id=None):
    with get_db_connection() as conn:
        ip = request.remote_addr if request else "N/A"
        conn.execute('''
            INSERT INTO system_logs (level, message, user_id, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (level, message, user_id, ip))
    logger.info(f"[{level}] {message} (User ID: {user_id}, IP: {ip})")

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Função para verificar se o usuário é superadmin
def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or 'is_superadmin' not in session or not session['is_superadmin']:
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
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']
            session['fullname'] = user['fullname']
            session['is_superadmin'] = user['is_superadmin'] == 1
            
            # Adicionar log de login
            add_log('INFO', f'Usuário {username} fez login', user['id'])
            
            # Redirecionar para superadmin ou admin normal
            if user['is_superadmin'] == 1:
                return redirect(url_for('superadmin'))
            else:
                return redirect(url_for('admin'))
        else:
            error = 'Credenciais inválidas. Por favor, tente novamente.'
            add_log('WARNING', f'Tentativa de login mal-sucedida para o usuário: {username}')
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    if 'user_id' in session:
        add_log('INFO', f'Usuário {session.get("username")} fez logout', session.get('user_id'))
    
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('fullname', None)
    session.pop('is_superadmin', None)
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    # Obter números e links do banco de dados para o usuário logado
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
    return render_template('admin.html', numbers=numbers, links=links)

# API para gerenciar números
@app.route('/api/numbers', methods=['GET', 'POST'])
@login_required
def manage_numbers():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        if request.method == 'POST':
            # Adicionar novo número
            phone = request.form.get('phone')
            description = request.form.get('description')
            conn.execute('INSERT INTO whatsapp_numbers (user_id, phone_number, description) VALUES (?, ?, ?)', 
                      (user_id, phone, description))
            return redirect(url_for('admin'))
        
        # Se for GET, retornar todos os números
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
        return jsonify([dict(number) for number in numbers])

@app.route('/api/numbers/<int:number_id>', methods=['DELETE'])
@login_required
def delete_number(number_id):
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        # Verificar se o número pertence ao usuário atual
        number = conn.execute('SELECT * FROM whatsapp_numbers WHERE id = ? AND user_id = ?', 
                           (number_id, user_id)).fetchone()
        if number:
            conn.execute('DELETE FROM whatsapp_numbers WHERE id = ?', (number_id,))
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Número não encontrado ou sem permissão'}), 403

# API para gerenciar links personalizados
@app.route('/api/links', methods=['GET', 'POST'])
@login_required
def manage_links():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        if request.method == 'POST':
            # Adicionar novo link
            link_name = request.form.get('link_name')
            custom_message = request.form.get('custom_message')
            
            # Verificar se o link já existe para este usuário
            existing = conn.execute('SELECT * FROM custom_links WHERE link_name = ? AND user_id = ?', 
                                 (link_name, user_id)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Este link já existe para o seu usuário'}), 400
            
            conn.execute('INSERT INTO custom_links (user_id, link_name, custom_message) VALUES (?, ?, ?)', 
                      (user_id, link_name, custom_message))
            return redirect(url_for('admin'))
        
        # Se for GET, retornar todos os links
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
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
        
        # Não permitir excluir o link padrão
        if link['link_name'] == 'padrao':
            return jsonify({'success': False, 'error': 'Não é possível excluir o link padrão'}), 400
        
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
        
        # Se estiver tentando atualizar o nome do link, verificar se o novo nome já existe
        if 'link_name' in data and data['link_name'] != link['link_name']:
            existing = conn.execute('SELECT * FROM custom_links WHERE link_name = ? AND user_id = ? AND id != ?', 
                                 (data['link_name'], user_id, link_id)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Este nome de link já está em uso'}), 400
        
        # Atualizar o link
        if 'link_name' in data:
            conn.execute('UPDATE custom_links SET link_name = ? WHERE id = ?', 
                      (data['link_name'], link_id))
        
        if 'custom_message' in data:
            conn.execute('UPDATE custom_links SET custom_message = ? WHERE id = ?', 
                      (data['custom_message'], link_id))
        
        if 'is_active' in data:
            conn.execute('UPDATE custom_links SET is_active = ? WHERE id = ?', 
                      (1 if data['is_active'] else 0, link_id))
        
        return jsonify({'success': True})

# Rota para redirecionamento direto ao WhatsApp
@app.route('/redirect/<link_name>')
def redirect_whatsapp(link_name):
    # Primeiro, precisamos encontrar qual usuário tem este link
    with get_db_connection() as conn:
        # Procurar o link entre todos os usuários
        link = conn.execute('''
            SELECT cl.*, u.id as owner_id 
            FROM custom_links cl
            JOIN users u ON cl.user_id = u.id
            WHERE cl.link_name = ? AND cl.is_active = 1
        ''', (link_name,)).fetchone()
        
        if not link:
            # Link não encontrado ou inativo
            return render_template('index.html', error='Link não encontrado ou inativo')
        
        # Encontrar o link, agora pegar um número aleatório desse usuário
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', 
                            (link['owner_id'],)).fetchall()
        
        if not numbers:
            # Usuário não tem números cadastrados
            return render_template('index.html', error='Não há números disponíveis para este link')
        
        # Selecionar um número aleatório
        random_number = random.choice(numbers)
        phone_number = random_number['phone_number']
        
        custom_message = link['custom_message'] or ''
        
        # Construir URL do WhatsApp
        whatsapp_url = f"https://wa.me/{phone_number}?text={custom_message}"
        
        # Redirecionar diretamente para o WhatsApp
        return redirect(whatsapp_url)

# Rota para o painel de super administrador
@app.route('/superadmin')
@superadmin_required
def superadmin():
    with get_db_connection() as conn:
        # Obter todos os usuários
        users = conn.execute('''
            SELECT u.*, 
                  (SELECT COUNT(*) FROM whatsapp_numbers WHERE user_id = u.id) as number_count,
                  (SELECT COUNT(*) FROM custom_links WHERE user_id = u.id) as link_count
            FROM users u
            ORDER BY u.id
        ''').fetchall()
        
        # Obter logs recentes
        logs = conn.execute('''
            SELECT l.*, u.username 
            FROM system_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.timestamp DESC
            LIMIT 100
        ''').fetchall()
    
    return render_template('superadmin.html', users=users, logs=logs)

# API para gerenciar usuários (apenas superadmin)
@app.route('/api/users', methods=['GET', 'POST'])
@superadmin_required
def manage_users():
    with get_db_connection() as conn:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            fullname = request.form.get('fullname')
            
            # Verificar se o usuário já existe
            existing = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if existing:
                add_log('ERROR', f'Tentativa de criar usuário duplicado: {username}', session.get('user_id'))
                return jsonify({'success': False, 'error': 'Este nome de usuário já existe'}), 400
            
            # Criar o novo usuário
            conn.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (?, ?, ?)
            ''', (username, generate_password_hash(password), fullname))
            
            add_log('INFO', f'Novo usuário criado: {username}', session.get('user_id'))
            return redirect(url_for('superadmin'))
        
        # Para requisições GET, retornar todos os usuários
        users = conn.execute('''
            SELECT id, username, fullname, is_superadmin, created_at,
                  (SELECT COUNT(*) FROM whatsapp_numbers WHERE user_id = users.id) as number_count,
                  (SELECT COUNT(*) FROM custom_links WHERE user_id = users.id) as link_count
            FROM users
        ''').fetchall()
        return jsonify([dict(user) for user in users])

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@superadmin_required
def manage_user(user_id):
    # Não permitir excluir o próprio superadmin
    if user_id == session.get('user_id') and request.method == 'DELETE':
        add_log('ERROR', 'Tentativa de excluir o próprio superadmin', session.get('user_id'))
        return jsonify({'success': False, 'error': 'Não é possível excluir seu próprio usuário'}), 403
    
    with get_db_connection() as conn:
        if request.method == 'GET':
            # Obter detalhes de um usuário específico
            user = conn.execute('SELECT id, username, fullname, is_superadmin, created_at FROM users WHERE id = ?', 
                             (user_id,)).fetchone()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
            
            # Obter números deste usuário
            numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', 
                                (user_id,)).fetchall()
            
            # Obter links deste usuário
            links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', 
                              (user_id,)).fetchall()
            
            return jsonify({
                'user': dict(user),
                'numbers': [dict(number) for number in numbers],
                'links': [dict(link) for link in links]
            })
        
        elif request.method == 'PUT':
            # Atualizar usuário
            data = request.json
            
            if 'password' in data and data['password']:
                conn.execute('UPDATE users SET password = ? WHERE id = ?', 
                          (generate_password_hash(data['password']), user_id))
            
            if 'fullname' in data:
                conn.execute('UPDATE users SET fullname = ? WHERE id = ?', 
                          (data['fullname'], user_id))
            
            add_log('INFO', f'Usuário ID {user_id} atualizado', session.get('user_id'))
            return jsonify({'success': True})
        
        elif request.method == 'DELETE':
            # Excluir usuário e todos os seus dados
            conn.execute('DELETE FROM whatsapp_numbers WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM custom_links WHERE user_id = ?', (user_id,))
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            add_log('INFO', f'Usuário ID {user_id} excluído com todos os seus dados', session.get('user_id'))
            return jsonify({'success': True})

# Rota para visualizar/limpar logs
@app.route('/api/logs', methods=['GET', 'DELETE'])
@superadmin_required
def manage_logs():
    with get_db_connection() as conn:
        if request.method == 'GET':
            # Obter logs, opcionalmente filtrados
            limit = request.args.get('limit', 100, type=int)
            level = request.args.get('level')
            user_id = request.args.get('user_id')
            
            query = 'SELECT l.*, u.username FROM system_logs l LEFT JOIN users u ON l.user_id = u.id WHERE 1=1'
            params = []
            
            if level:
                query += ' AND l.level = ?'
                params.append(level)
            
            if user_id:
                query += ' AND l.user_id = ?'
                params.append(user_id)
            
            query += ' ORDER BY l.timestamp DESC LIMIT ?'
            params.append(limit)
            
            logs = conn.execute(query, params).fetchall()
            return jsonify([dict(log) for log in logs])
        
        elif request.method == 'DELETE':
            # Limpar logs
            conn.execute('DELETE FROM system_logs')
            
            # Registrar ação de limpeza
            add_log('INFO', 'Todos os logs foram limpos', session.get('user_id'))
            return jsonify({'success': True})

if __name__ == '__main__':
    # Configuração para desenvolvimento local
    # app.run(debug=True, port=5002)
    
    # Configuração para produção (Railway)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
