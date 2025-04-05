import logging
import re
from utils.db_adapter import db_adapter
from app.models.custom_link import CustomLink
from app.models.user import User


class LinkController:
    """Controlador para operações com links personalizados"""
    
    @staticmethod
    def get_links_by_user(user_id):
        """
        Obtém todos os links personalizados de um usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            list: Lista de links personalizados
        """
        try:
            return CustomLink.get_by_user(user_id)
        except Exception as e:
            logging.error(f"Erro ao buscar links do usuário: {str(e)}")
            return []
    
    @staticmethod
    def add_link(user_id, link_name, message=None):
        """
        Adiciona um novo link personalizado para um usuário
        
        Args:
            user_id (int): ID do usuário
            link_name (str): Nome do link personalizado
            message (str, optional): Mensagem personalizada. Defaults to None.
            
        Returns:
            tuple: (CustomLink, str) - Link criado e mensagem de erro (ou None se sucesso)
        """
        # Validar o nome do link
        if not link_name:
            return None, "Nome do link é obrigatório"
            
        # Remover espaços e caracteres especiais, converter para minúsculas
        link_name = re.sub(r'[^a-zA-Z0-9]', '', link_name).lower()
        
        if len(link_name) < 3:
            return None, "O nome do link deve ter pelo menos 3 caracteres"
            
        # Verificar se o link já existe (para qualquer usuário)
        existing = CustomLink.get_by_name(link_name)
        if existing:
            return None, "Este nome de link já está em uso. Escolha outro nome."
        
        # Verificar o limite de plano do usuário para links
        user = User.get_by_id(user_id)
        if not user:
            return None, "Usuário não encontrado"
            
        plan = user.get_plan()
        if not plan:
            return None, "Plano não encontrado para o usuário"
        
        current_links = LinkController.get_links_by_user(user_id)
        if len(current_links) >= plan['max_links']:
            return None, f"Limite de links atingido. Seu plano permite apenas {plan['max_links']} link(s). Contate o administrador para upgrade."
        
        # Criar novo link
        try:
            link = CustomLink(
                link_name=link_name,
                custom_message=message,
                user_id=user_id,
                is_active=True,
                click_count=0
            )
            link.save()
            logging.info(f"Novo link adicionado: {link_name} para o usuário {user_id}")
            return link, None
        except Exception as e:
            logging.error(f"Erro ao adicionar link: {str(e)}")
            return None, f"Erro ao adicionar link: {str(e)}"
    
    @staticmethod
    def update_link(link_id, user_id, message=None, is_active=None):
        """
        Atualiza um link personalizado
        
        Args:
            link_id (int): ID do link
            user_id (int): ID do usuário (para verificação de propriedade)
            message (str, optional): Nova mensagem. Defaults to None.
            is_active (bool, optional): Novo status de ativação. Defaults to None.
            
        Returns:
            tuple: (CustomLink, str) - Link atualizado e mensagem de erro (ou None se sucesso)
        """
        # Buscar o link
        link = CustomLink.get_by_id(link_id)
        if not link:
            return None, "Link não encontrado"
            
        # Verificar propriedade
        if link.user_id != user_id:
            logging.warning(f"Tentativa de atualizar link de outro usuário: {user_id} tentou atualizar link {link_id}")
            return None, "Você não tem permissão para atualizar este link"
        
        # Atualizar campos
        if message is not None:
            link.custom_message = message
            
        if is_active is not None:
            link.is_active = is_active
        
        # Salvar alterações
        try:
            link.save()
            logging.info(f"Link {link_id} atualizado pelo usuário {user_id}")
            return link, None
        except Exception as e:
            logging.error(f"Erro ao atualizar link: {str(e)}")
            return None, f"Erro ao atualizar link: {str(e)}"
    
    @staticmethod
    def delete_link(link_id, user_id):
        """
        Remove um link personalizado
        
        Args:
            link_id (int): ID do link
            user_id (int): ID do usuário (para verificação de propriedade)
            
        Returns:
            tuple: (bool, str) - Sucesso e mensagem de erro (ou None se sucesso)
        """
        # Buscar o link
        link = CustomLink.get_by_id(link_id)
        if not link:
            return False, "Link não encontrado"
            
        # Verificar propriedade
        if link.user_id != user_id:
            logging.warning(f"Tentativa de remover link de outro usuário: {user_id} tentou remover link {link_id}")
            return False, "Você não tem permissão para remover este link"
        
        # Remover o link
        try:
            success = link.delete()
            if success:
                logging.info(f"Link {link_id} removido pelo usuário {user_id}")
                return True, None
            else:
                return False, "Erro ao remover link"
        except Exception as e:
            logging.error(f"Erro ao remover link: {str(e)}")
            return False, f"Erro ao remover link: {str(e)}"
    
    @staticmethod
    def get_link_statistics(link_id, user_id):
        """
        Obtém estatísticas de um link personalizado
        
        Args:
            link_id (int): ID do link
            user_id (int): ID do usuário (para verificação de propriedade)
            
        Returns:
            tuple: (dict, str) - Estatísticas e mensagem de erro (ou None se sucesso)
        """
        # Buscar o link
        link = CustomLink.get_by_id(link_id)
        if not link:
            return None, "Link não encontrado"
            
        # Verificar propriedade
        if link.user_id != user_id:
            logging.warning(f"Tentativa de acessar estatísticas de link de outro usuário: {user_id} tentou acessar link {link_id}")
            return None, "Você não tem permissão para acessar estatísticas deste link"
        
        # Obter estatísticas
        try:
            if db_adapter.use_postgres:
                query = '''
                    SELECT 
                        COUNT(*) as total_redirects,
                        COUNT(DISTINCT number_id) as unique_numbers,
                        COUNT(DISTINCT date(timestamp)) as unique_days,
                        MAX(timestamp) as last_redirect
                    FROM redirect_logs
                    WHERE link_id = %s
                '''
            else:
                query = '''
                    SELECT 
                        COUNT(*) as total_redirects,
                        COUNT(DISTINCT number_id) as unique_numbers,
                        COUNT(DISTINCT date(timestamp)) as unique_days,
                        MAX(timestamp) as last_redirect
                    FROM redirect_logs
                    WHERE link_id = ?
                '''
            
            stats = db_adapter.execute_query(query, (link_id,))
            
            if not stats:
                stats = {
                    'total_redirects': 0,
                    'unique_numbers': 0,
                    'unique_days': 0,
                    'last_redirect': None
                }
            
            # Adicionar informações básicas do link
            stats['link_name'] = link.link_name
            stats['click_count'] = link.click_count
            
            return stats, None
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas de link: {str(e)}")
            return None, f"Erro ao obter estatísticas: {str(e)}"

    @staticmethod
    def create_default_link(user_id):
        """
        Cria um link padrão para o usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            CustomLink: Link padrão criado
        """
        # Verificar se o usuário já tem um link padrão
        links = CustomLink.get_by_user(user_id)
        if links:
            # Se já tem links, verificar se algum tem ID 1 (link padrão)
            for link in links:
                if link.id == 1:
                    return link
        
        # Criar link padrão
        default_message = "Você será redirecionado para um de nossos atendentes. Aguarde um momento..."
        link, error = LinkController.add_link(user_id, "padrao", default_message)
        if error:
            logging.error(f"Erro ao criar link padrão: {error}")
            # Tentar com um nome alternativo
            link, error = LinkController.add_link(user_id, "default", default_message)
            if error:
                logging.error(f"Erro ao criar link alternativo: {error}")
                # Tentar com o ID do usuário
                link_name = f"user{user_id}"
                link, error = LinkController.add_link(user_id, link_name, default_message)
                if error:
                    raise Exception(f"Não foi possível criar um link padrão: {error}")
        
        return link
