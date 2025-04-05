import logging
from utils.db_adapter import db_adapter


class AnalyticsService:
    """Serviço para análise e estatísticas do sistema de redirecionamento"""
    
    @staticmethod
    def get_dashboard_stats(user_id):
        """
        Obtém estatísticas de uso para exibição no dashboard do usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            dict: Estatísticas de uso
        """
        stats = {
            'total_links': 0,
            'total_numbers': 0,
            'total_redirects': 0,
            'redirects_today': 0,
            'top_links': [],
            'top_numbers': [],
            'recent_redirects': []
        }
        
        try:
            # Total de links ativos do usuário
            total_links = db_adapter.execute_query(
                'SELECT COUNT(*) as count FROM custom_links WHERE user_id = %s', 
                (user_id,)
            )
            stats['total_links'] = total_links['count'] if total_links else 0
            
            # Total de números ativos do usuário
            total_numbers = db_adapter.execute_query(
                'SELECT COUNT(*) as count FROM whatsapp_numbers WHERE user_id = %s AND is_active = %s', 
                (user_id, True)
            )
            stats['total_numbers'] = total_numbers['count'] if total_numbers else 0
            
            # Total de redirecionamentos (geral)
            if db_adapter.use_postgres:
                # Consulta otimizada para PostgreSQL usando JOINs
                query = '''
                    SELECT COUNT(*) as count 
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    WHERE cl.user_id = %s
                '''
            else:
                # Consulta para SQLite
                query = '''
                    SELECT COUNT(*) as count 
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    WHERE cl.user_id = ?
                '''
            
            total_redirects = db_adapter.execute_query(query, (user_id,))
            stats['total_redirects'] = total_redirects['count'] if total_redirects else 0
            
            # Redirecionamentos de hoje
            if db_adapter.use_postgres:
                query = '''
                    SELECT COUNT(*) as count 
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    WHERE cl.user_id = %s
                    AND DATE(rl.timestamp) = CURRENT_DATE
                '''
            else:
                query = '''
                    SELECT COUNT(*) as count 
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    WHERE cl.user_id = ?
                    AND DATE(rl.timestamp) = DATE('now')
                '''
            
            redirects_today = db_adapter.execute_query(query, (user_id,))
            stats['redirects_today'] = redirects_today['count'] if redirects_today else 0
            
            # Top 5 links mais usados
            if db_adapter.use_postgres:
                query = '''
                    SELECT cl.link_name, cl.id, COUNT(rl.id) as redirect_count
                    FROM custom_links cl
                    LEFT JOIN redirect_logs rl ON cl.id = rl.link_id
                    WHERE cl.user_id = %s
                    GROUP BY cl.id, cl.link_name
                    ORDER BY redirect_count DESC
                    LIMIT 5
                '''
            else:
                query = '''
                    SELECT cl.link_name, cl.id, COUNT(rl.id) as redirect_count
                    FROM custom_links cl
                    LEFT JOIN redirect_logs rl ON cl.id = rl.link_id
                    WHERE cl.user_id = ?
                    GROUP BY cl.id, cl.link_name
                    ORDER BY redirect_count DESC
                    LIMIT 5
                '''
            
            top_links = db_adapter.execute_query(query, (user_id,), fetch_all=True)
            stats['top_links'] = top_links if top_links else []
            
            # Top 5 números mais usados
            if db_adapter.use_postgres:
                query = '''
                    SELECT wn.phone_number, wn.description, COUNT(rl.id) as redirect_count
                    FROM whatsapp_numbers wn
                    LEFT JOIN redirect_logs rl ON wn.id = rl.number_id
                    WHERE wn.user_id = %s
                    GROUP BY wn.id, wn.phone_number, wn.description
                    ORDER BY redirect_count DESC
                    LIMIT 5
                '''
            else:
                query = '''
                    SELECT wn.phone_number, wn.description, COUNT(rl.id) as redirect_count
                    FROM whatsapp_numbers wn
                    LEFT JOIN redirect_logs rl ON wn.id = rl.number_id
                    WHERE wn.user_id = ?
                    GROUP BY wn.id, wn.phone_number, wn.description
                    ORDER BY redirect_count DESC
                    LIMIT 5
                '''
            
            top_numbers = db_adapter.execute_query(query, (user_id,), fetch_all=True)
            stats['top_numbers'] = top_numbers if top_numbers else []
            
            # Redirecionamentos recentes
            if db_adapter.use_postgres:
                query = '''
                    SELECT 
                        rl.timestamp, cl.link_name, wn.phone_number,
                        rl.ip_address, rl.city, rl.country, rl.message
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    JOIN whatsapp_numbers wn ON rl.number_id = wn.id
                    WHERE cl.user_id = %s
                    ORDER BY rl.timestamp DESC
                    LIMIT 10
                '''
            else:
                query = '''
                    SELECT 
                        rl.timestamp, cl.link_name, wn.phone_number,
                        rl.ip_address, rl.city, rl.country, rl.message
                    FROM redirect_logs rl
                    JOIN custom_links cl ON rl.link_id = cl.id
                    JOIN whatsapp_numbers wn ON rl.number_id = wn.id
                    WHERE cl.user_id = ?
                    ORDER BY rl.timestamp DESC
                    LIMIT 10
                '''
            
            recent_redirects = db_adapter.execute_query(query, (user_id,), fetch_all=True)
            stats['recent_redirects'] = recent_redirects if recent_redirects else []
            
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas do dashboard: {str(e)}")
        
        return stats
    
    @staticmethod
    def get_link_click_counts(user_id):
        """
        Obtém a contagem de cliques para todos os links de um usuário
        
        Args:
            user_id (int): ID do usuário
            
        Returns:
            list: Lista de dicionários com informações de contagem de cliques
        """
        try:
            query = '''
                SELECT id, link_name, click_count 
                FROM custom_links 
                WHERE user_id = %s
                ORDER BY click_count DESC
            '''
            
            results = db_adapter.execute_query(query, (user_id,), fetch_all=True)
            return results if results else []
        except Exception as e:
            logging.error(f"Erro ao obter contagem de cliques: {str(e)}")
            return []
    
    @staticmethod
    def get_conversion_rates(user_id, days=30):
        """
        Calcula taxas de conversão para links de um usuário
        
        Args:
            user_id (int): ID do usuário
            days (int, optional): Período de análise em dias. Defaults to 30.
            
        Returns:
            dict: Estatísticas de conversão
        """
        try:
            if db_adapter.use_postgres:
                query = '''
                    WITH link_stats AS (
                        SELECT 
                            cl.id, 
                            cl.link_name,
                            cl.click_count,
                            COUNT(rl.id) as redirect_count
                        FROM custom_links cl
                        LEFT JOIN redirect_logs rl ON cl.id = rl.link_id
                        WHERE cl.user_id = %s
                        AND (rl.timestamp >= CURRENT_DATE - INTERVAL '%s days' OR rl.timestamp IS NULL)
                        GROUP BY cl.id, cl.link_name, cl.click_count
                    )
                    SELECT 
                        id, 
                        link_name,
                        click_count,
                        redirect_count,
                        CASE 
                            WHEN click_count > 0 THEN round((redirect_count::float / click_count::float) * 100, 2)
                            ELSE 0
                        END as conversion_rate
                    FROM link_stats
                    ORDER BY conversion_rate DESC
                '''
            else:
                query = '''
                    WITH link_stats AS (
                        SELECT 
                            cl.id, 
                            cl.link_name,
                            cl.click_count,
                            COUNT(rl.id) as redirect_count
                        FROM custom_links cl
                        LEFT JOIN redirect_logs rl ON cl.id = rl.link_id
                        WHERE cl.user_id = ?
                        AND (rl.timestamp >= date('now', '-%s days') OR rl.timestamp IS NULL)
                        GROUP BY cl.id, cl.link_name, cl.click_count
                    )
                    SELECT 
                        id, 
                        link_name,
                        click_count,
                        redirect_count,
                        CASE 
                            WHEN click_count > 0 THEN round((redirect_count * 100.0 / click_count), 2)
                            ELSE 0
                        END as conversion_rate
                    FROM link_stats
                    ORDER BY conversion_rate DESC
                '''
            
            results = db_adapter.execute_query(query, (user_id, days), fetch_all=True)
            return results if results else []
        except Exception as e:
            logging.error(f"Erro ao calcular taxas de conversão: {str(e)}")
            return []
