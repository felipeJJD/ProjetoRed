from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.controllers.number_controller import NumberController
from app.controllers.link_controller import LinkController
from app.services.analytics import AnalyticsService
from app.routes.auth_routes import login_required
from app.models.user import User
import logging
from utils.db_adapter import db_adapter


# Criar blueprint para rotas administrativas
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Rota para o painel administrativo"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if not user:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Buscar todos os números do usuário (ativos e inativos)
    numbers = NumberController.get_all_numbers_by_user(user_id)
    
    # Buscar links personalizados
    links = LinkController.get_links_by_user(user_id)
    
    # Se não houver links, criar o link padrão
    if not links:
        try:
            default_link = LinkController.create_default_link(user_id)
            links = [default_link]
        except Exception as e:
            flash(f'Erro ao criar link padrão: {str(e)}', 'danger')
    
    # Obter dados do plano
    user_plan = user.get_plan()
    
    # Número de chips ativos (para verificação de limite)
    active_numbers = [n for n in numbers if n['is_active']]
    
    # Usar o template dashboard.html em vez de administracao.html
    return render_template('dashboard.html', 
                          user=user, 
                          numbers=numbers, 
                          links=links, 
                          plan=user_plan,
                          active_numbers_count=len(active_numbers))


@admin_bp.route('/numbers')
@login_required
def manage_numbers():
    """Rota para gerenciar números de WhatsApp"""
    user_id = session.get('user_id')
    numbers = NumberController.get_numbers_by_user(user_id)
    
    return render_template('administracao.html', numbers=numbers, active_tab='numbers')


@admin_bp.route('/numbers/add', methods=['GET', 'POST'])
@login_required
def add_number():
    """Rota para adicionar um novo número de WhatsApp"""
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        description = request.form.get('description')
        user_id = session.get('user_id')
        
        number, error = NumberController.add_number(user_id, phone_number, description)
        
        if number:
            flash('Número adicionado com sucesso!', 'success')
            return redirect(url_for('admin.manage_numbers'))
        else:
            flash(error, 'danger')
    
    return render_template('administracao.html', active_tab='numbers', action='add_number')


