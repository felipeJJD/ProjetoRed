import os
import logging
from app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Criar a instância da aplicação
app = create_app()

if __name__ == '__main__':
    # Obter a porta do ambiente (para compatibilidade com Railway e outros provedores)
    port = int(os.environ.get('PORT', 3000))
    
    # Definir a configuração de debug
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Iniciar o servidor
    app.run(host='0.0.0.0', port=port, debug=debug)