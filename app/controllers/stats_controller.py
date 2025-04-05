import logging
from utils.db_adapter import db_adapter

class StatsController:
    """Controlador para gerenciar estatísticas da aplicação"""
    
    @staticmethod
    def get_stats_by_number(user_id, start_date, end_date, link_id=None):
        """Obtém estatísticas agrupadas por número de telefone"""
        try:
            conn = db_adapter.get_db_connection()
            cursor = conn.cursor()
            
            # Condições para a consulta
            conditions = ["cl.user_id = %s"]
            params = [user_id]
            
            if start_date and end_date:
                conditions.append("rl.redirect_time::date BETWEEN %s AND %s")
                params.extend([start_date, end_date])
            
            if link_id:
                conditions.append("cl.id = %s")
                params.append(link_id)
            
            # Consulta para obter estatísticas por número
            query = f"""
                SELECT 
                    wn.id, 
                    wn.phone_number,
                    wn.description,
                    COUNT(rl.id) as access_count,
                    MAX(rl.redirect_time) as last_access,
                    ROUND(100.0 * COUNT(rl.id) / SUM(COUNT(rl.id)) OVER (), 2) as percentage
                FROM whatsapp_numbers wn
                JOIN redirect_logs rl ON wn.id = rl.number_id
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {" AND ".join(conditions)}
                GROUP BY wn.id, wn.phone_number, wn.description
                ORDER BY access_count DESC
            """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Formatar os resultados para serem retornados como JSON
            stats = []
            for row in results:
                stats.append({
                    'id': row['id'],
                    'phone_number': row['phone_number'],
                    'description': row['description'],
                    'access_count': row['access_count'],
                    'last_access': row['last_access'].strftime('%Y-%m-%d %H:%M:%S') if row['last_access'] else None,
                    'percentage': row['percentage']
                })
            
            conn.close()
            return {"number_stats": stats}
            
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas por número: {str(e)}")
            return {"number_stats": []}
    
    @staticmethod
    def get_stats_summary(user_id, start_date, end_date, link_id=None):
        """Obtém um resumo das estatísticas para um intervalo de datas"""
        try:
            conn = db_adapter.get_db_connection()
            cursor = conn.cursor()
            
            # Prepara as condições da consulta SQL
            conditions = ["cl.user_id = %s"]
            params = [user_id]
            
            if start_date and end_date:
                conditions.append("rl.redirect_time::date BETWEEN %s AND %s")
                params.extend([start_date, end_date])
            
            if link_id:
                conditions.append("cl.id = %s")
                params.append(link_id)
            
            # Total de cliques
            query = f"""
                SELECT COUNT(*) as total_clicks
                FROM redirect_logs rl
                JOIN custom_links cl ON rl.link_id = cl.id
                WHERE {' AND '.join(conditions)}
            """
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            total_clicks = result['total_clicks'] if result else 0
            
            # Total de links ativos
            active_links_query = """
                SELECT COUNT(DISTINCT cl.id) as total
                FROM custom_links cl
                WHERE cl.user_id = %s AND cl.is_active = 1
            """
            
            cursor.execute(active_links_query, [user_id])
            active_links_result = cursor.fetchone()
            active_links = active_links_result['total'] if active_links_result else 0
            
            # Total de números ativos
            active_numbers_query = """
                SELECT COUNT(*) as total
                FROM whatsapp_numbers
                WHERE user_id = %s AND is_active = 1
            """
            
            cursor.execute(active_numbers_query, [user_id])
            active_numbers_result = cursor.fetchone()
            active_numbers = active_numbers_result['total'] if active_numbers_result else 0
            
            # Calcular média diária
            daily_avg = 0
            if start_date and end_date:
                # Calcular número de dias entre datas
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                days = (end - start).days + 1  # Incluir ambos os dias
                
                if days > 0 and total_clicks > 0:
                    daily_avg = round(total_clicks / days, 1)
            
            return {
                "total_clicks": total_clicks,
                "active_links": active_links,
                "active_numbers": active_numbers,
                "daily_average": daily_avg,
                "period": {
                    "start": start_date,
                    "end": end_date
                }
            }
                
        except Exception as e:
            logging.error(f"Erro ao obter resumo de estatísticas: {str(e)}")
            return {
                "total_clicks": 0,
                "active_links": 0,
                "active_numbers": 0,
                "daily_average": 0,
                "period": {
                    "start": start_date,
                    "end": end_date
                }
            }
    
    @staticmethod
    def get_stats_map(user_id, start_date, end_date, link_id=None):
        """Obtém dados de mapa de calor para visualização"""
        # Implementação simplificada - em uma versão real, isso poderia usar
        # geolocalização de IPs para criar um mapa de calor
        return {"map_data": []}
    
    @staticmethod
    def get_recent_redirects(user_id, start_date, end_date, link_id=None, limit=100):
        """Obtém os redirecionamentos mais recentes"""
        try:
            with db_adapter.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepara as condições da consulta SQL
                conditions = ["r.timestamp::date BETWEEN %s AND %s", "u.id = %s"]
                params = [start_date, end_date, user_id]
                
                if link_id:
                    conditions.append("l.id = %s")
                    params.append(link_id)
                
                # Constrói e executa a consulta SQL
                query = f"""
                    SELECT 
                        r.id, 
                        l.short_path, 
                        n.number, 
                        r.timestamp,
                        r.ip_address,
                        r.user_agent
                    FROM redirect_logs r
                    JOIN whatsapp_numbers n ON r.number_id = n.id
                    JOIN custom_links l ON r.link_id = l.id
                    JOIN users u ON l.user_id = u.id
                    WHERE {' AND '.join(conditions)}
                    ORDER BY r.timestamp DESC
                    LIMIT %s
                """
                
                params.append(limit)
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Formatar resultados
                redirects = []
                for row in results:
                    redirects.append({
                        "id": row[0],
                        "link": row[1],
                        "number": row[2],
                        "timestamp": row[3].strftime('%Y-%m-%d %H:%M:%S'),
                        "ip_address": row[4],
                        "user_agent": row[5]
                    })
                
                return redirects
                
        except Exception as e:
            logging.error(f"Erro ao obter redirecionamentos recentes: {str(e)}")
            return []
