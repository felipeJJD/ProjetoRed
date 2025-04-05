import random
import logging
from utils.db_adapter import db_adapter
from app.models.whatsapp_number import WhatsAppNumber
from app.models.custom_link import CustomLink
from datetime import datetime


class NumberBalancer:
    """Serviço para balanceamento de carga entre números de WhatsApp"""
    
    @staticmethod
    def select_number(numbers, link_id):
        """Seleciona um número de WhatsApp para redirecionamento de forma balanceada
        
        Args:
            numbers (list): Lista de dicionários com números disponíveis
            link_id (int): ID do link de redirecionamento
            
        Returns:
            dict: Número selecionado
        """
        try:
            # Verificar se há apenas um número disponível
            if len(numbers) == 1:
                return numbers[0]
            
            # Obter contagem de redirecionamentos para cada número (último dia)
            stats_by_number = NumberBalancer._get_number_stats(numbers, link_id)
            
            # Se não temos estatísticas ou ocorreu erro, usar seleção aleatória
            if not stats_by_number:
                logging.info("Sem estatísticas disponíveis, usando seleção aleatória simples.")
                selected_number = random.choice(numbers)
                logging.info(f"Número selecionado aleatoriamente: ID={selected_number['id']}, fone={selected_number['phone_number']}")
                return selected_number
            
            # Se temos estatísticas, fazer seleção baseada nelas
            # Ordenar por contagem total para priorizar números menos usados
            numbers_sorted = sorted(stats_by_number, key=lambda x: x['redirect_count'])
            
            # Verificar se há números com a mesma contagem mínima
            if len(numbers_sorted) > 0:
                min_redirects = numbers_sorted[0]['redirect_count']
                min_numbers = [n for n in numbers_sorted if n['redirect_count'] == min_redirects]
                
                # Se há múltiplos números com a mesma contagem, escolher aleatoriamente entre eles
                if len(min_numbers) > 1:
                    selected_number = random.choice(min_numbers)
                    logging.info(f"Múltiplos números com contagem mínima {min_redirects}, escolhido aleatoriamente: ID={selected_number['id']}")
                else:
                    selected_number = min_numbers[0]
                    logging.info(f"Número com menor contagem ({min_redirects}) selecionado: ID={selected_number['id']}")
            else:
                # Fallback para seleção aleatória se algo deu errado na ordenação
                selected_number = random.choice(numbers)
                logging.info(f"Fallback para seleção aleatória: ID={selected_number['id']}")
                
            # Registrar o número selecionado para diagnóstico
            logging.info(f"Número selecionado para redirecionamento: ID={selected_number['id']}, fone={selected_number['phone_number']}")
            
            return selected_number
            
        except Exception as e:
            logging.error(f"Erro na seleção balanceada de números: {str(e)}")
            # Sempre retornar um número válido, mesmo em caso de erro
            return random.choice(numbers)
    
    @staticmethod
    def _get_number_stats(numbers, link_id):
        """Obtém estatísticas de uso para cada número
        
        Args:
            numbers (list): Lista de dicionários com números disponíveis
            link_id (int): ID do link de redirecionamento
            
        Returns:
            list: Lista de dicionários com números e suas estatísticas
        """
        conn = None
        try:
            conn = db_adapter.get_db_connection()
            number_stats = []
            
            if db_adapter.use_postgres:
                # Consulta única com subquery para obter todas as estatísticas de uma vez
                query = '''
                    WITH link_stats AS (
                        SELECT 
                            number_id, 
                            COUNT(*) FILTER (WHERE link_id = %s) AS link_specific_count,
                            COUNT(*) AS total_count
                        FROM redirect_logs 
                        WHERE redirect_time >= CURRENT_TIMESTAMP - INTERVAL '1 day'
                        GROUP BY number_id
                    )
                    SELECT 
                        n.id, n.phone_number, n.description, 
                        COALESCE(s.total_count, 0) AS redirect_count,
                        COALESCE(s.link_specific_count, 0) AS link_specific_count
                    FROM whatsapp_numbers n
                    LEFT JOIN link_stats s ON n.id = s.number_id
                    WHERE n.id IN (%s)
                '''
                
                # Construir placeholders para a lista de IDs de números
                id_list = ','.join(['%s'] * len(numbers))
                query = query.replace('%s)', f'{id_list})')
                
                # Preparar parâmetros: link_id seguido pelos IDs dos números
                params = [link_id] + [n['id'] for n in numbers]
                
                # Executar a consulta
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Processar resultados
                for row in results:
                    number_stats.append({
                        'id': row['id'],
                        'phone_number': row['phone_number'],
                        'description': row['description'],
                        'redirect_count': row['redirect_count'],
                        'link_specific_count': row['link_specific_count']
                    })
            else:
                # Abordagem individual para SQLite
                cursor = conn.cursor()
                for num in numbers:
                    # Calcular a quantidade de redirecionamentos nas últimas 24 horas
                    cursor.execute('''
                        SELECT COUNT(*) as count 
                        FROM redirect_logs 
                        WHERE number_id = ? 
                        AND timestamp >= datetime('now', '-1 day')
                    ''', (num['id'],))
                    redirect_count = cursor.fetchone()['count']
                    
                    # Se temos o ID do link, verificar redirecionamentos específicos do link
                    link_specific_count = 0
                    if link_id:
                        cursor.execute('''
                            SELECT COUNT(*) as count 
                            FROM redirect_logs 
                            WHERE number_id = ? AND link_id = ? 
                            AND timestamp >= datetime('now', '-1 day')
                        ''', (num['id'], link_id))
                        link_specific_count = cursor.fetchone()['count']
                    
                    # Adicionar número com suas estatísticas para o processo de seleção
                    number_stats.append({
                        'id': num['id'],
                        'phone_number': num['phone_number'],
                        'description': num.get('description', ''),
                        'redirect_count': redirect_count,
                        'link_specific_count': link_specific_count
                    })
            
            return number_stats
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas de números: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
