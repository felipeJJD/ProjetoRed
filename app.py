import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, jsonify, url_for, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Flask
app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.instance_path, 'whatsapp_redirect.db')
app.secret_key = 'chave_secreta_para_sessoes_do_flask'  # Chave necessária para sessões

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verificar se existem usuários e criar os padrões se não houver
        if not conn.execute('SELECT * FROM users').fetchone():
            # Criar usuários padrão (pedro e felipe)
            conn.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (?, ?, ?)
            ''', ('pedro', generate_password_hash('Vera123'), 'Pedro Administrador'))
            
            conn.execute('''
                INSERT INTO users (username, password, fullname)
                VALUES (?, ?, ?)
            ''', ('felipe', generate_password_hash('123'), 'Felipe Administrador'))

        # Criar tabela de números com referência ao usuário
        conn.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                redirect_count INTEGER DEFAULT 0,
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
                click_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, link_name)
            )
        ''')
        
        # Criar tabela de redirecionamentos (nova tabela)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS redirects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number_id INTEGER NOT NULL,
                link_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id),
                FOREIGN KEY (link_id) REFERENCES custom_links (id)
            )
        ''')
        
        # Verificar se as colunas necessárias existem
        result = conn.execute("PRAGMA table_info(custom_links)").fetchall()
        columns = [col['name'] for col in result]
        
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
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, link_name)
                    )
                ''')
                
                # Transferir dados, atribuindo a pedro (id=1) por padrão
                for link in links:
                    conn.execute('''
                        INSERT INTO custom_links (id, user_id, link_name, custom_message, is_active)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (link['id'], 1, link['link_name'], link['custom_message'], link['is_active']))
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
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, link_name)
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
                        redirect_count INTEGER DEFAULT 0,
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
                        redirect_count INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
        
        # Verificar e adicionar coluna redirect_count se não existir
        if 'redirect_count' not in columns:
            try:
                print("Adicionando coluna redirect_count à tabela whatsapp_numbers...")
                conn.execute('ALTER TABLE whatsapp_numbers ADD COLUMN redirect_count INTEGER DEFAULT 0')
                print("Coluna redirect_count adicionada com sucesso!")
            except Exception as e:
                print(f"Erro ao adicionar coluna redirect_count: {e}")
        
        # Verificar se a tabela redirects existe
        tabelas_existentes = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tabelas_existentes = [tabela['name'] for tabela in tabelas_existentes]
        
        if 'redirects' not in tabelas_existentes:
            try:
                print("Criando tabela redirects...")
                conn.execute('''
                    CREATE TABLE redirects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        number_id INTEGER NOT NULL,
                        link_id INTEGER NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id),
                        FOREIGN KEY (link_id) REFERENCES custom_links (id)
                    )
                ''')
                print("Tabela redirects criada com sucesso!")
            except Exception as e:
                print(f"Erro ao criar a tabela redirects: {e}")
        
        # Garantir que cada usuário tenha pelo menos um link padrão
        for user_id in [1, 2]:  # pedro e felipe
            conn.execute('''
                INSERT OR IGNORE INTO custom_links (user_id, link_name, custom_message)
                VALUES (?, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...')
            ''', (user_id,))

# Inicializar o banco de dados
init_db()

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
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
            return redirect(url_for('admin'))
        else:
            error = 'Credenciais inválidas. Por favor, tente novamente.'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('fullname', None)
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

@app.route('/admin/estatisticas')
@login_required
def estatisticas():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        # Obter estatísticas por número
        numeros_stats = conn.execute('''
            SELECT wn.*, COUNT(r.id) as total_redirects,
                   (SELECT COUNT(*) FROM redirects r2 
                    JOIN custom_links cl ON r2.link_id = cl.id 
                    WHERE r2.number_id = wn.id AND cl.user_id = ? 
                    AND DATE(r2.timestamp) = DATE('now')) as redirects_today
            FROM whatsapp_numbers wn
            LEFT JOIN redirects r ON wn.id = r.number_id
            WHERE wn.user_id = ?
            GROUP BY wn.id
            ORDER BY total_redirects DESC
        ''', (user_id, user_id)).fetchall()
        
        # Obter estatísticas por link para este usuário
        links_stats = conn.execute('''
            SELECT cl.*, COUNT(r.id) as total_redirects
            FROM custom_links cl
            LEFT JOIN redirects r ON cl.id = r.link_id
            WHERE cl.user_id = ?
            GROUP BY cl.id
            ORDER BY total_redirects DESC
        ''', (user_id,)).fetchall()
        
        # Obter detalhes de redirecionamentos recentes (últimos 50)
        recentes = conn.execute('''
            SELECT r.timestamp, cl.link_name, wn.phone_number, wn.description
            FROM redirects r
            JOIN whatsapp_numbers wn ON r.number_id = wn.id
            JOIN custom_links cl ON r.link_id = cl.id
            WHERE wn.user_id = ?
            ORDER BY r.timestamp DESC
            LIMIT 50
        ''', (user_id,)).fetchall()
        
    return render_template('estatisticas.html', 
                          numeros_stats=numeros_stats,
                          links_stats=links_stats,
                          recentes=recentes)

@app.route('/admin/balanco')
@login_required
def balanco_redirecionamentos():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        # Obter estatísticas por número
        numeros = conn.execute('''
            SELECT phone_number, description, redirect_count 
            FROM whatsapp_numbers
            WHERE user_id = ?
            ORDER BY redirect_count DESC
        ''', (user_id,)).fetchall()
        
        # Calcular o total de redirecionamentos
        total_redirects = sum(num['redirect_count'] for num in numeros)
        
        # Calcular a proporção ideal
        num_count = len(numeros)
        ideal_por_numero = total_redirects / num_count if num_count > 0 else 0
        
        # Calcular desvio do ideal
        for i in range(len(numeros)):
            numeros[i] = dict(numeros[i])
            numeros[i]['desvio'] = numeros[i]['redirect_count'] - ideal_por_numero
            numeros[i]['porcentagem'] = (numeros[i]['redirect_count'] / total_redirects * 100) if total_redirects > 0 else 0
            numeros[i]['ideal'] = 100 / num_count if num_count > 0 else 0
            numeros[i]['diferenca_pct'] = numeros[i]['porcentagem'] - numeros[i]['ideal']
        
    # Retornar em formato JSON
    return jsonify({
        'total_redirecionamentos': total_redirects,
        'numeros_cadastrados': num_count,
        'ideal_por_numero': round(ideal_por_numero, 2),
        'ideal_porcentagem': round(100 / num_count if num_count > 0 else 0, 2),
        'numeros': [{
            'phone': num['phone_number'],
            'description': num['description'],
            'count': num['redirect_count'],
            'porcentagem': round(num['porcentagem'], 2),
            'ideal': round(num['ideal'], 2),
            'diferenca': round(num['diferenca_pct'], 2)
        } for num in numeros]
    })

# API para gerenciar números
@app.route('/api/numbers', methods=['GET', 'POST'])
@login_required
def manage_numbers():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        if request.method == 'POST':
            # Verificar se os dados são JSON ou formulário
            if request.is_json:
                data = request.json
                phone = data.get('phone_number')
                description = data.get('description')
            else:
                phone = request.form.get('phone')
                description = request.form.get('description')
                
            # Validar dados
            if not phone:
                return jsonify({'success': False, 'error': 'Número de telefone é obrigatório'}), 400
                
            # Adicionar novo número
            conn.execute('INSERT INTO whatsapp_numbers (user_id, phone_number, description) VALUES (?, ?, ?)', 
                       (user_id, phone, description))
            # Retornar JSON em vez de redirecionamento
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso'})
        
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
            
            # Verificar se o link já existe para este usuário
            existing = conn.execute('SELECT * FROM custom_links WHERE link_name = ? AND user_id = ?', 
                                  (link_name, user_id)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Este link já existe para o seu usuário'}), 400
            
            conn.execute('INSERT INTO custom_links (user_id, link_name, custom_message) VALUES (?, ?, ?)', 
                       (user_id, link_name, custom_message))
            return jsonify({'success': True, 'message': 'Link adicionado com sucesso'})
        
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
    with get_db_connection() as conn:
        # Procurar qual usuário é dono do link
        link = conn.execute('''
            SELECT cl.*, u.id as owner_id 
            FROM custom_links cl
            JOIN users u ON cl.user_id = u.id
            WHERE cl.link_name = ? AND cl.is_active = 1
        ''', (link_name,)).fetchone()
        
        if not link:
            # Link não encontrado ou inativo
            return render_template('index.html', error='Link não encontrado ou inativo')
        
        # Incrementar contador de cliques
        conn.execute('UPDATE custom_links SET click_count = click_count + 1 WHERE id = ?', (link['id'],))
        
        # Obter todos os números deste usuário
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', 
                            (link['owner_id'],)).fetchall()
        
        if not numbers:
            # Nenhum número registrado
            return render_template('index.html', error='Nenhum número cadastrado para este link')
        
        # Algoritmo de distribuição equilibrada:
        # Em vez de escolher aleatoriamente, vamos priorizar o número com menos redirecionamentos
        
        if len(numbers) == 1:
            # Se só tem um número, não há o que balancear
            selected_number = numbers[0]
        else:
            # Ordenar números pela quantidade de redirecionamentos (do menor para o maior)
            sorted_numbers = sorted(numbers, key=lambda x: x['redirect_count'])
            
            # Verificar se há empate no menor número de redirecionamentos
            min_redirects = sorted_numbers[0]['redirect_count']
            candidates = [n for n in sorted_numbers if n['redirect_count'] == min_redirects]
            
            if len(candidates) > 1:
                # Se houver empate, escolher aleatoriamente entre os candidatos
                selected_number = random.choice(candidates)
            else:
                # Caso contrário, escolher o que tem menos redirecionamentos
                selected_number = sorted_numbers[0]
                
            # Adicionar um pouco de aleatoriedade (20% de chance de não escolher o mínimo)
            # Isso evita que o padrão fique muito óbvio e mantém alguma aleatoriedade
            if random.random() < 0.2 and len(sorted_numbers) > 1:
                # Escolher qualquer número exceto o primeiro (que já foi selecionado acima)
                selected_number = random.choice(sorted_numbers[1:])
        
        phone_number = selected_number['phone_number']
        
        # Incrementar contador de redirecionamentos para este número específico
        conn.execute('UPDATE whatsapp_numbers SET redirect_count = redirect_count + 1 WHERE id = ?', 
                   (selected_number['id'],))
        
        # Registrar o redirecionamento na nova tabela
        conn.execute('INSERT INTO redirects (number_id, link_id) VALUES (?, ?)', 
                   (selected_number['id'], link['id']))
        
        # Preparar mensagem personalizada ou usar padrão
        custom_message = link['custom_message'] or 'Olá!'
        
        # Codificar a mensagem para URL
        import urllib.parse
        custom_message = urllib.parse.quote(custom_message)
        
        # Construir URL do WhatsApp
        whatsapp_url = f"https://wa.me/{phone_number}?text={custom_message}"
        
        # Redirecionar diretamente para o WhatsApp
        return redirect(whatsapp_url)

if __name__ == '__main__':
    # Configuração para desenvolvimento local
    app.run(debug=True, port=5002)
    
    # Configuração para produção (Railway)
    # port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port, debug=False)
