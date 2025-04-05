from app.models.user import User
from werkzeug.security import check_password_hash
import logging


class AuthController:
    """Controlador para operações de autenticação"""
    
    @staticmethod
    def login(username, password):
        """
        Autentica um usuário com base no nome de usuário e senha
        
        Args:
            username (str): Nome de usuário
            password (str): Senha
            
        Returns:
            tuple: (User, str) - Usuário autenticado e mensagem de erro (ou None se sucesso)
        """
        if not username or not password:
            return None, "Nome de usuário e senha são obrigatórios"
            
        try:
            logging.info(f"Tentando autenticar usuário: {username}")
            user = User.get_by_username(username)
            
            if not user:
                logging.warning(f"Usuário não encontrado: {username}")
                return None, "Usuário não encontrado"
                
            logging.info(f"Verificando senha para usuário: {username}")
            
            # Verificar se a senha está no formato werkzeug
            try:
                if check_password_hash(user.password, password):
                    logging.info(f"Login bem-sucedido para o usuário: {username}")
                    return user, None
            except Exception as e:
                logging.warning(f"Erro ao verificar senha com werkzeug: {str(e)}")
                
            # Verificar se a senha está no formato bcrypt
            try:
                import bcrypt
                stored_password = user.password
                
                # Se parece ser um hash bcrypt (começa com $2b$ ou $2a$)
                if stored_password.startswith(('$2b$', '$2a$')):
                    if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                        logging.info(f"Login bem-sucedido para o usuário: {username} usando bcrypt")
                        return user, None
            except ImportError:
                logging.warning("Módulo bcrypt não encontrado, pulando verificação de senha bcrypt")
            except Exception as e:
                logging.warning(f"Erro ao verificar senha com bcrypt: {str(e)}")
                
            # Se a senha não está em formato hash, verifique diretamente (para fins de desenvolvimento/teste)
            if user.password == password:
                logging.warning("Senha em texto plano corresponde, mas formato hash falhou")
                return user, None
                
            return None, "Senha incorreta"
        except Exception as e:
            logging.error(f"Erro durante o login: {str(e)}")
            return None, f"Erro ao processar o login: {str(e)}"
    
    @staticmethod
    def register(username, password, password_confirm):
        """
        Registra um novo usuário
        
        Args:
            username (str): Nome de usuário
            password (str): Senha
            password_confirm (str): Confirmação de senha
            
        Returns:
            tuple: (User, str) - Usuário criado e mensagem de erro (ou None se sucesso)
        """
        # Validar entradas
        if not username or not password:
            return None, "Nome de usuário e senha são obrigatórios"
            
        if password != password_confirm:
            return None, "As senhas não coincidem"
        
        # Verificar se o usuário já existe
        existing_user = User.get_by_username(username)
        if existing_user:
            return None, "Este nome de usuário já está em uso"
            
        try:
            # Criar usuário (usando plano básico por padrão)
            user = User.create(username, password, plan_id=1)
            logging.info(f"Novo usuário registrado: {username}")
            return user, None
        except Exception as e:
            logging.error(f"Erro ao registrar usuário: {str(e)}")
            return None, f"Erro ao registrar usuário: {str(e)}"
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Obtém um usuário pelo ID
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            User: Objeto de usuário ou None se não encontrado
        """
        try:
            return User.get_by_id(user_id)
        except Exception as e:
            logging.error(f"Erro ao buscar usuário por ID: {str(e)}")
            return None
