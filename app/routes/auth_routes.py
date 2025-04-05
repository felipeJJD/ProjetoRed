from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.controllers.auth_controller import AuthController
import logging


# Criar blueprint para rotas de autenticação
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login de usuários"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user, error = AuthController.login(username, password)
        
        if user:
            # Armazenar informações do usuário na sessão
            session['user_id'] = user.id
            session['username'] = user.username
            
            logging.info(f"Usuário logado com sucesso: {username}")
            flash('Login realizado com sucesso!', 'success')
            
            # Redirecionamento explícito para o dashboard
            response = redirect('/admin/dashboard')
            logging.info(f"Redirecionando para: /admin/dashboard")
            return response
        else:
            logging.warning(f"Falha no login para o usuário: {username}. Erro: {error}")
            flash(error, 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Rota para registro de novos usuários"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        user, error = AuthController.register(username, password, password_confirm)
        
        if user:
            logging.info(f"Novo usuário registrado: {username}")
            flash('Registro realizado com sucesso! Faça o login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            logging.warning(f"Falha no registro para o usuário: {username}. Erro: {error}")
            flash(error, 'danger')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Rota para logout de usuários"""
    # Limpar a sessão
    session.pop('user_id', None)
    session.pop('username', None)
    
    flash('Você foi desconectado com sucesso!', 'success')
    return redirect(url_for('auth.login'))


def login_required(view):
    """Decorador para proteger rotas que exigem autenticação"""
    from functools import wraps
    
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    
    return wrapped_view
