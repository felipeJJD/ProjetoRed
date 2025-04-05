from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.redirect_routes import redirect_bp
from app.routes.api_routes import api_bp


def register_routes(app):
    """Registra todas as rotas da aplicação"""
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp)  # Já tem url_prefix='/api' definido
    app.register_blueprint(redirect_bp)  # Sem prefixo, para capturar rotas de redirecionamento
    
    # Rota raiz (página com botão "Falar com Atendente")
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')