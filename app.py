import os
import random
import sqlite3
from datetime import datetime
import traceback  # Adicionando para capturar stacktrace
import logging    # Adicionando para melhorar logs
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, send_from_directory
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Chave secreta para sessões
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'instance', 'whatsapp_redirect.db')

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        # Criar tabela de usuários
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                fullname TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Criar tabela de números de WhatsApp
        conn.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Criar tabela de links personalizados
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                link_name TEXT UNIQUE NOT NULL,
                custom_message TEXT,
                click_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Criar tabela de logs de redirecionamento
        conn.execute('''
            CREATE TABLE IF NOT EXISTS redirect_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL,
                number_id INTEGER NOT NULL,
                redirect_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (link_id) REFERENCES custom_links (id),
                FOREIGN KEY (number_id) REFERENCES whatsapp_numbers (id)
            )
        ''')
        
        conn.commit()

# Inicializar o banco de dados na inicialização
try:
    init_db()
    print("Banco de dados inicializado com sucesso")
except Exception as e:
    print(f"Erro ao inicializar banco de dados: {e}")
    # Continuar mesmo se houver erro para evitar falha no Railway

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            logger.info(f"Verificando autenticação para rota: {request.path}")
            logger.debug(f"Informações da sessão: {session}")
            
            # Verificar se a sessão existe
            if not session:
                logger.warning("Sessão vazia ou inexistente")
                return redirect(url_for('login'))
                
            # Verificar se o usuário está logado
            if 'logged_in' not in session or not session['logged_in']:
                logger.warning(f"Acesso negado: usuário não está logado")
                return redirect(url_for('login'))
                
            # Verificar se user_id está presente
            if 'user_id' not in session:
                logger.warning("user_id não encontrado na sessão")
                session.clear()  # Limpar sessão inválida
                return redirect(url_for('login'))
                
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erro no decorator login_required: {str(e)}")
            logger.error(traceback.format_exc())
            return redirect(url_for('login'))
    return decorated_function

# Rotas da aplicação
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    try:
        logger.info(f"Acesso à página de login - método: {request.method}")
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            logger.info(f"Tentativa de login para usuário: {username}")
            
            # Buscar usuário no banco de dados
            try:
                with get_db_connection() as conn:
                    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
                    if user:
                        logger.debug(f"Usuário encontrado: ID={user['id']}")
                    else:
                        logger.warning(f"Usuário não encontrado: {username}")
            except Exception as db_error:
                logger.error(f"Erro ao consultar banco de dados: {str(db_error)}")
                error = 'Erro ao acessar banco de dados. Por favor, tente novamente.'
                return render_template('login.html', error=error)
            
            # Verificar credenciais
            if user and check_password_hash(user['password'], password):
                try:
                    # Limpar qualquer sessão existente
                    session.clear()
                    
                    # Configurar a sessão com informações do usuário
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_id'] = user['id']
                    session['fullname'] = user['fullname']
                    
                    logger.info(f"Login bem-sucedido para usuário: {username}, ID: {user['id']}")
                    
                    # Verificar se a sessão foi configurada corretamente
                    if 'logged_in' not in session or not session['logged_in']:
                        logger.error("Falha ao configurar sessão após login")
                        error = 'Erro ao configurar sessão. Por favor, tente novamente.'
                        return render_template('login.html', error=error)
                        
                    return redirect(url_for('admin'))
                except Exception as session_error:
                    logger.error(f"Erro ao configurar sessão: {str(session_error)}")
                    error = 'Erro ao processar login. Por favor, tente novamente.'
            else:
                error = 'Credenciais inválidas. Por favor, tente novamente.'
                logger.warning(f"Tentativa de login falhou para usuário: {username}")
        
        # Se for método GET ou login falhar
        return render_template('login.html', error=error)
    except Exception as e:
        logger.error(f"Erro não tratado na rota de login: {str(e)}")
        logger.error(traceback.format_exc())
        error = 'Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.'
        return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    print(f"Logout para usuário: {session.get('username')}")
    session.clear()  # Limpar a sessão completamente
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    try:
        logger.info(f"Acessando /admin - user_id: {session.get('user_id')}")
        
        # Obter números e links do banco de dados para o usuário logado
        user_id = session.get('user_id')
        
        if not user_id:
            logger.error("Erro: user_id não encontrado na sessão")
            return redirect(url_for('login'))
            
        logger.debug(f"Conectando ao banco de dados para user_id: {user_id}")
        with get_db_connection() as conn:
            numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
            links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
            
            # Converter para lista para detectar problemas potenciais
            numbers_list = [dict(row) for row in numbers]
            links_list = [dict(row) for row in links]
            
            logger.info(f"Encontrados {len(numbers_list)} números e {len(links_list)} links")
            
            return render_template('admin.html', numbers=numbers_list, links=links_list)
    except Exception as e:
        # Registrar o erro detalhadamente
        logger.error(f"Erro ao acessar /admin: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Retornar uma página de erro amigável
        return render_template('index.html', error='Ocorreu um erro ao carregar a página de administração. Por favor, tente novamente ou contate o suporte.'), 500

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
            
            # Validar formato do número
            is_valid, formatted_number = validate_phone_number(phone)
            if not is_valid:
                return jsonify({'success': False, 'error': 'Formato de número inválido. Use apenas dígitos e inclua o código do país.'}), 400
            
            # Verificar se o número já existe para este usuário
            existing = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ? AND phone_number = ?', 
                                 (user_id, formatted_number)).fetchone()
            if existing:
                # Se já existir mas estiver inativo, reativá-lo
                if existing['is_active'] == 0:
                    conn.execute('UPDATE whatsapp_numbers SET is_active = 1, description = ? WHERE id = ?', 
                              (description or existing['description'], existing['id']))
                    return jsonify({'success': True, 'message': 'Número reativado com sucesso'})
                return jsonify({'success': False, 'error': 'Este número já está cadastrado para o seu usuário'}), 400
                
            # Adicionar novo número
            conn.execute('INSERT INTO whatsapp_numbers (user_id, phone_number, description, is_active) VALUES (?, ?, ?, 1)', 
                       (user_id, formatted_number, description))
            # Retornar JSON em vez de redirecionamento
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso'})
        
        # Se for GET, retornar todos os números ativos
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ? AND is_active = 1', (user_id,)).fetchall()
        return jsonify([dict(number) for number in numbers])

