import os
import logging
from flask import Flask
from config.settings import load_config
from utils.db_adapter import db_adapter
from app.routes import register_routes
from app.error_handlers import register_error_handlers
from datetime import datetime


def create_app(test_config=None):
    """Cria e configura a instância da aplicação Flask"""
    # Criar e configurar a app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Carregar configurações
    if test_config:
        app.config.from_mapping(test_config)
    else:
        config = load_config()()  # Instanciar a classe de configuração
        app.config['SECRET_KEY'] = config.SECRET_KEY
        app.config['DEBUG'] = config.DEBUG
        app.config['TESTING'] = config.TESTING
        # Outras configurações específicas que precisamos
        app.config['USE_POSTGRES'] = config.USE_POSTGRES
        app.config['POSTGRES_HOST'] = config.POSTGRES_HOST
        app.config['POSTGRES_PORT'] = config.POSTGRES_PORT
        app.config['POSTGRES_DB'] = config.POSTGRES_DB
        app.config['POSTGRES_USER'] = config.POSTGRES_USER
        app.config['POSTGRES_PASSWORD'] = config.POSTGRES_PASSWORD
    
    # Configurar logging
    logging_level = app.config.get('LOGGING_LEVEL', logging.INFO)
    logging.basicConfig(
        level=logging_level,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configurar a chave secreta
    app.secret_key = app.config.get('SECRET_KEY', os.urandom(24))
    
    # Inicializar o adaptador de banco de dados
    db_adapter.init_app(app)
    
    # Registrar filtros personalizados do Jinja2
    @app.template_filter('datetime')
    def format_datetime(value):
        """Formata um objeto datetime para exibição em formato brasileiro"""
        if value is None:
            return ""
        
        # Se for string, tentar converter para datetime
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return value
        
        # Se for datetime, formatar
        if isinstance(value, datetime):
            return value.strftime('%d/%m/%Y %H:%M')
        
        # Se não for reconhecido, retornar como está
        return value
    
    # Registrar rotas
    register_routes(app)
    
    # Registrar tratadores de erro
    register_error_handlers(app)
    
    # Inicializar banco de dados se necessário
    with app.app_context():
        db_adapter.init_db()
    
    return app