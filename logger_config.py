import logging
import time
import functools
import os
from datetime import datetime

# Configurar diretório de logs
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Logger para consultas de banco de dados
db_logger = logging.getLogger('database')
db_logger.setLevel(logging.INFO)

# Logger para erros críticos
error_logger = logging.getLogger('errors')
error_logger.setLevel(logging.ERROR)

# Logger para performance
perf_logger = logging.getLogger('performance')
perf_logger.setLevel(logging.INFO)

# Logger para acessos
access_logger = logging.getLogger('access')
access_logger.setLevel(logging.INFO)

# Formatação dos logs
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')

# Handlers para arquivo
hoje = datetime.now().strftime('%Y-%m-%d')

# Handler para logs de banco de dados
db_handler = logging.FileHandler(os.path.join(LOG_DIR, f'db_{hoje}.log'))
db_handler.setFormatter(log_formatter)
db_logger.addHandler(db_handler)

# Handler para logs de erro
error_handler = logging.FileHandler(os.path.join(LOG_DIR, f'error_{hoje}.log'))
error_handler.setFormatter(log_formatter)
error_logger.addHandler(error_handler)

# Handler para logs de performance
perf_handler = logging.FileHandler(os.path.join(LOG_DIR, f'performance_{hoje}.log'))
perf_handler.setFormatter(log_formatter)
perf_logger.addHandler(perf_handler)

# Handler para logs de acesso
access_handler = logging.FileHandler(os.path.join(LOG_DIR, f'access_{hoje}.log'))
access_handler.setFormatter(log_formatter)
access_logger.addHandler(access_handler)

# Handler para console (todos os logs)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Adicionar handler de console apenas em ambiente de desenvolvimento
if os.environ.get('FLASK_ENV') == 'development':
    db_logger.addHandler(console_handler)
    error_logger.addHandler(console_handler)
    perf_logger.addHandler(console_handler)

def log_query_time(func):
    """Decorator para registrar o tempo de execução de consultas"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Classificação de performance
        performance_category = "NORMAL"
        if elapsed_time > 1.0:
            performance_category = "LENTO"
        elif elapsed_time > 0.5:
            performance_category = "ATENÇÃO"
        elif elapsed_time < 0.1:
            performance_category = "RÁPIDO"
        
        # Registrar detalhes da função
        func_name = func.__name__
        module_name = func.__module__
        
        db_logger.info(
            f"{performance_category} [{module_name}.{func_name}] - {elapsed_time:.4f}s"
        )
        
        # Registrar em caso de operações lentas
        if elapsed_time > 1.0:
            perf_logger.warning(
                f"Operação lenta: [{module_name}.{func_name}] - {elapsed_time:.4f}s"
            )
            
        return result
    return wrapper

def log_error(error, context=None):
    """Função para registrar erros críticos"""
    error_msg = f"ERRO: {error}"
    if context:
        error_msg += f" | Contexto: {context}"
    
    error_logger.error(error_msg)

def log_access(endpoint, user_id=None, ip=None, success=True):
    """Função para registrar acessos ao sistema"""
    status = "SUCESSO" if success else "FALHA"
    user_info = f"user_id={user_id}" if user_id else "anônimo"
    ip_info = f"ip={ip}" if ip else "ip=desconhecido"
    
    access_logger.info(f"{status} | {endpoint} | {user_info} | {ip_info}")
