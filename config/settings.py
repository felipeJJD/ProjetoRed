import os
from datetime import timedelta

class Config:
    """Configuração base para a aplicação"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_muito_segura')
    DEBUG = False
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True
    DATABASE_URI = None
    USE_POSTGRES = True
    
    # Configuração do PostgreSQL
    POSTGRES_HOST = os.environ.get('PGHOST', 'switchyard.proxy.rlwy.net')
    POSTGRES_PORT = os.environ.get('PGPORT', '24583')
    POSTGRES_DB = os.environ.get('PGDATABASE', 'railway')
    POSTGRES_USER = os.environ.get('PGUSER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('PGPASSWORD', 'nsAgxYUGJuIRXTalVIdclsTDecKEsgpc')
    
    # Outras configurações
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)


class DevelopmentConfig(Config):
    """Configuração para ambiente de desenvolvimento"""
    DEBUG = True
    TESTING = False
    DATABASE_URI = f"postgresql://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}"
    

class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    TESTING = False
    
    @property
    def DATABASE_URI(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class TestingConfig(Config):
    """Configuração de testes"""
    DEBUG = True
    TESTING = True
    DATABASE_URI = "postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}".format(
        POSTGRES_USER='postgres',
        POSTGRES_PASSWORD='postgres',
        POSTGRES_HOST='localhost',
        POSTGRES_PORT='5432',
        POSTGRES_DB='whatsapp_redirect_test'
    )


# Escolher configuração baseado no ambiente
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def load_config(config_name=None):
    """Carrega a configuração adequada baseada no ambiente ou nome especificado"""
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'default')
    return config_by_name.get(config_name, config_by_name['default'])

# Configuração ativa - corrigida para instanciar a classe
active_config = load_config()()
