import logging
from app.models.whatsapp_number import WhatsAppNumber
from app.models.user import User
from app.controllers.redirect_controller import RedirectController
from utils.db_adapter import db_adapter


class NumberController:
    """Controlador para operações com números de WhatsApp"""
    
    @staticmethod
    def get_numbers_by_user(user_id):
        """
        Obtém todos os números de WhatsApp de um usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            list: Lista de números de WhatsApp
        """
        try:
            with db_adapter.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM whatsapp_numbers WHERE user_id = %s', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Erro ao buscar números do usuário: {str(e)}")
            return []
    
    @staticmethod
    def add_number(user_id, phone_number, description=None):
        """
        Adiciona um novo número de WhatsApp para um usuário
        
        Args:
            user_id (int): ID do usuário
            phone_number (str): Número de telefone
            description (str, optional): Descrição do número. Defaults to None.
            
        Returns:
            tuple: (WhatsAppNumber, str) - Número criado e mensagem de erro (ou None se sucesso)
        """
        # Validar o número de telefone
        validated_number = RedirectController.validate_phone_number(phone_number)
        if not validated_number:
            return None, "Número de telefone inválido. Use o formato: 5541999887766"
        
        # Verificar se o número já existe para este usuário
        existing = WhatsAppNumber.get_by_phone(validated_number, user_id)
        if existing:
            return None, "Este número já está cadastrado para o seu usuário"
        
        # Verificar o limite de plano do usuário para números
        user = User.get_by_id(user_id)
        if not user:
            return None, "Usuário não encontrado"
            
        plan = user.get_plan()
        if not plan:
            return None, "Plano não encontrado para o usuário"
        
        # Contar apenas números ATIVOS para verificar o limite do plano
        active_numbers = WhatsAppNumber.get_active_by_user(user_id)
        if len(active_numbers) >= plan['max_numbers']:
            return None, f"Limite de chips ativos atingido. Seu plano permite apenas {plan['max_numbers']} chip(s) ativo(s). Contate o administrador para upgrade."
        
        # Criar novo número
        try:
            number = WhatsAppNumber(
                phone_number=validated_number,
                description=description,
                is_active=True,
                user_id=user_id,
                redirect_count=0
            )
            number.save()
            logging.info(f"Novo número adicionado: {validated_number} para o usuário {user_id}")
            return number, None
        except Exception as e:
            logging.error(f"Erro ao adicionar número: {str(e)}")
            return None, f"Erro ao adicionar número: {str(e)}"
    
    @staticmethod
    def update_number(number_id, user_id, description=None, is_active=None):
        """
        Atualiza um número de WhatsApp
        
        Args:
            number_id (int): ID do número
            user_id (int): ID do usuário (para verificação de propriedade)
            description (str, optional): Nova descrição. Defaults to None.
            is_active (bool, optional): Novo status de ativação. Defaults to None.
            
        Returns:
            tuple: (WhatsAppNumber, str) - Número atualizado e mensagem de erro (ou None se sucesso)
        """
        # Buscar o número
        number = WhatsAppNumber.get_by_id(number_id)
        if not number:
            return None, "Número não encontrado"
            
        # Verificar propriedade
        if number.user_id != user_id:
            logging.warning(f"Tentativa de atualizar número de outro usuário: {user_id} tentou atualizar número {number_id}")
            return None, "Você não tem permissão para atualizar este número"
        
        # Atualizar campos
        if description is not None:
            number.description = description
            
        if is_active is not None:
            number.is_active = is_active
        
        # Salvar alterações
        try:
            number.save()
            logging.info(f"Número {number_id} atualizado pelo usuário {user_id}")
            return number, None
        except Exception as e:
            logging.error(f"Erro ao atualizar número: {str(e)}")
            return None, f"Erro ao atualizar número: {str(e)}"
    
    @staticmethod
    def delete_number(number_id, user_id):
        """
        Desativa um número de WhatsApp (exclusão lógica)
        
        Args:
            number_id (int): ID do número
            user_id (int): ID do usuário (para verificação de propriedade)
            
        Returns:
            tuple: (bool, str) - Sucesso e mensagem de erro (ou None se sucesso)
        """
        # Buscar o número
        number = WhatsAppNumber.get_by_id(number_id)
        if not number:
            return False, "Número não encontrado"
            
        # Verificar propriedade
        if number.user_id != user_id:
            logging.warning(f"Tentativa de desativar número de outro usuário: {user_id} tentou desativar número {number_id}")
            return False, "Você não tem permissão para desativar este número"
        
        # Se o número já estiver desativado, retornar sucesso
        if not number.is_active:
            return True, "Número já estava desativado"
        
        # Atualizar o status para inativo
        try:
            number.is_active = False
            number.save()
            logging.info(f"Número {number_id} desativado pelo usuário {user_id}")
            return True, None
        except Exception as e:
            logging.error(f"Erro ao desativar número: {str(e)}")
            return False, f"Erro ao desativar número: {str(e)}"
    
    @staticmethod
    def reactivate_number(number_id, user_id):
        """
        Reativa um número de WhatsApp que estava desativado
        
        Args:
            number_id (int): ID do número
            user_id (int): ID do usuário (para verificação de propriedade)
            
        Returns:
            tuple: (bool, str) - Sucesso e mensagem de erro (ou None se sucesso)
        """
        # Buscar o número
        number = WhatsAppNumber.get_by_id(number_id)
        if not number:
            return False, "Número não encontrado"
            
        # Verificar propriedade
        if number.user_id != user_id:
            logging.warning(f"Tentativa de reativar número de outro usuário: {user_id} tentou reativar número {number_id}")
            return False, "Você não tem permissão para reativar este número"
        
        # Se o número já estiver ativo, retornar sucesso
        if number.is_active:
            return True, "Número já estava ativo"
        
        # Verificar o limite de plano do usuário para números ativos
        user = User.get_by_id(user_id)
        if not user:
            return False, "Usuário não encontrado"
            
        plan = user.get_plan()
        if not plan:
            return False, "Plano não encontrado para o usuário"
        
        # Contar apenas números ATIVOS
        active_numbers = WhatsAppNumber.get_active_by_user(user_id)
        if len(active_numbers) >= plan['max_numbers']:
            return False, f"Você já atingiu o limite de {plan['max_numbers']} chip(s) ativo(s) do seu plano. Para ativar este número, desative outro ou contate o administrador para upgrade do plano."
        
        # Reativar o número
        try:
            number.is_active = True
            number.save()
            logging.info(f"Número {number_id} reativado pelo usuário {user_id}")
            return True, None
        except Exception as e:
            logging.error(f"Erro ao reativar número: {str(e)}")
            return False, f"Erro ao reativar número: {str(e)}"

    @staticmethod
    def get_all_numbers_by_user(user_id):
        """
        Obtém todos os números de WhatsApp de um usuário (ativos e inativos)
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            list: Lista de números de WhatsApp
        """
        try:
            with db_adapter.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM whatsapp_numbers WHERE user_id = %s', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Erro ao buscar todos os números do usuário: {str(e)}")
            return []
