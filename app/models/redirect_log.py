from utils.db_adapter import db_adapter
from datetime import datetime
import logging


class RedirectLog:
    """Modelo que representa um log de redirecionamento no sistema"""
    
    def __init__(self, id=None, link_id=None, number_id=None, timestamp=None,
                 ip_address=None, user_agent=None, message=None, city=None,
                 region=None, country=None, latitude=None, longitude=None):
        self.id = id
        self.link_id = link_id
        self.number_id = number_id
        self.timestamp = timestamp or datetime.now()
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.message = message
        self.city = city
        self.region = region
        self.country = country
        self.latitude = latitude
        self.longitude = longitude
    
    @staticmethod
    def get_by_id(log_id):
        """Busca um log pelo ID"""
        result = db_adapter.execute_query(
            'SELECT * FROM redirect_logs WHERE id = %s', 
            (log_id,)
        )
        return RedirectLog._from_db_result(result) if result else None
    
    @staticmethod
    def get_by_link(link_id, limit=100):
        """Busca logs por link_id"""
        results = db_adapter.execute_query(
            'SELECT * FROM redirect_logs WHERE link_id = %s ORDER BY timestamp DESC LIMIT %s', 
            (link_id, limit),
            fetch_all=True
        )
        return [RedirectLog._from_db_result(result) for result in results] if results else []
    
    @staticmethod
    def get_by_number(number_id, limit=100):
        """Busca logs por number_id"""
        results = db_adapter.execute_query(
            'SELECT * FROM redirect_logs WHERE number_id = %s ORDER BY timestamp DESC LIMIT %s', 
            (number_id, limit),
            fetch_all=True
        )
        return [RedirectLog._from_db_result(result) for result in results] if results else []
    
    @staticmethod
    def get_recent_by_user(user_id, limit=10):
        """Busca logs recentes de um usuário através dos links"""
        query = '''
            SELECT rl.* 
            FROM redirect_logs rl
            JOIN custom_links cl ON rl.link_id = cl.id
            WHERE cl.user_id = %s
            ORDER BY rl.timestamp DESC
            LIMIT %s
        '''
        results = db_adapter.execute_query(query, (user_id, limit), fetch_all=True)
        return [RedirectLog._from_db_result(result) for result in results] if results else []
    
    def save(self):
        """Salva um log no banco de dados (cria ou atualiza)"""
        if self.id:
            # Atualizar log existente
            query = '''UPDATE redirect_logs SET 
                link_id = %s, 
                number_id = %s, 
                ip_address = %s, 
                user_agent = %s,
                message = %s,
                city = %s,
                region = %s,
                country = %s,
                latitude = %s,
                longitude = %s
            WHERE id = %s'''
            
            params = (
                self.link_id, self.number_id, 
                self.ip_address, self.user_agent, self.message,
                self.city, self.region, self.country,
                self.latitude, self.longitude,
                self.id
            )
            
            try:
                db_adapter.execute_query(query, params, commit=True)
                return self.id
            except Exception as e:
                logging.error(f"Erro ao atualizar log: {str(e)}")
                raise
        else:
            # Criar novo log
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                
                if db_adapter.use_postgres:
                    query = '''INSERT INTO redirect_logs 
                        (link_id, number_id, timestamp, ip_address, user_agent,
                         message, city, region, country, latitude, longitude)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id'''
                    
                    params = (
                        self.link_id, self.number_id, 
                        self.ip_address, self.user_agent, self.message,
                        self.city, self.region, self.country,
                        self.latitude, self.longitude
                    )
                else:
                    query = '''INSERT INTO redirect_logs 
                        (link_id, number_id, timestamp, ip_address, user_agent,
                         message, city, region, country, latitude, longitude)
                    VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)'''
                    
                    params = (
                        self.link_id, self.number_id, 
                        self.ip_address, self.user_agent, self.message,
                        self.city, self.region, self.country,
                        self.latitude, self.longitude
                    )
                
                if db_adapter.use_postgres:
                    cursor.execute(query, params)
                    self.id = cursor.fetchone()['id']
                else:
                    cursor.execute(query, params)
                    self.id = cursor.lastrowid
                
                conn.commit()
                return self.id
            except Exception as e:
                conn.rollback()
                logging.error(f"Erro ao criar log: {str(e)}")
                raise
            finally:
                conn.close()
    
    @staticmethod
    def get_statistics_by_link(link_id, days=30):
        """Retorna estatísticas de redirecionamento por link"""
        if db_adapter.use_postgres:
            query = '''
                SELECT 
                    COUNT(*) as total_redirects,
                    COUNT(DISTINCT number_id) as unique_numbers,
                    COUNT(DISTINCT date(timestamp)) as unique_days,
                    MAX(timestamp) as last_redirect
                FROM redirect_logs
                WHERE link_id = %s
                AND timestamp >= CURRENT_DATE - INTERVAL '%s days'
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
                AND timestamp >= date('now', '-%s days')
            '''
        
        result = db_adapter.execute_query(query, (link_id, days))
        return result if result else {'total_redirects': 0, 'unique_numbers': 0, 'unique_days': 0, 'last_redirect': None}
    
    @staticmethod
    def _from_db_result(db_result):
        """Cria uma instância de RedirectLog a partir de um resultado do banco de dados"""
        if not db_result:
            return None
            
        return RedirectLog(
            id=db_result['id'],
            link_id=db_result['link_id'],
            number_id=db_result['number_id'],
            timestamp=db_result.get('timestamp', None),
            ip_address=db_result.get('ip_address', None),
            user_agent=db_result.get('user_agent', None),
            message=db_result.get('message', None),
            city=db_result.get('city', None),
            region=db_result.get('region', None),
            country=db_result.get('country', None),
            latitude=db_result.get('latitude', None),
            longitude=db_result.get('longitude', None)
        )
