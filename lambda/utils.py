"""
Funções utilitárias
"""
import math
from typing import Dict, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância entre dois pontos geográficos usando a fórmula de Haversine
    
    Args:
        lat1, lon1: Latitude e longitude do ponto 1
        lat2, lon2: Latitude e longitude do ponto 2
    
    Returns:
        float: Distância em quilômetros
    """
    # Raio da Terra em km
    R = 6371.0
    
    # Converter graus para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return round(distance, 1)


def create_response(status_code: int, body: Dict[Any, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Cria resposta padronizada para Lambda
    
    Args:
        status_code: Código HTTP de status
        body: Corpo da resposta (será convertido para JSON)
        headers: Headers customizados (opcional)
    
    Returns:
        dict: Resposta formatada para API Gateway
    """
    import json
    
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, ensure_ascii=False)
    }


def parse_query_params(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai e valida parâmetros de query da requisição
    
    Args:
        event: Evento da Lambda
    
    Returns:
        dict: Parâmetros extraídos
    """
    params = event.get('queryStringParameters') or {}
    return params


def parse_path_params(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai parâmetros de path da requisição
    
    Args:
        event: Evento da Lambda
    
    Returns:
        dict: Parâmetros extraídos
    """
    params = event.get('pathParameters') or {}
    return params


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai e parseia o body da requisição
    
    Args:
        event: Evento da Lambda
    
    Returns:
        dict: Body parseado
    """
    import json
    
    body = event.get('body')
    if not body:
        return {}
    
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    
    return body
