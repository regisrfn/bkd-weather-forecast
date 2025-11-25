"""
Output Adapter: Implementação do Cache Repository usando DynamoDB
Armazena respostas completas da API OpenWeather com TTL de 3 horas
Otimizado com serialização JSON nativa (sem TypeSerializer)
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from functools import lru_cache
from decimal import Decimal
from threading import RLock
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from ddtrace import tracer

from application.ports.output.cache_repository_port import ICacheRepository


logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Encoder JSON customizado para converter Decimal em float"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def python_to_dynamodb(obj):
    """
    Converte tipos Python para DynamoDB-safe (floats -> Decimal)
    Usado apenas para garantir compatibilidade com DynamoDB
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: python_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [python_to_dynamodb(item) for item in obj]
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
        self._memory_cache: Dict[str, tuple[Any, int]] = {}
        self._cache_lock = RLock()
        
        # Verificar se cache está habilitado
        if enabled is None:
            enabled_env = os.environ.get('CACHE_ENABLED', 'true').lower()
            self.enabled = enabled_env in ('true', '1', 'yes')
        else:
            self.enabled = enabled
        
        # Inicializar cliente DynamoDB com connection pooling otimizado
        self.dynamodb_client = None
        
        if self.enabled:
            try:
                # Config com connection pooling otimizado e timeouts adequados
                config = Config(
                    max_pool_connections=500,
                    connect_timeout=2,      # 2s para estabelecer conexão
                    read_timeout=3,         # 3s para leitura (DynamoDB p99 < 1s)
                    retries={
                        'max_attempts': 2,  # Apenas 1 retry
                        'mode': 'adaptive'  # Adapta baseado em throttling
                    }
                )
                self.dynamodb_client = boto3.client(
                    'dynamodb',
                    region_name=self.region_name,
                    config=config
                )
                logger.info(f"Cache DynamoDB inicializado (client): {self.table_name}")
            except Exception as e:
                logger.error(f"Erro ao inicializar DynamoDB: {e}")
                self.enabled = False
    
    def is_enabled(self) -> bool:
        """Verifica se cache está habilitado e operacional"""
        return self.enabled and self.dynamodb_client is not None
    
    @tracer.wrap(resource="cache.get")
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
        
        now_ts = int(datetime.now(timezone.utc).timestamp())

        # Hot cache em memória para evitar round-trips ao Dynamo em warm starts
        with self._cache_lock:
            cached_entry = self._memory_cache.get(city_id)
            if cached_entry:
                cached_data, cached_ttl = cached_entry
                if cached_ttl > now_ts:
                    logger.debug(f"Cache HIT (memory): cidade {city_id}")
                    return cached_data
                # Expirou: remover para não acumular
                self._memory_cache.pop(city_id, None)
        
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key={'cityId': {'S': city_id}},
                ConsistentRead=False  # Leitura eventual é suficiente e mais barata/rápida
            )
            
            if 'Item' not in response:
                logger.debug(f"Cache MISS: cidade {city_id}")
                return None
            
            # Deserializar usando JSON nativo (mais rápido que TypeDeserializer)
            item = response['Item']
            
            # Verificar TTL (DynamoDB pode demorar para excluir itens expirados)
            ttl = int(item['ttl']['N']) if 'ttl' in item else None
            if ttl and ttl < now_ts:
                logger.debug(f"Cache EXPIRED: cidade {city_id}")
                return None
            
            logger.info(f"Cache HIT: cidade {city_id}")
            # Parse JSON string diretamente (bem mais rápido)
            data_json = item.get('data', {}).get('S')
            if data_json:
                cached_data = json.loads(data_json)
                with self._cache_lock:
                    self._memory_cache[city_id] = (
                        cached_data,
                        ttl or now_ts + self.default_ttl
                    )
                return cached_data
            return None
            
        except ClientError as e:
            logger.error(f"Erro DynamoDB ao buscar cache: {e.response['Error']['Code']} - {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar cache: {e}")
            return None
    
    @tracer.wrap(resource="cache.set")
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
            
            # Serializar data como JSON string (muito mais rápido que TypeSerializer)
            data_json = json.dumps(data, cls=DecimalEncoder, separators=(',', ':'))
            
            # Item com serialização JSON nativa
            item = {
                'cityId': {'S': city_id},
                'data': {'S': data_json},
                'ttl': {'N': str(ttl_timestamp)},
                'createdAt': {'S': now.isoformat()}
            }
            
            self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=item
            )
            logger.info(f"Cache SET: cidade {city_id}, TTL {ttl_seconds}s")
            # Atualiza hot cache para evitar round-trip nas próximas invocações do mesmo container
            with self._cache_lock:
                self._memory_cache[city_id] = (data, ttl_timestamp)
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
            with self._cache_lock:
                self._memory_cache.pop(city_id, None)
            
            self.dynamodb_client.delete_item(
                TableName=self.table_name,
                Key={'cityId': {'S': city_id}}
            )
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
