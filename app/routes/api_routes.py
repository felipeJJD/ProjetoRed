from flask import Blueprint, request, jsonify, session
from app.controllers.stats_controller import StatsController
from app.controllers.number_controller import NumberController
from app.controllers.link_controller import LinkController
from app.routes.auth_routes import login_required
import logging
from utils.db_adapter import db_adapter

# Criar blueprint para a API
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/numbers', methods=['GET', 'POST'])
@login_required
def manage_numbers():
    """API para listar e adicionar números de WhatsApp"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Verificar se os dados são JSON ou formulário
        if request.is_json:
            data = request.json
            phone_number = data.get('phone_number')
            description = data.get('description')
        else:
            phone_number = request.form.get('phone_number')
            description = request.form.get('description')
        
        # Adicionar o número usando o controller
        number, error = NumberController.add_number(user_id, phone_number, description)
        
        if number:
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso'})
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    # GET - Listar todos os números do usuário
    numbers = NumberController.get_numbers_by_user(user_id)
    
    # Formatar os números para a resposta
    result = []
    for number in numbers:
        result.append({
            'id': number.id,
            'phone_number': number.phone_number,
            'description': number.description,
            'is_active': number.is_active
        })
    
    return jsonify({'success': True, 'numbers': result})

@api_bp.route('/numbers/<int:number_id>', methods=['DELETE', 'PUT'])
@login_required
def manage_number_by_id(number_id):
    """API para gerenciar um número específico (deletar ou atualizar)"""
    user_id = session.get('user_id')
    
    if request.method == 'DELETE':
        # Chamar o controller para deletar o número
        success, error = NumberController.delete_number(number_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Número excluído com sucesso'})
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    elif request.method == 'PUT':
        # Obter dados da requisição
        data = request.json
        description = data.get('description')
        is_active = data.get('is_active')
        
        # Chamar o controller para atualizar o número
        updated_number, error = NumberController.update_number(
            number_id, user_id, description, is_active
        )
        
        if updated_number:
            return jsonify({'success': True, 'message': 'Número atualizado com sucesso'})
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({'success': False, 'error': 'Método não permitido'}), 405

@api_bp.route('/numbers/<int:number_id>/reactivate', methods=['POST'])
@login_required
def reactivate_number(number_id):
    """API para reativar um número previamente desativado"""
    user_id = session.get('user_id')
    
    # Chamar o controller para reativar o número
    success, error = NumberController.reactivate_number(number_id, user_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Número reativado com sucesso'})
    else:
        return jsonify({'success': False, 'error': error}), 400

@api_bp.route('/links', methods=['GET', 'POST'])
@login_required
def manage_links():
    """API para listar e adicionar links personalizados"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Verificar se os dados são JSON ou formulário
        if request.is_json:
            data = request.json
            link_name = data.get('link_name')
            message = data.get('custom_message')
        else:
            link_name = request.form.get('link_name')
            message = request.form.get('custom_message')
        
        # Adicionar o link usando o controller
        link, error = LinkController.add_link(user_id, link_name, message)
        
        if link:
            # Obter o prefixo e ID do usuário para gerar o link completo
            prefix = link.prefix if hasattr(link, 'prefix') else 0
            
            return jsonify({
                'success': True, 
                'message': 'Link adicionado com sucesso',
                'prefix': prefix,
                'user_id': user_id,
                'full_link': f"{user_id}/{link_name}",
                'legacy_link': f"{prefix}/{link_name}" if prefix else link_name
            })
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    # GET - Listar todos os links do usuário
    links = LinkController.get_links_by_user(user_id)
    
    return jsonify([{
        'id': link.id,
        'link_name': link.link_name,
        'custom_message': link.custom_message,
        'is_active': link.is_active,
        'click_count': link.click_count,
        'prefix': link.prefix if hasattr(link, 'prefix') else 0,
        'user_id': user_id
    } for link in links])

