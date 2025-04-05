from flask import render_template, jsonify, request
import logging


def register_error_handlers(app):
    """Registra os handlers de erro para a aplicação"""
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handler para erro 404 - Página não encontrada"""
        logging.warning(f"Erro 404: {request.path} - {e}")
        
        # Verificar se é uma requisição Ajax/API
        if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error=str(e), code=404), 404
            
        return render_template('errors/404.html', error=str(e)), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """Handler para erro 500 - Erro interno do servidor"""
        logging.error(f"Erro 500: {request.path} - {e}")
        
        # Verificar se é uma requisição Ajax/API
        if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error="Erro interno do servidor", code=500), 500
            
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handler para erro 403 - Acesso proibido"""
        logging.warning(f"Erro 403: {request.path} - {e}")
        
        # Verificar se é uma requisição Ajax/API
        if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error="Acesso proibido", code=403), 403
            
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handler para erro 400 - Requisição inválida"""
        logging.warning(f"Erro 400: {request.path} - {e}")
        
        # Verificar se é uma requisição Ajax/API
        if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error=str(e), code=400), 400
            
        return render_template('errors/400.html', error=str(e)), 400
