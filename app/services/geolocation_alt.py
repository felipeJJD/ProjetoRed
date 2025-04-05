import requests
import logging

class GeoLocationService:
    """
    Serviço de geolocalização alternativo que não depende do pacote ipapi
    """
    
    @staticmethod
    def get_location_data(ip_address):
        """
        Obtém dados de localização para um endereço IP usando o serviço ipinfo.io
        
        Args:
            ip_address (str): O endereço IP para obter dados de localização
            
        Returns:
            dict: Dados de localização ou None se falhar
        """
        if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
            return {
                'city': 'Local',
                'region': 'Local',
                'country': 'Local',
                'latitude': 0,
                'longitude': 0
            }
            
        try:
            # Usando ipinfo.io como alternativa (não requer pacote adicional)
            response = requests.get(f'https://ipinfo.io/{ip_address}/json')
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair coordenadas se disponíveis
                lat, lon = 0, 0
                if 'loc' in data and data['loc']:
                    try:
                        lat, lon = map(float, data['loc'].split(','))
                    except (ValueError, TypeError):
                        pass
                
                return {
                    'city': data.get('city', 'Desconhecido'),
                    'region': data.get('region', 'Desconhecido'),
                    'country': data.get('country', 'Desconhecido'),
                    'latitude': lat,
                    'longitude': lon
                }
                
            return {
                'city': 'Desconhecido',
                'region': 'Desconhecido',
                'country': 'Desconhecido',
                'latitude': 0,
                'longitude': 0
            }
            
        except Exception as e:
            logging.error(f"Erro ao obter dados de geolocalização: {str(e)}")
            return {
                'city': 'Erro',
                'region': 'Erro',
                'country': 'Erro',
                'latitude': 0,
                'longitude': 0
            } 