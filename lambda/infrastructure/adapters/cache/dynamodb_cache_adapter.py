"""
Output Adapter: Implementação do Cache Repository usando DynamoDB
Armazena respostas completas da API OpenWeather com TTL de 3 horas
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from functools import lru_cache
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from ddtrace import tracer

from application.ports.output.cache_repository_port import ICacheRepository


logger = logging.getLogger(__name__)


def convert_floats_to_decimal(obj):
    """
    Converte recursivamente floats para Decimal para DynamoDB
    DynamoDB não aceita float, apenas Decimal
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


def convert_decimal_to_float(obj):
    """
    Converte recursivamente Decimal para float ao ler do DynamoDB
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj


class DynamoDBCacheAdapter(ICacheRepository):
    """
    Implementação de cache usando DynamoDB
    
    Estrutura do item:
    {
        "cityId": "3531803",
        "data": { ... resposta completa da API ... },
        "ttl": 1700593200,  # Unix timestamp
        "createdAt": "2025-11-21T10:00:00Z"
    }
    """
    
    def __init__(
        self, 
        table_name: Optional[str] = None,
        enabled: Optional[bool] = None,
        ttl_seconds: int = 10800,  # 3 horas
        region_name: Optional[str] = None
    ):
        """
        Inicializa o adapter de cache DynamoDB
        
        Args:
            table_name: Nome da tabela DynamoDB (padrão: env CACHE_TABLE_NAME)
            enabled: Se cache está habilitado (padrão: env CACHE_ENABLED)
            ttl_seconds: TTL padrão em segundos (padrão: 3 horas)
            region_name: Região AWS (padrão: env AWS_REGION ou sa-east-1)
        """
        self.table_name = table_name or os.environ.get('CACHE_TABLE_NAME', 'weather-forecast-cache')
        self.default_ttl = ttl_seconds
        self.region_name = region_name or os.environ.get('AWS_REGION', 'sa-east-1')
        
        # Verificar se cache está habilitado
        if enabled is None:
            enabled_env = os.environ.get('CACHE_ENABLED', 'true').lower()
            self.enabled = enabled_env in ('true', '1', 'yes')
        else:
            self.enabled = enabled
        
        # Inicializar cliente DynamoDB
        self.dynamodb = None
        self.table = None
        
        if self.enabled:
            try:
                self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
                self.table = self.dynamodb.Table(self.table_name)
                logger.info(f"Cache DynamoDB inicializado: {self.table_name}")
            except Exception as e:
                logger.error(f"Erro ao inicializar DynamoDB: {e}")
                self.enabled = False
    
    def is_enabled(self) -> bool:
        """Verifica se cache está habilitado e operacional"""
        return self.enabled and self.table is not None
    
    @tracer.wrap(service="weather-forecast", resource="cache.get")
    def get(self, city_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados do cache
        
        Args:
            city_id: ID da cidade
            
        Returns:
            Dados da API ou None se não encontrado/expirado
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self.table.get_item(Key={'cityId': city_id})
            
            if 'Item' not in response:
                logger.debug(f"Cache MISS: cidade {city_id}")
                return None
            
            item = response['Item']
            
            # Verificar se TTL ainda é válido (DynamoDB pode demorar para excluir)
            ttl = item.get('ttl')
            if ttl and ttl < int(datetime.now(timezone.utc).timestamp()):
                logger.debug(f"Cache EXPIRED: cidade {city_id}")
                return None
            
            logger.info(f"Cache HIT: cidade {city_id}")
            # Converter Decimal de volta para float
            data = item.get('data')
            return convert_decimal_to_float(data) if data else None
            
        except ClientError as e:
            logger.error(f"Erro DynamoDB ao buscar cache: {e.response['Error']['Code']} - {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar cache: {e}")
            return None
    
    @tracer.wrap(service="weather-forecast", resource="cache.set")
    def set(self, city_id: str, data: Dict[str, Any], ttl_seconds: int = None) -> bool:
        """
        Armazena dados no cache
        
        Args:
            city_id: ID da cidade
            data: Resposta completa da API OpenWeather
            ttl_seconds: TTL customizado (opcional, usa padrão se None)
            
        Returns:
            True se salvo com sucesso
        """
        if not self.is_enabled():
            return False
        
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
        
        try:
            now = datetime.now(timezone.utc)
            ttl_timestamp = int(now.timestamp()) + ttl_seconds
            
            # Converter floats para Decimal antes de salvar no DynamoDB
            data_decimal = convert_floats_to_decimal(data)
            
            item = {
                'cityId': city_id,
                'data': data_decimal,
                'ttl': ttl_timestamp,
                'createdAt': now.isoformat()
            }
            
            self.table.put_item(Item=item)
            logger.info(f"Cache SET: cidade {city_id}, TTL {ttl_seconds}s")
            return True
            
        except ClientError as e:
            logger.error(f"Erro DynamoDB ao salvar cache: {e.response['Error']['Code']} - {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar cache: {e}")
            return False
    
    def delete(self, city_id: str) -> bool:
        """
        Remove entrada do cache
        
        Args:
            city_id: ID da cidade
            
        Returns:
            True se removido com sucesso
        """
        if not self.is_enabled():
            return False
        
        try:
            self.table.delete_item(Key={'cityId': city_id})
            logger.info(f"Cache DELETE: cidade {city_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Erro DynamoDB ao deletar cache: {e.response['Error']['Code']} - {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao deletar cache: {e}")
            return False


# Factory singleton com LRU cache para reutilizar instância no Lambda container
@lru_cache(maxsize=1)
def get_cache_repository(
    table_name: Optional[str] = None,
    enabled: Optional[bool] = None
) -> ICacheRepository:
    """
    Factory para criar cache repository (singleton com LRU)
    Reutiliza instância durante warm starts do Lambda
    
    Args:
        table_name: Nome da tabela (opcional, usa env)
        enabled: Habilitar cache (opcional, usa env)
        
    Returns:
        Instância do cache repository
    """
    return DynamoDBCacheAdapter(table_name=table_name, enabled=enabled)
