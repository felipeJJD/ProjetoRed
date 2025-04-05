from flask import Blueprint, redirect, request, abort
from app.controllers.redirect_controller import RedirectController
from utils.db_adapter import db_adapter
import logging


# Criar blueprint para rotas de redirecionamento
redirect_bp = Blueprint('redirect', __name__)


@redirect_bp.route('/<link_name>')
def redirect_to_whatsapp(link_name):
    """
    Rota principal para redirecionar para WhatsApp usando um link personalizado
    
    Args:
        link_name (str): Nome do link personalizado
    """
    try:
        # Obter o IP real do cliente, considerando proxies
        client_ip = get_real_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')
        
        # Registrar a tentativa de redirecionamento
        logging.info(f"Tentativa de redirecionamento para link: {link_name} | IP: {client_ip}")
        
        # Processar o redirecionamento através do controlador
        redirect_url, error = RedirectController.redirect_whatsapp(
            link_name, 
            client_ip=client_ip, 
            user_agent=user_agent
        )
        
        if redirect_url:
            logging.info(f"Redirecionando para: {redirect_url}")
            return redirect(redirect_url)
        else:
            logging.warning(f"Falha no redirecionamento para {link_name}: {error}")
            abort(404, description=error)
            
    except Exception as e:
        logging.error(f"Erro no redirecionamento para {link_name}: {str(e)}")
        abort(500, description="Ocorreu um erro ao processar seu redirecionamento.")


@redirect_bp.route('/<prefix>/<link_name>')
def redirect_with_prefix(prefix, link_name):
    """
    Rota alternativa para redirecionar com um prefixo
    O prefixo é tratado como o ID do usuário
    
    Args:
        prefix (str): Prefixo do link (ID do usuário)
        link_name (str): Nome do link personalizado
    """
    try:
        # Obter o IP real do cliente, considerando proxies
        client_ip = get_real_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')
        
        # Verificar se o prefixo é um número (ID de usuário)
        user_id = None
        try:
            user_id = int(prefix)
        except ValueError:
            abort(404, description="Link inválido. Prefixo deve ser um número.")
        
        # Registrar a tentativa de redirecionamento
        logging.info(f"Tentativa de redirecionamento para link com prefixo: {prefix}/{link_name} | IP: {client_ip}")
        
        # Buscar link específico do usuário (user_id)
        conn = db_adapter.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM custom_links WHERE link_name = %s AND user_id = %s', 
                        (link_name, user_id))
            link = cursor.fetchone()
            
            if not link:
                logging.warning(f"Link não encontrado para usuário específico: {prefix}/{link_name}")
                abort(404, description="Link não encontrado para este usuário.")
                
            # Processar o redirecionamento usando o link encontrado
            redirect_url, error = RedirectController.redirect_whatsapp_with_link(
                link,
                client_ip=client_ip, 
                user_agent=user_agent
            )
            
            if redirect_url:
                logging.info(f"Redirecionando para: {redirect_url}")
                return redirect(redirect_url)
            else:
                logging.warning(f"Falha no redirecionamento para {prefix}/{link_name}: {error}")
                abort(404, description=error)
        finally:
            conn.close()
            
    except Exception as e:
        logging.error(f"Erro no redirecionamento para {prefix}/{link_name}: {str(e)}")
        abort(500, description="Ocorreu um erro ao processar seu redirecionamento.")


def get_real_client_ip(request):
    """
    Obtém o endereço IP real do cliente, considerando proxies
    
    Args:
        request: Objeto de requisição Flask
        
    Returns:
        str: Endereço IP real do cliente
    """
    # Tentar obter o IP a partir de cabeçalhos comuns usados por proxies
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP',     
        'X-Client-IP'
    ]
    
    for header in headers_to_check:
        if header in request.headers:
            # X-Forwarded-For pode conter múltiplos IPs separados por vírgula
            if header == 'X-Forwarded-For':
                forwarded_for = request.headers.get(header, '')
                ip_list = [ip.strip() for ip in forwarded_for.split(',')]
                if ip_list and ip_list[0]:
                    logging.info(f"IP obtido do cabeçalho {header}: {ip_list[0]}")
                    return ip_list[0]
            else:
                ip = request.headers.get(header)
                if ip:
                    logging.info(f"IP obtido do cabeçalho {header}: {ip}")
                    return ip
    
    # Se não encontrar em nenhum cabeçalho, usar o remote_addr padrão
    ip = request.remote_addr
    logging.info(f"IP obtido de request.remote_addr: {ip}")
    return ip