@api_bp.route('/links/<int:link_id>', methods=['DELETE', 'PUT'])
@login_required
def manage_link_by_id(link_id):
    """API para gerenciar um link específico (deletar ou atualizar)"""
    user_id = session.get('user_id')
    
    if request.method == 'DELETE':
        # Chamar o controller para deletar o link
        success, error = LinkController.delete_link(link_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Link removido com sucesso'})
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    elif request.method == 'PUT':
        # Obter dados da requisição
        data = request.json
        message = data.get('custom_message')
        is_active = data.get('is_active')
        
        # Chamar o controller para atualizar o link
        updated_link, error = LinkController.update_link(
            link_id, user_id, message, is_active
        )
        
        if updated_link:
            return jsonify({'success': True, 'message': 'Link atualizado com sucesso'})
        else:
            return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({'success': False, 'error': 'Método não permitido'}), 405

@api_bp.route('/stats/by-number')
@login_required
def get_stats_by_number():
    """API para obter estatísticas de redirecionamento por número"""
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id', 'all')
    
    if link_id == 'all':
        link_id = None
    
    # Obter estatísticas
    stats = StatsController.get_stats_by_number(user_id, start_date, end_date, link_id)
    
    # Converter valores Decimal para float para serialização JSON
    if 'number_stats' in stats:
        for stat in stats['number_stats']:
            if 'percentage' in stat and hasattr(stat['percentage'], 'as_integer_ratio'):
                stat['percentage'] = float(stat['percentage'])
    
    return jsonify(stats)

@api_bp.route('/stats/summary')
@login_required
def get_stats_summary():
    """Endpoint para obter estatísticas resumidas para o dashboard"""
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Datas de início e fim são obrigatórias'}), 400
    
    try:
        # Converter link_id para int se for fornecido
        link_id_param = int(link_id) if link_id and link_id != 'all' else None
        
        # Obter as estatísticas do controlador
        stats = StatsController.get_stats_summary(user_id, start_date, end_date, link_id_param)
        
        # Retornar dados em formato JSON
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({'error': f'Erro ao processar estatísticas: {str(e)}'}), 500

@api_bp.route('/stats/map')
@login_required
def get_stats_map():
    """API para obter dados de mapa de calor"""
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id')
    
    try:
        # Converter link_id para int se for fornecido
        link_id_param = int(link_id) if link_id and link_id != 'all' else None
        
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obter pontos de localização para o mapa de calor
        query = """
            SELECT 
                rl.latitude, 
                rl.longitude, 
                COUNT(*) as access_count,
                COALESCE(rl.city, '') || ', ' || COALESCE(rl.region, '') || ', ' || COALESCE(rl.country, '') as name
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE cl.user_id = %s
            AND rl.latitude IS NOT NULL
            AND rl.longitude IS NOT NULL
        """
        
        params = [user_id]
        
        # Adicionar filtros de data
        if start_date and end_date:
            query += " AND rl.redirect_time::date BETWEEN %s::date AND %s::date"
            params.extend([start_date, end_date])
        
        # Adicionar filtro de link específico
        if link_id_param:
            query += " AND cl.id = %s"
            params.append(link_id_param)
        
        # Agrupar por coordenadas e localização
        query += " GROUP BY rl.latitude, rl.longitude, name"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Formatar os resultados para JSON
        map_points = []
        for row in results:
            if row['latitude'] and row['longitude']:
                map_points.append({
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'count': row['access_count'],
                    'name': row['name']
                })
        
        # Consulta para obter dados de distribuição geográfica
        geo_query = """
            SELECT 
                rl.country,
                COUNT(*) as access_count
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE cl.user_id = %s
            AND rl.country IS NOT NULL
        """
        
        geo_params = [user_id]
        
        # Adicionar filtros de data
        if start_date and end_date:
            geo_query += " AND rl.redirect_time::date BETWEEN %s::date AND %s::date"
            geo_params.extend([start_date, end_date])
        
        # Adicionar filtro de link específico
        if link_id_param:
            geo_query += " AND cl.id = %s"
            geo_params.append(link_id_param)
        
        # Agrupar por país e ordenar
        geo_query += " GROUP BY rl.country ORDER BY access_count DESC"
        
        cursor.execute(geo_query, geo_params)
        geo_results = cursor.fetchall()
        
        # Formatar dados geográficos
        countries = []
        for row in geo_results:
            countries.append({
                'country': row['country'],
                'count': row['access_count']
            })
        
        return jsonify({
            'locations': map_points,
            'countries': countries
        })
        
    except Exception as e:
        logging.error(f"Erro ao obter dados de mapa: {str(e)}")
        return jsonify({'error': f'Erro ao processar dados de mapa: {str(e)}'}), 500

@api_bp.route('/redirects/recent')
@login_required
def get_recent_redirects():
    """API para obter redirecionamentos recentes"""
    user_id = session.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    link_id = request.args.get('link_id')
    limit = int(request.args.get('limit', 10))
    page = int(request.args.get('page', 1))
    
    try:
        offset = (page - 1) * limit
        
        # Converter link_id para int se for fornecido
        link_id_param = int(link_id) if link_id and link_id != 'all' else None
        
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Construir a consulta base
        query = """
            SELECT 
                rl.id,
                rl.redirect_time,
                cl.link_name,
                cl.id as link_id,
                wn.phone_number,
                wn.description as number_description,
                rl.ip_address,
                rl.city,
                rl.region,
                rl.country,
                COUNT(*) OVER (PARTITION BY wn.phone_number, cl.id, DATE(rl.redirect_time)) as click_count
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            JOIN whatsapp_numbers wn ON rl.number_id = wn.id
            WHERE cl.user_id = %s
        """
        
        params = [user_id]
        
        # Adicionar filtros de data
        if start_date and end_date:
            query += " AND rl.redirect_time::date BETWEEN %s::date AND %s::date"
            params.extend([start_date, end_date])
        
        # Adicionar filtro de link específico
        if link_id_param:
            query += " AND cl.id = %s"
            params.append(link_id_param)
        
        # Adicionar ordenação e limite
        query += " ORDER BY rl.redirect_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Obter contagem total para paginação
        count_query = """
            SELECT COUNT(*) as total
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE cl.user_id = %s
        """
        
        count_params = [user_id]
        
        if start_date and end_date:
            count_query += " AND rl.redirect_time::date BETWEEN %s::date AND %s::date"
            count_params.extend([start_date, end_date])
        
        if link_id_param:
            count_query += " AND cl.id = %s"
            count_params.append(link_id_param)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        # Formatar os resultados para JSON
        redirects = []
        for row in results:
            multiple_clicks = row['click_count'] > 1
            redirects.append({
                'id': row['id'],
                'redirect_time': row['redirect_time'],
                'link_name': row['link_name'],
                'link_id': row['link_id'],
                'phone_number': row['phone_number'],
                'number_description': row['number_description'],
                'ip_address': row['ip_address'],
                'city': row['city'],
                'region': row['region'],
                'country': row['country'],
                'click_count': row['click_count'],
                'multiple_clicks': multiple_clicks
            })
        
        return jsonify({
            'results': redirects,
            'total_records': total_count,
            'page': page,
            'limit': limit,
            'show_all': False
        })
        
    except Exception as e:
        logging.error(f"Erro ao obter redirecionamentos recentes: {str(e)}")
        return jsonify({'error': f'Erro ao processar redirecionamentos: {str(e)}'}), 500

@api_bp.route('/usuarios/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """API para excluir um usuário"""
    # Verificar se o usuário logado é administrador
    if session.get('username') != 'felipe':
        return jsonify({'success': False, 'error': 'Acesso restrito ao administrador.'}), 403
    
    # Não permitir excluir certos usuários (IDs dos administradores)
    if user_id in [1, 2]:
        return jsonify({'success': False, 'error': 'Não é possível excluir usuários administradores.'}), 403
    
    try:
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o usuário existe
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': 'Usuário não encontrado.'}), 404
        
        # Guardar o nome do usuário antes de excluir para usar na mensagem
        username = user['username']
        
        try:
            # 1. Excluir registros de redirecionamento relacionados a links do usuário
            cursor.execute('''
                DELETE FROM redirect_logs
                WHERE link_id IN (
                    SELECT id FROM custom_links WHERE user_id = %s
                )
            ''', (user_id,))
            
            # 2. Excluir links do usuário
            cursor.execute('DELETE FROM custom_links WHERE user_id = %s', (user_id,))
            
            # 3. Excluir números do usuário
            cursor.execute('DELETE FROM whatsapp_numbers WHERE user_id = %s', (user_id,))
            
            # 4. Finalmente, excluir o usuário
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            
            # Commit da transação
            conn.commit()
            
            # Registrar no log
            logging.info(f"Usuário {username} (ID: {user_id}) excluído pelo administrador {session.get('username')}")
            
            return jsonify({
                'success': True, 
                'message': f'Usuário {username} excluído com sucesso.'
            })
            
        except Exception as e:
            # Reverter alterações em caso de erro
            conn.rollback()
            logging.error(f"Erro ao excluir usuário {user_id}: {str(e)}")
            return jsonify({'success': False, 'error': f'Erro ao excluir usuário: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Erro ao acessar banco de dados: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao processar solicitação: {str(e)}'}), 500

@api_bp.route('/usuarios', methods=['POST'])
@login_required
def create_user():
    """API para criar um novo usuário"""
    # Verificar se o usuário logado é administrador
    username = session.get('username')
    
    # Log para debugging
    logging.info(f"Tentativa de criar usuário pelo usuário: {username}")
    
    conn = db_adapter.get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se é admin
    cursor.execute('SELECT is_admin FROM users WHERE username = %s', (username,))
    user_data = cursor.fetchone()
    is_admin = user_data and user_data.get('is_admin', False)
    
    if username != 'felipe' and not is_admin:
        logging.warning(f"Usuário {username} tentou criar um novo usuário, mas não é administrador")
        return jsonify({'success': False, 'error': 'Acesso restrito ao administrador.'}), 403
    
    try:
        # Obter dados do formulário
        username = request.form.get('username')
        password = request.form.get('password')
        fullname = request.form.get('fullname')
        email = request.form.get('email', '')
        plan_id = request.form.get('plan_id', 1)  # Plano básico por padrão
        
        logging.info(f"Dados do formulário: username={username}, fullname={fullname}, email={email}, plan_id={plan_id}")
        
        # Validar dados básicos
        if not username or not password:
            return jsonify({'success': False, 'error': 'Usuário e senha são obrigatórios.'}), 400
        
        # Converter para inteiro
        try:
            plan_id = int(plan_id)
        except ValueError:
            return jsonify({'success': False, 'error': 'ID do plano deve ser um valor numérico.'}), 400
        
        # Verificar se o usuário já existe
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return jsonify({'success': False, 'error': 'Nome de usuário já existe.'}), 400
            
        # Verificar se o plano existe
        cursor.execute('SELECT * FROM plans WHERE id = %s', (plan_id,))
        plan = cursor.fetchone()
        
        if not plan:
            return jsonify({'success': False, 'error': 'Plano selecionado não existe.'}), 400
            
        # Criar o novo usuário
        try:
            from werkzeug.security import generate_password_hash
            
            # Gerar hash da senha com werkzeug (mesmo método usado na autenticação)
            password_hash = generate_password_hash(password)
            
            # Verificar campos disponíveis na tabela users
            cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s', ('users',))
            columns = [col['column_name'] for col in cursor.fetchall()]
            
            logging.info(f"Colunas disponíveis na tabela users: {columns}")
            
            # Construir a query de inserção com base nos campos disponíveis
            fields = ['username', 'password', 'plan_id']
            values = [username, password_hash, plan_id]
            placeholders = ['%s', '%s', '%s']
            
            # Adicionar campos opcionais se existirem na tabela
            if 'fullname' in columns and fullname:
                fields.append('fullname')
                values.append(fullname)
                placeholders.append('%s')
                
            if 'email' in columns and email:
                fields.append('email')
                values.append(email)
                placeholders.append('%s')
            
            # Construir e executar a query de inserção
            query = f'''
                INSERT INTO users ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            '''
            
            logging.info(f"Query de inserção: {query}")
            logging.info(f"Valores: {values}")
            
            cursor.execute(query, values)
            result = cursor.fetchone()
            
            if not result:
                conn.rollback()
                logging.error("Nenhum ID retornado após a inserção")
                return jsonify({'success': False, 'error': 'Erro ao inserir o usuário. Nenhum ID retornado.'}), 500
                
            new_user_id = result['id']
            conn.commit()
            
            logging.info(f"Novo usuário criado: {username} (ID: {new_user_id}) pelo administrador {session.get('username')}")
            
            return jsonify({
                'success': True, 
                'message': f'Usuário {username} criado com sucesso com o plano {plan["name"]}.',
                'user_id': new_user_id
            })
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao criar usuário: {str(e)}")
            return jsonify({'success': False, 'error': f'Erro ao criar usuário: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Erro ao processar criação de usuário: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao processar solicitação: {str(e)}'}), 500
