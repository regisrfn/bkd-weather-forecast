"""
Output Port: Interface para Cache Repository
Define contrato para implementações de cache (DynamoDB, Redis, etc.)
"""
from typing import Protocol, Optional, Dict, Any


class ICacheRepository(Protocol):
    """Interface para repositório de cache"""
    
    def get(self, city_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados do cache por city_id
        
        Args:
            city_id: ID da cidade
            
        Returns:
            Dados completos da API OpenWeather ou None se não encontrado/expirado
        """
        ...
    
    def set(self, city_id: str, data: Dict[str, Any], ttl_seconds: int = 10800) -> bool:
        """
        Armazena dados no cache com TTL
        
        Args:
            city_id: ID da cidade
            data: Resposta completa da API OpenWeather (JSON)
            ttl_seconds: Tempo de vida em segundos (padrão: 3 horas = 10800s)
            
        Returns:
            True se salvo com sucesso, False caso contrário
        """
        ...
    
    def delete(self, city_id: str) -> bool:
        """
        Remove entrada do cache
        
        Args:
            city_id: ID da cidade
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        ...
    
    def is_enabled(self) -> bool:
        """
        Verifica se o cache está habilitado
        
        Returns:
            True se cache está ativo, False caso contrário
        """
        ...
