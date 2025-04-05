import requests
import logging
from urllib.parse import urljoin
import time
import json


class GeoLocationService:
    """Serviço para obter informações de geolocalização a partir de endereços IP"""
    
    BACKUP_URL = "https://ipinfo.io/"
    FREE_GEO_URL = "https://freegeoip.app/json/"
    IP_API_URL = "http://ip-api.com/json/"
    
    # Lista de IPs locais/privados que não precisam de geolocalização
    LOCAL_IPS = ['127.0.0.1', 'localhost', '::1', '0.0.0.0']
    
    # Cache simples para evitar múltiplas consultas para o mesmo IP
    ip_cache = {}
    
    @staticmethod
    def get_location_from_ip(ip_address):
        """
        Obtém informações de geolocalização a partir de um endereço IP
        
        Args:
            ip_address (str): Endereço IP
            
        Returns:
            dict: Informações de localização ou None em caso de erro
        """
        # Verificar se o IP é local ou foi previamente consultado no cache
        if not ip_address or ip_address in GeoLocationService.LOCAL_IPS:
            logging.info(f"IP local detectado: {ip_address}. Pulando geolocalização.")
            # Retornar dados padrão para IPs locais (Brasil)
            return {
                'ip': ip_address,
                'city': 'Local',
                'region': 'Local',
                'country': 'Brasil',
                'lat': -14.235,
                'lon': -51.925
            }
        
        # Verificar no cache
        if ip_address in GeoLocationService.ip_cache:
            logging.info(f"Usando dados em cache para IP {ip_address}")
            return GeoLocationService.ip_cache[ip_address]
        
        # Tentar diferentes provedores de geolocalização até encontrar um que funcione
        location_info = (
            GeoLocationService._try_ipinfo(ip_address) or 
            GeoLocationService._try_ip_api(ip_address) or
            GeoLocationService._try_freegeoip(ip_address)
        )
        
        # Se ainda não tiver obtido informações, retornar dados padrão (Brasil)
        if not location_info:
            logging.warning(f"Não foi possível obter geolocalização para IP {ip_address}. Usando dados padrão.")
            location_info = {
                'ip': ip_address,
                'city': 'Desconhecido',
                'region': 'Desconhecido',
                'country': 'Brasil',
                'lat': -14.235,
                'lon': -51.925
            }
        
        # Armazenar no cache
        GeoLocationService.ip_cache[ip_address] = location_info
        return location_info
    
    @staticmethod
    def _try_ipinfo(ip_address):
        """Tenta obter localização usando ipinfo.io"""
        try:
            url = urljoin(GeoLocationService.BACKUP_URL, f"{ip_address}/json")
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'loc' in data and data['loc']:
                    lat, lon = data['loc'].split(',')
                    
                    location_info = {
                        'ip': ip_address,
                        'city': data.get('city', 'Desconhecido'),
                        'region': data.get('region', 'Desconhecido'),
                        'country': data.get('country', 'BR'),
                        'lat': float(lat),
                        'lon': float(lon)
                    }
                    
                    logging.info(f"Informações obtidas de ipinfo.io para IP {ip_address}")
                    return location_info
                else:
                    logging.warning(f"Dados de localização inválidos de ipinfo.io para IP {ip_address}")
                    return None
            else:
                logging.warning(f"Erro ao obter localização de ipinfo.io. Status: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Erro ao acessar ipinfo.io para IP {ip_address}: {str(e)}")
            return None
    
    @staticmethod
    def _try_freegeoip(ip_address):
        """Tenta obter localização usando freegeoip.app"""
        try:
            url = urljoin(GeoLocationService.FREE_GEO_URL, ip_address)
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
                location_info = {
                    'ip': ip_address,
                    'city': data.get('city', 'Desconhecido'),
                    'region': data.get('region_name', 'Desconhecido'),
                    'country': data.get('country_name', 'Brasil'),
                    'lat': data.get('latitude', -14.235),
                    'lon': data.get('longitude', -51.925)
                }
                
                logging.info(f"Informações obtidas de freegeoip.app para IP {ip_address}")
                return location_info
            else:
                logging.warning(f"Erro ao obter localização de freegeoip.app. Status: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Erro ao acessar freegeoip.app para IP {ip_address}: {str(e)}")
            return None
    
    @staticmethod
    def _try_ip_api(ip_address):
        """Tenta obter localização usando ip-api.com"""
        try:
            url = urljoin(GeoLocationService.IP_API_URL, ip_address)
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    location_info = {
                        'ip': ip_address,
                        'city': data.get('city', 'Desconhecido'),
                        'region': data.get('regionName', 'Desconhecido'),
                        'country': data.get('country', 'Brasil'),
                        'lat': data.get('lat', -14.235),
                        'lon': data.get('lon', -51.925)
                    }
                    
                    logging.info(f"Informações obtidas de ip-api.com para IP {ip_address}")
                    return location_info
                else:
                    logging.warning(f"Erro na API ip-api.com: {data.get('message')}")
                    return None
            else:
                logging.warning(f"Erro ao obter localização de ip-api.com. Status: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Erro ao acessar ip-api.com para IP {ip_address}: {str(e)}")
            return None
    
    @staticmethod
    def update_log_with_location(log_id, ip_address, db_adapter):
        """
        Atualiza um log de redirecionamento com informações de localização
        
        Args:
            log_id (int): ID do log de redirecionamento
            ip_address (str): Endereço IP
            db_adapter: Adaptador de banco de dados
            
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário
        """
        location_info = GeoLocationService.get_location_from_ip(ip_address)
        
        if not location_info:
            return False
            
        try:
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE redirect_logs 
                    SET city = %s, region = %s, country = %s, latitude = %s, longitude = %s
                    WHERE id = %s
                ''', (
                    location_info.get('city'), 
                    location_info.get('region'), 
                    location_info.get('country'), 
                    location_info.get('lat'), 
                    location_info.get('lon'),
                    log_id
                ))
                conn.commit()
                logging.info(f"Log ID {log_id} atualizado com dados de geolocalização")
                return True
            finally:
                conn.close()
        except Exception as e:
            logging.error(f"Erro ao atualizar log com informações de localização: {str(e)}")
            return False