# Função para validar número de telefone
def validate_phone_number(phone):
    # Remover caracteres não numéricos
    clean_number = ''.join(filter(str.isdigit, phone))
    
    # Validar comprimento básico
    if len(clean_number) < 10:
        return False, None
    
    # Garantir que tenha o código do país (55 para Brasil)
    if not clean_number.startswith('55'):
        clean_number = '55' + clean_number
    
    return True, clean_number

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
                # Verificar se é o último número ativo
                active_count = conn.execute('SELECT COUNT(*) as count FROM whatsapp_numbers WHERE user_id = ? AND is_active = 1', 
                                       (user_id,)).fetchone()['count']
                
                if active_count <= 1 and number['is_active'] == 1:
                    return jsonify({'success': False, 'error': 'Não é possível excluir o último número ativo. Adicione outro número antes de excluir este.'}), 400
                
                # Em vez de excluir, marcar como inativo (soft delete)
                conn.execute('UPDATE whatsapp_numbers SET is_active = 0 WHERE id = ?', (number_id,))
                return jsonify({'success': True, 'message': 'Número desativado com sucesso'})
            
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
                        # Verificar se não está desativando o último número ativo
                        if is_active == 0 and number['is_active'] == 1:
                            active_count = conn.execute('SELECT COUNT(*) as count FROM whatsapp_numbers WHERE user_id = ? AND is_active = 1', 
                                                   (user_id,)).fetchone()['count']
                            if active_count <= 1:
                                return jsonify({'success': False, 'error': 'Não é possível desativar o último número ativo.'}), 400
                        
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
    redirect_start_time = datetime.now()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    try:
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
            
            # Novo código: Verificar e exibir a página de redirecionamento
            return render_template('redirect.html', whatsapp_url=whatsapp_url, custom_message=link['custom_message'] or 'Olá!')
    except Exception as e:
        # Retornar uma página de erro genérica
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
        # Verificar consistência de dados antes de executar a consulta principal
        validate_data_consistency(conn, user_id, link_id, start_date, end_date)
        
        # Obter o número total de registros para essa consulta (sem paginação)
        count_query = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition}
        '''
        
        total_records = conn.execute(count_query, params).fetchone()['total']
        print(f"Total de registros para atividades recentes: {total_records}")
        
        # Preparar a query base
        query = f'''
            SELECT 
                rl.id,
                rl.redirect_time,
                cl.link_name,
                wn.phone_number,
                wn.description as number_description,
                rl.ip_address,
                rl.user_agent
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE {link_condition} {date_condition}
            ORDER BY rl.redirect_time DESC
        '''
        
        # Se não for para mostrar todos, adicionar LIMIT e OFFSET para paginação
        query_params = params.copy()
        if not show_all:
            query += " LIMIT ? OFFSET ?"
            query_params.append(limit)
            query_params.append((page - 1) * limit)
            print(f"Aplicando paginação: limite={limit}, página={page}")
        else:
            print(f"Retornando TODAS as atividades recentes ({total_records} registros)")
        
        recent_redirects = conn.execute(query, query_params).fetchall()
        
        # Formatar os resultados para JSON
        result = []
        for redirect in recent_redirects:
            result.append({
                'id': redirect['id'],
                'redirect_time': redirect['redirect_time'],
                'link_name': redirect['link_name'],
                'phone_number': redirect['phone_number'],
                'number_description': redirect['number_description'],
                'ip_address': redirect['ip_address'],
                'user_agent': redirect['user_agent']
            })
        
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
        # Total de cliques em todos os links do usuário
        total_clicks_query = 'SELECT SUM(click_count) as total FROM custom_links WHERE user_id = ?'
        if link_id != 'all' and link_id.isdigit():
            total_clicks_query = 'SELECT SUM(click_count) as total FROM custom_links WHERE user_id = ? AND id = ?'
        
        total_clicks = conn.execute(total_clicks_query, params).fetchone()['total'] or 0
        
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

# API para obter dados geográficos para o mapa de cliques
@app.route('/api/stats/map', methods=['GET'])
@login_required
def get_map_stats():
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id', 'all')
    
    # Obter condições e parâmetros de forma padronizada
    link_condition, date_condition, params = get_standard_filter_conditions(user_id, link_id, start_date, end_date)
    
    print(f"Query de mapa - user_id: {user_id}, link_id: {link_id}, start_date: {start_date}, end_date: {end_date}")
    print(f"Parâmetros para mapa: {params}")
    
    with get_db_connection() as conn:
        # Usamos a mesma consulta padrão para manter consistência
        count_query = f'''
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE {link_condition} {date_condition}
        '''
        
        total_clicks = conn.execute(count_query, params).fetchone()['total']
        print(f"Total de cliques no mapa: {total_clicks}")
        
        # Verificar consistência de dados
        validate_data_consistency(conn, user_id, link_id, start_date, end_date)
        
        if total_clicks > 0:
            # Em vez de espalhar aleatoriamente, vamos usar uma localização fixa
            # para todos os cliques do mesmo usuário/link
            
            # Para uma implementação de produção, você usaria um serviço de geolocalização
            # para determinar a localização real com base no IP dos usuários
            
            # Usar uma localização fixa para demonstração (Curitiba)
            # Isso simula que todos os acessos vieram do mesmo local
            city = {"name": "Curitiba", "lat": -25.4290, "lng": -49.2671}
            
            locations = [{
                "lat": city["lat"],
                "lng": city["lng"],
                "name": city["name"],
                "count": total_clicks  # Todos os cliques em um único lugar
            }]
            
            return jsonify({"locations": locations})
        else:
            # Se não temos cliques para os filtros, retornar lista vazia
            return jsonify({"locations": []})

# Rota para a página de dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
    
    return render_template('dashboard.html', links=links, numbers=numbers)

# Rota para a página de estatísticas
@app.route('/estatisticas')
@login_required
def estatisticas():
    user_id = session.get('user_id')
    with get_db_connection() as conn:
        links = conn.execute('SELECT * FROM custom_links WHERE user_id = ?', (user_id,)).fetchall()
        numbers = conn.execute('SELECT * FROM whatsapp_numbers WHERE user_id = ?', (user_id,)).fetchall()
    
    # Retornar o template específico de estatísticas em vez do dashboard
    return render_template('estatisticas.html', links=links, numbers=numbers)

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
    try:
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
    except Exception as e:
        print(f"Erro na verificação de consistência: {e}")
        # Não deixar falhar no Railway
        pass

# Configuração para permitir acesso a recursos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        logger.info(f"Acessando arquivo estático: {filename}")
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Erro ao acessar arquivo estático {filename}: {str(e)}")
        return f"Erro ao carregar arquivo: {filename}", 404

# Capturar erros 500 para logar detalhes
@app.errorhandler(500)
def handle_500(e):
    logger.error(f"Erro 500 interno: {str(e)}")
    logger.error(traceback.format_exc())
    return render_template('index.html', error="Ocorreu um erro interno no servidor. Por favor, tente novamente mais tarde."), 500

if __name__ == '__main__':
    # Configurações para ambiente de desenvolvimento local
    # Executar a aplicação com configurações corretas para acesso externo
    try:
        port = int(os.environ.get('PORT', 5000))  # Alterando porta padrão para 5000
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        logger.info(f"Iniciando servidor na porta {port} com debug={debug}")
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.critical(f"Erro ao iniciar o servidor: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"Erro crítico ao iniciar: {str(e)}")
