import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, jsonify, url_for

# Configuração do Flask
app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.instance_path, 'whatsapp_redirect.db')

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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                description TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_name TEXT NOT NULL UNIQUE,
                custom_message TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Verificar se a coluna custom_message já existe
        result = conn.execute("PRAGMA table_info(custom_links)").fetchall()
        columns = [col['name'] for col in result]
        
        # Adicionar coluna custom_message se não existir
        if 'custom_message' not in columns:
            conn.execute('ALTER TABLE custom_links ADD COLUMN custom_message TEXT')
        
        # Inserir link padrão se não existir
        conn.execute('''
            INSERT OR IGNORE INTO custom_links (id, link_name, custom_message)
            VALUES (1, 'padrao', 'Olá! Você será redirecionado para um de nossos atendentes. Aguarde um momento...')
        ''')
        conn.commit()

# Inicializar o banco de dados
init_db()

# Rotas da aplicação
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    # Obter números e links do banco de dados
    with get_db_connection() as conn:
        numbers = conn.execute('SELECT * FROM whatsapp_numbers').fetchall()
        links = conn.execute('SELECT * FROM custom_links').fetchall()
    return render_template('admin.html', numbers=numbers, links=links)

# API para gerenciar números
@app.route('/api/numbers', methods=['GET', 'POST'])
def manage_numbers():
    if request.method == 'GET':
        with get_db_connection() as conn:
            numbers = conn.execute('SELECT * FROM whatsapp_numbers').fetchall()
        return jsonify([dict(num) for num in numbers])
    
    elif request.method == 'POST':
        data = request.json
        phone = data.get('phone_number')
        description = data.get('description', '')
        
        with get_db_connection() as conn:
            conn.execute('INSERT INTO whatsapp_numbers (phone_number, description) VALUES (?, ?)',
                         (phone, description))
            conn.commit()
        return jsonify({"success": True, "message": "Número adicionado com sucesso!"}), 201

@app.route('/api/numbers/<int:number_id>', methods=['DELETE'])
def delete_number(number_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM whatsapp_numbers WHERE id = ?', (number_id,))
        conn.commit()
    return jsonify({"success": True, "message": "Número excluído com sucesso!"})

# API para gerenciar links personalizados
@app.route('/api/links', methods=['GET', 'POST'])
def manage_links():
    if request.method == 'GET':
        with get_db_connection() as conn:
            links = conn.execute('SELECT * FROM custom_links').fetchall()
        return jsonify([dict(link) for link in links])
    
    elif request.method == 'POST':
        data = request.json
        link_name = data.get('link_name')
        custom_message = data.get('custom_message', 'Você será redirecionado para um de nossos atendentes. Aguarde um momento...')
        
        with get_db_connection() as conn:
            try:
                conn.execute('INSERT INTO custom_links (link_name, custom_message) VALUES (?, ?)', 
                             (link_name, custom_message))
                conn.commit()
                return jsonify({"success": True, "message": "Link adicionado com sucesso!"}), 201
            except sqlite3.IntegrityError:
                return jsonify({"success": False, "message": "Nome de link já existe!"}), 400

@app.route('/api/links/<int:link_id>', methods=['DELETE'])
def delete_link(link_id):
    # Não permitir deletar o link padrão (id=1)
    if link_id == 1:
        return jsonify({"success": False, "message": "Não é possível excluir o link padrão!"}), 400
    
    with get_db_connection() as conn:
        conn.execute('DELETE FROM custom_links WHERE id = ?', (link_id,))
        conn.commit()
    return jsonify({"success": True, "message": "Link excluído com sucesso!"})

@app.route('/api/links/<int:link_id>', methods=['PUT'])
def update_link(link_id):
    data = request.json
    new_name = data.get('link_name')
    custom_message = data.get('custom_message')
    
    with get_db_connection() as conn:
        try:
            if custom_message is not None:
                conn.execute('UPDATE custom_links SET link_name = ?, custom_message = ? WHERE id = ?', 
                             (new_name, custom_message, link_id))
            else:
                conn.execute('UPDATE custom_links SET link_name = ? WHERE id = ?', 
                             (new_name, link_id))
            conn.commit()
            return jsonify({"success": True, "message": "Link atualizado com sucesso!"})
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Nome de link já existe!"}), 400

# Rota para redirecionamento direto ao WhatsApp
@app.route('/redirect/<link_name>')
def redirect_whatsapp(link_name):
    with get_db_connection() as conn:
        # Verificar se o link existe
        link = conn.execute('SELECT id, custom_message FROM custom_links WHERE link_name = ?', 
                            (link_name,)).fetchone()
        if not link:
            return "Link não encontrado", 404
        
        # Obter todos os números de WhatsApp
        numbers = conn.execute('SELECT phone_number FROM whatsapp_numbers').fetchall()
        
    if not numbers:
        return "Nenhum número de WhatsApp cadastrado", 404
    
    # Escolher um número aleatoriamente
    random_number = random.choice(numbers)['phone_number']
    
    # Obter mensagem personalizada
    custom_message = link['custom_message'] if link['custom_message'] else "Olá! Gostaria de mais informações."
    
    # Codificar a mensagem para URL
    import urllib.parse
    encoded_message = urllib.parse.quote(custom_message)
    
    # Construir o link do WhatsApp com a mensagem pré-preenchida
    whatsapp_url = f"https://wa.me/{random_number}?text={encoded_message}"
    
    # Redirecionar diretamente para o WhatsApp
    return redirect(whatsapp_url)

if __name__ == '__main__':
    # Configuração para desenvolvimento local
    # app.run(debug=True, port=5002)
    
    # Configuração para produção (Railway)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
