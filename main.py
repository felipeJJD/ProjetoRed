import os
import logging
import argparse
from app import create_app

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Servidor de Redirecionamento WhatsApp')
    parser.add_argument('-p', '--port', type=int, default=int(os.environ.get('PORT', 3000)),
                        help='Porta para executar o servidor (padrão: 3000)')
    parser.add_argument('-d', '--debug', action='store_true', 
                        default=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true',
                        help='Executar em modo debug (padrão: True)')
    return parser.parse_args()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Criar a aplicação
app = create_app()

if __name__ == '__main__':
    # Obter argumentos da linha de comando
    args = parse_args()
    
    # Iniciar o servidor
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)