@admin_bp.route('/numbers/edit/<int:number_id>', methods=['GET', 'POST'])
@login_required
def edit_number(number_id):
    """Rota para editar um número de WhatsApp"""
    user_id = session.get('user_id')
    
    # Obter o número atual
    number = NumberController.get_by_id(number_id)
    if not number or number.user_id != user_id:
        flash('Número não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('admin.manage_numbers'))
    
    if request.method == 'POST':
        description = request.form.get('description')
        is_active = bool(request.form.get('is_active'))
        
        updated_number, error = NumberController.update_number(
            number_id, user_id, description, is_active
        )
        
        if updated_number:
            flash('Número atualizado com sucesso!', 'success')
            return redirect(url_for('admin.manage_numbers'))
        else:
            flash(error, 'danger')
    
    return render_template('administracao.html', number=number, active_tab='numbers', action='edit_number')


@admin_bp.route('/numbers/delete/<int:number_id>', methods=['POST'])
@login_required
def delete_number(number_id):
    """Rota para remover um número de WhatsApp"""
    user_id = session.get('user_id')
    
    success, error = NumberController.delete_number(number_id, user_id)
    
    if success:
        flash('Número removido com sucesso!', 'success')
    else:
        flash(error, 'danger')
    
    return redirect(url_for('admin.manage_numbers'))


@admin_bp.route('/links')
@login_required
def manage_links():
    """Rota para gerenciar links personalizados"""
    user_id = session.get('user_id')
    links = LinkController.get_links_by_user(user_id)
    
    return render_template('administracao.html', links=links, active_tab='links')


@admin_bp.route('/links/add', methods=['GET', 'POST'])
@login_required
def add_link():
    """Rota para adicionar um novo link personalizado"""
    if request.method == 'POST':
        link_name = request.form.get('link_name')
        message = request.form.get('message')
        user_id = session.get('user_id')
        
        link, error = LinkController.add_link(user_id, link_name, message)
        
        if link:
            flash('Link adicionado com sucesso!', 'success')
            return redirect(url_for('admin.manage_links'))
        else:
            flash(error, 'danger')
    
    return render_template('administracao.html', active_tab='links', action='add_link')


@admin_bp.route('/links/edit/<int:link_id>', methods=['GET', 'POST'])
@login_required
def edit_link(link_id):
    """Rota para editar um link personalizado"""
    user_id = session.get('user_id')
    
    # Obter o link atual
    link = LinkController.get_by_id(link_id)
    if not link or link.user_id != user_id:
        flash('Link não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('admin.manage_links'))
    
    if request.method == 'POST':
        message = request.form.get('message')
        is_active = bool(request.form.get('is_active'))
        
        updated_link, error = LinkController.update_link(
            link_id, user_id, message, is_active
        )
        
        if updated_link:
            flash('Link atualizado com sucesso!', 'success')
            return redirect(url_for('admin.manage_links'))
        else:
            flash(error, 'danger')
    
    return render_template('administracao.html', link=link, active_tab='links', action='edit_link')


@admin_bp.route('/links/delete/<int:link_id>', methods=['POST'])
@login_required
def delete_link(link_id):
    """Rota para remover um link personalizado"""
    user_id = session.get('user_id')
    
    success, error = LinkController.delete_link(link_id, user_id)
    
    if success:
        flash('Link removido com sucesso!', 'success')
    else:
        flash(error, 'danger')
    
    return redirect(url_for('admin.manage_links'))


@admin_bp.route('/links/stats/<int:link_id>')
@login_required
def link_stats(link_id):
    """Rota para visualizar estatísticas de um link personalizado"""
    user_id = session.get('user_id')
    
    stats, error = LinkController.get_link_statistics(link_id, user_id)
    
    if not stats:
        flash(error, 'danger')
        return redirect(url_for('admin.manage_links'))
    
    return render_template('administracao.html', stats=stats, active_tab='links', action='link_stats')


@admin_bp.route('/administracao')
@login_required
def administracao():
    """Rota alternativa para a página de administração"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if not user:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Obter todos os números do usuário (ativos e inativos)
    numbers = NumberController.get_all_numbers_by_user(user_id)
    
    # Buscar links personalizados
    links = LinkController.get_links_by_user(user_id)
    
    # Obter dados do plano
    user_plan = user.get_plan()
    
    # Número de chips ativos (para verificação de limite)
    active_numbers = [n for n in numbers if n['is_active']]
    
    return render_template(
        'administracao.html',
        user=user,
        numbers=numbers,
        links=links,
        plan=user_plan,
        active_numbers_count=len(active_numbers)
    )


@admin_bp.route('/admin_backup')
@login_required
def admin_backup():
    """Rota de backup para administração"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if not user:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Obter todos os números do usuário (ativos e inativos)
    numbers = NumberController.get_all_numbers_by_user(user_id)
    
    # Buscar links personalizados
    links = LinkController.get_links_by_user(user_id)
    
    # Obter dados do plano
    user_plan = user.get_plan()
    
    # Número de chips ativos (para verificação de limite)
    active_numbers = [n for n in numbers if n['is_active']]
    
    return render_template(
        'backup.html',
        user=user,
        numbers=numbers,
        links=links,
        plan=user_plan,
        active_numbers_count=len(active_numbers)
    )


@admin_bp.route('/admin_usuarios')
@login_required
def admin_usuarios():
    """Rota para a página de administração de usuários"""
    try:
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Buscar todos os usuários
        cursor.execute("""
            SELECT u.id, u.username, u.fullname, u.created_at, u.plan_id, u.is_admin
            FROM users u
            ORDER BY u.id ASC
        """)
        users = cursor.fetchall()
        
        # Buscar informações dos planos
        cursor.execute("SELECT * FROM plans")
        plans = cursor.fetchall()
        
        # Criar mapa de planos por ID
        plans_map = {plan['id']: plan for plan in plans}
        
        # Buscar contagem de links e números por usuário
        cursor.execute("""
            SELECT 
                user_id, 
                COUNT(*) as link_count 
            FROM custom_links 
            GROUP BY user_id
        """)
        link_counts = {row['user_id']: row['link_count'] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT 
                user_id, 
                COUNT(*) as number_count 
            FROM whatsapp_numbers 
            GROUP BY user_id
        """)
        number_counts = {row['user_id']: row['number_count'] for row in cursor.fetchall()}
        
        # Associar planos aos usuários
        user_plans = {}
        for user in users:
            if user['plan_id'] and user['plan_id'] in plans_map:
                user_plans[user['id']] = plans_map[user['plan_id']]
            else:
                # Plano padrão para usuários sem plano definido
                user_plans[user['id']] = {
                    'name': 'basic',
                    'max_links': 1,
                    'max_numbers': 2,
                    'description': 'Plano Básico (padrão)'
                }
        
        # Definir filtro de template no contexto atual em vez de no objeto app global
        def format_date(date):
            if not date:
                return 'N/A'
            try:
                if isinstance(date, str):
                    from datetime import datetime
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                return date.strftime('%d/%m/%Y %H:%M')
            except Exception as e:
                logging.error(f"Erro ao formatar data: {str(e)}")
                return str(date)
        
        return render_template(
            'admin_usuarios.html', 
            users=users, 
            user_plans=user_plans,
            user_link_counts=link_counts,
            user_number_counts=number_counts,
            formatdate=format_date
        )
        
    except Exception as e:
        logging.error(f"Erro ao carregar página de administração de usuários: {str(e)}")
        flash(f"Erro ao carregar página de usuários: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/backup_db_secret')
@login_required
def backup_db_secret():
    """Rota para download de backup do banco de dados (temporariamente indisponível)"""
    # Verificar se o usuário é administrador
    if session.get('username') != 'felipe':
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Redirecionando para o dashboard com mensagem informativa
    flash('A funcionalidade de backup do banco de dados está temporariamente indisponível.', 'warning')
    return redirect(url_for('admin.dashboard'))


def fix_database_schema():
    """Verifica e corrige o esquema do banco de dados."""
    try:
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a tabela whatsapp_numbers existe
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'whatsapp_numbers')")
        if not cursor.fetchone()[0]:
            print("Tabela whatsapp_numbers não existe. Criando tabela...")
            cursor.execute("""
                CREATE TABLE whatsapp_numbers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    number VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("Tabela whatsapp_numbers criada com sucesso!")
        else:
            # Verificar se a coluna is_active existe e seu tipo
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'whatsapp_numbers' AND column_name = 'is_active'")
            result = cursor.fetchone()
            if result:
                current_type = result[0]
                print(f"Coluna is_active existe com tipo: {current_type}")
                
                if current_type != 'boolean':
                    print("Atualizando valor padrão para NULLs na coluna is_active...")
                    # Primeiro atualiza valores NULL para 1 (true)
                    cursor.execute("UPDATE whatsapp_numbers SET is_active = 1 WHERE is_active IS NULL")
                    conn.commit()
                    
                    print("Alterando tipo da coluna is_active para boolean...")
                    # Depois altera o tipo com USING para garantir a conversão segura
                    cursor.execute("""
                        ALTER TABLE whatsapp_numbers 
                        ALTER COLUMN is_active TYPE boolean 
                        USING CASE WHEN is_active = 0 THEN false ELSE true END
                    """)
                    conn.commit()
                    print("Coluna is_active alterada para boolean com sucesso!")
                    
                    # Define o valor padrão após a conversão
                    cursor.execute("ALTER TABLE whatsapp_numbers ALTER COLUMN is_active SET DEFAULT true")
                    conn.commit()
                    print("Valor padrão da coluna is_active definido como TRUE")
            else:
                # Se a coluna não existe, adicioná-la
                print("Adicionando coluna is_active à tabela whatsapp_numbers...")
                cursor.execute("ALTER TABLE whatsapp_numbers ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
                conn.commit()
                print("Coluna is_active adicionada com sucesso!")
        
        # Verificação para custom_links
        # ... rest of the function
        
        conn.close()
    except Exception as e:
        logging.error(f"Erro ao corrigir esquema do banco de dados: {str(e)}")
        # Continue normalmente mesmo com erro

# Executar a correção no momento da importação deste módulo
fix_database_schema()
