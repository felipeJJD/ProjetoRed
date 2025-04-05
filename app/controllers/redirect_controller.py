import logging
import random
from datetime import datetime
from app.models.custom_link import CustomLink
from app.models.whatsapp_number import WhatsAppNumber
from app.models.redirect_log import RedirectLog
from app.services.balancer import NumberBalancer
from app.services.geolocation import GeoLocationService
from utils.db_adapter import db_adapter


class RedirectController:
    """Controlador para operações de redirecionamento"""
    
    @staticmethod
    def redirect_whatsapp(link_name, client_ip=None, user_agent=None):
        """
        Realiza o redirecionamento para WhatsApp com base em um link personalizado
        
        Args:
            link_name (str): Nome do link personalizado
            client_ip (str, optional): Endereço IP do cliente. Defaults to None.
            user_agent (str, optional): User Agent do cliente. Defaults to None.
            
        Returns:
            tuple: (url, error) - URL de redirecionamento e mensagem de erro (ou None se sucesso)
        """
        redirect_start_time = datetime.now()
        conn = None
        log_id = None
        
        try:
            conn = db_adapter.get_db_connection()
            
            # Buscar link pelo nome
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM custom_links WHERE link_name = %s', (link_name,))
            link = cursor.fetchone()
            
            if not link:
                logging.warning(f"Link não encontrado: {link_name}")
                return None, "Link não encontrado."
            
            # Verificar se o link está ativo
            if not link['is_active']:
                logging.warning(f"Tentativa de acesso a link inativo: {link_name}")
                return None, "Este link está inativo."
            
            # Incrementar o contador de cliques
            try:
                cursor.execute('UPDATE custom_links SET click_count = COALESCE(click_count, 0) + 1 WHERE id = %s', (link['id'],))
                conn.commit()
                logging.info(f"Contador de cliques incrementado para o link_id={link['id']}")
            except Exception as e:
                logging.error(f"Erro ao incrementar contador de cliques: {str(e)}")
                conn.rollback()
                # Continuar mesmo se falhar o contador
            
            # Obter todos os números ativos do usuário proprietário do link
            cursor.execute('SELECT * FROM whatsapp_numbers WHERE user_id = %s AND is_active = 1', 
                           (link['user_id'],))
            numbers = cursor.fetchall()
            
            if not numbers:
                logging.error(f"Nenhum número ativo encontrado para user_id={link['user_id']}")
                return None, "Não há números disponíveis para este link."
            
            logging.info(f"Encontrados {len(numbers)} números ativos para o usuário {link['user_id']}")
            
            # Selecionar um número - lógica melhorada para balanceamento
            selected_number = NumberBalancer.select_number(numbers, link['id'])
            
            # Incrementar contador do número selecionado
            try:
                cursor.execute('UPDATE whatsapp_numbers SET redirect_count = redirect_count + 1 WHERE id = %s', 
                              (selected_number['id'],))
                conn.commit()
            except Exception as e:
                logging.error(f"Erro ao incrementar contador do número: {str(e)}")
                conn.rollback()
                # Continuar mesmo com erro no contador
            
            # Inserir log de redirecionamento
            try:
                if db_adapter.use_postgres:
                    cursor.execute('''
                        INSERT INTO redirect_logs (link_id, number_id, user_agent, ip_address, redirect_time)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (link['id'], selected_number['id'], user_agent, client_ip))
                    log_id = cursor.fetchone()['id']
                else:
                    cursor.execute('''
                        INSERT INTO redirect_logs (link_id, number_id, user_agent, ip_address, timestamp)
                        VALUES (?, ?, ?, ?, datetime('now'))
                    ''', (link['id'], selected_number['id'], user_agent, client_ip))
                    log_id = cursor.lastrowid
                
                conn.commit()
            except Exception as e:
                logging.error(f"Erro ao inserir log de redirecionamento: {str(e)}")
                conn.rollback()
                log_id = None
            
            # Processar informações de localização em segundo plano (não bloquear o redirecionamento)
            try:
                if log_id:
                    # Esta chamada deve ser executada de forma assíncrona em produção
                    GeoLocationService.update_log_with_location(log_id, client_ip, db_adapter)
            except Exception as e:
                logging.error(f"Erro ao processar localização: {str(e)}")
            
            # Formatar o número para o WhatsApp
            formatted_phone = RedirectController.format_phone_number(selected_number['phone_number'])
            
            # Preparar a mensagem personalizada
            message = ''
            if link.get('message_template'):
                message = f"?text={link['message_template']}"
                # Atualizar o log com a mensagem usada
                try:
                    cursor.execute('UPDATE redirect_logs SET message = %s WHERE id = %s', 
                                (link['message_template'], log_id))
                    conn.commit()
                except Exception as e:
                    logging.error(f"Erro ao registrar mensagem no log: {str(e)}")
                    conn.rollback()
            elif link.get('custom_message'):  # Verificar campo alternativo para mensagem
                message = f"?text={link['custom_message']}"
                # Atualizar o log com a mensagem usada
                try:
                    cursor.execute('UPDATE redirect_logs SET message = %s WHERE id = %s', 
                                (link['custom_message'], log_id))
                    conn.commit()
                except Exception as e:
                    logging.error(f"Erro ao registrar mensagem no log: {str(e)}")
                    conn.rollback()
            
            # Calcular tempo de redirecionamento
            redirect_time = (datetime.now() - redirect_start_time).total_seconds()
            logging.info(f"Redirecionamento para {formatted_phone} concluído em {redirect_time:.4f} segundos.")
            
            # Redirecionar para o WhatsApp
            whatsapp_url = f"https://wa.me/{formatted_phone}{message}"
            return whatsapp_url, None
            
        except Exception as e:
            # Retornar uma mensagem de erro genérica
            logging.error(f"Erro no redirecionamento: {str(e)}")
            return None, "Ocorreu um erro ao processar seu redirecionamento. Tente novamente."
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def redirect_whatsapp_with_link(link, client_ip=None, user_agent=None):
        """
        Realiza o redirecionamento para WhatsApp usando um link já encontrado
        
        Args:
            link (dict): Objeto link encontrado na consulta
            client_ip (str, optional): Endereço IP do cliente. Defaults to None.
            user_agent (str, optional): User Agent do cliente. Defaults to None.
            
        Returns:
            tuple: (url, error) - URL de redirecionamento e mensagem de erro (ou None se sucesso)
        """
        redirect_start_time = datetime.now()
        conn = None
        log_id = None
        
        try:
            conn = db_adapter.get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se o link está ativo
            if not link['is_active']:
                logging.warning(f"Tentativa de acesso a link inativo: {link['link_name']}")
                return None, "Este link está inativo."
            
            # Incrementar o contador de cliques (já foi feito na rota, não precisamos repetir)
            
            # Obter todos os números ativos do usuário proprietário do link
            cursor.execute('SELECT * FROM whatsapp_numbers WHERE user_id = %s AND is_active = 1', 
                        (link['user_id'],))
            numbers = cursor.fetchall()
            
            if not numbers:
                logging.error(f"Nenhum número ativo encontrado para user_id={link['user_id']}")
                return None, "Não há números disponíveis para este link."
            
            logging.info(f"Encontrados {len(numbers)} números ativos para o usuário {link['user_id']}")
            
            # Selecionar um número - lógica melhorada para balanceamento
            selected_number = NumberBalancer.select_number(numbers, link['id'])
            
            # Incrementar contador do número selecionado
            try:
                cursor.execute('UPDATE whatsapp_numbers SET redirect_count = redirect_count + 1 WHERE id = %s', 
                            (selected_number['id'],))
                conn.commit()
            except Exception as e:
                logging.error(f"Erro ao incrementar contador do número: {str(e)}")
                conn.rollback()
                # Continuar mesmo com erro no contador
            
            # Inserir log de redirecionamento
            try:
                if db_adapter.use_postgres:
                    cursor.execute('''
                        INSERT INTO redirect_logs (link_id, number_id, user_agent, ip_address, redirect_time)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (link['id'], selected_number['id'], user_agent, client_ip))
                    log_id = cursor.fetchone()['id']
                else:
                    cursor.execute('''
                        INSERT INTO redirect_logs (link_id, number_id, user_agent, ip_address, timestamp)
                        VALUES (?, ?, ?, ?, datetime('now'))
                    ''', (link['id'], selected_number['id'], user_agent, client_ip))
                    log_id = cursor.lastrowid
                
                conn.commit()
            except Exception as e:
                logging.error(f"Erro ao inserir log de redirecionamento: {str(e)}")
                conn.rollback()
                log_id = None
            
            # Processar informações de localização em segundo plano (não bloquear o redirecionamento)
            try:
                if log_id:
                    # Esta chamada deve ser executada de forma assíncrona em produção
                    GeoLocationService.update_log_with_location(log_id, client_ip, db_adapter)
            except Exception as e:
                logging.error(f"Erro ao processar localização: {str(e)}")
            
            # Formatar o número para o WhatsApp
            formatted_phone = RedirectController.format_phone_number(selected_number['phone_number'])
            
            # Preparar a mensagem personalizada
            message = ''
            if link.get('message_template'):
                message = f"?text={link['message_template']}"
                # Atualizar o log com a mensagem usada
                try:
                    cursor.execute('UPDATE redirect_logs SET message = %s WHERE id = %s', 
                                (link['message_template'], log_id))
                    conn.commit()
                except Exception as e:
                    logging.error(f"Erro ao registrar mensagem no log: {str(e)}")
                    conn.rollback()
            elif link.get('custom_message'):  # Verificar campo alternativo para mensagem
                message = f"?text={link['custom_message']}"
                # Atualizar o log com a mensagem usada
                try:
                    cursor.execute('UPDATE redirect_logs SET message = %s WHERE id = %s', 
                                (link['custom_message'], log_id))
                    conn.commit()
                except Exception as e:
                    logging.error(f"Erro ao registrar mensagem no log: {str(e)}")
                    conn.rollback()
            
            # Calcular tempo de redirecionamento
            redirect_time = (datetime.now() - redirect_start_time).total_seconds()
            logging.info(f"Redirecionamento para {formatted_phone} concluído em {redirect_time:.4f} segundos.")
            
            # Redirecionar para o WhatsApp
            whatsapp_url = f"https://wa.me/{formatted_phone}{message}"
            return whatsapp_url, None
            
        except Exception as e:
            # Retornar uma mensagem de erro genérica
            logging.error(f"Erro no redirecionamento com link: {str(e)}")
            return None, "Ocorreu um erro ao processar seu redirecionamento. Tente novamente."
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def format_phone_number(phone_number):
        """
        Formata o número de telefone para o padrão do WhatsApp
        
        Args:
            phone_number (str): Número de telefone original
            
        Returns:
            str: Número formatado para o WhatsApp
        """
        # Remover caracteres não numéricos
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Garantir que o número comece com código do país
        if not digits_only.startswith('55'):
            digits_only = '55' + digits_only
            
        return digits_only
    
    @staticmethod
    def validate_phone_number(phone_number):
        """
        Valida e formata um número de telefone
        
        Args:
            phone_number (str): Número de telefone a ser validado
            
        Returns:
            str: Número formatado ou None se inválido
        """
        # Remover caracteres não numéricos
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Verificar tamanho válido (com e sem código do país)
        if len(digits_only) < 10:  # Muito curto para ser válido
            return None
            
        # Se começar com código do país brasileiro, verificar tamanho total
        if digits_only.startswith('55'):
            if len(digits_only) < 12 or len(digits_only) > 13:  # 55 + DDD + número (8 ou 9 dígitos)
                return None
        # Se não começar com código do país, verificar se tem DDD + número
        elif len(digits_only) < 10 or len(digits_only) > 11:  # DDD + número (8 ou 9 dígitos)
            return None
            
        # Normalizar para incluir código do país se não estiver presente
        if not digits_only.startswith('55'):
            digits_only = '55' + digits_only
            
        return digits_only
