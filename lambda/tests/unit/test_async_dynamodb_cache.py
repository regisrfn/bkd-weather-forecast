"""Testes unitários para AsyncDynamoDBCache"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.adapters.output.cache.async_dynamodb_cache import (
    AsyncDynamoDBCache,
    DecimalEncoder,
    get_async_cache
)


class TestDecimalEncoder:
    """Testes para DecimalEncoder"""
    
    def test_encode_decimal(self):
        """Testa conversão de Decimal para float"""
        data = {
            'temperature': Decimal('25.5'),
            'pressure': Decimal('1013')
        }
        result = json.dumps(data, cls=DecimalEncoder)
        assert '25.5' in result
        assert '1013' in result
    
    def test_encode_other_types(self):
        """Testa que outros tipos não são afetados"""
        data = {'text': 'hello', 'number': 42}
        result = json.dumps(data, cls=DecimalEncoder)
        assert 'hello' in result
        assert '42' in result


class TestAsyncDynamoDBCache:
    """Testes para AsyncDynamoDBCache"""
    
    @pytest.fixture
    def mock_client_manager(self):
        """Mock do gerenciador de cliente"""
        manager = MagicMock()
        mock_client = AsyncMock()
        manager.get_client = AsyncMock(return_value=mock_client)
        manager.cleanup = AsyncMock()
        return manager
    
    @pytest.fixture
    def cache_with_mocked_manager(self, mock_client_manager):
        """Cache com gerenciador mockado"""
        with patch('infrastructure.adapters.output.cache.async_dynamodb_cache.get_dynamodb_client_manager', return_value=mock_client_manager):
            cache = AsyncDynamoDBCache(
                table_name='test-table',
                enabled=True,
                ttl_seconds=3600
            )
            return cache
    
    @pytest.mark.asyncio
    async def test_get_cache_disabled(self, cache_with_mocked_manager):
        """Testa get quando cache está desabilitado"""
        cache_with_mocked_manager.enabled = False
        result = await cache_with_mocked_manager.get('123')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_with_mocked_manager, mock_client_manager):
        """Testa get quando item não existe"""
        mock_client = await mock_client_manager.get_client()
        mock_client.get_item.return_value = {}
        
        result = await cache_with_mocked_manager.get('123')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_with_mocked_manager, mock_client_manager):
        """Testa get quando item existe e não expirou"""
        future_ttl = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        data = {'temperature': 25.5, 'city': 'São Paulo'}
        
        mock_client = await mock_client_manager.get_client()
        mock_client.get_item.return_value = {
            'Item': {
                'cityId': {'S': '123'},
                'data': {'S': json.dumps(data)},
                'ttl': {'N': str(future_ttl)},
                'createdAt': {'S': datetime.now(timezone.utc).isoformat()}
            }
        }
        
        result = await cache_with_mocked_manager.get('123')
        assert result is not None
        assert result['temperature'] == 25.5
        assert result['city'] == 'São Paulo'
    
    @pytest.mark.asyncio
    async def test_get_expired_item(self, cache_with_mocked_manager, mock_client_manager):
        """Testa get quando item expirou"""
        expired_ttl = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        
        mock_client = await mock_client_manager.get_client()
        mock_client.get_item.return_value = {
            'Item': {
                'cityId': {'S': '123'},
                'data': {'S': '{"temperature": 25.5}'},
                'ttl': {'N': str(expired_ttl)}
            }
        }
        
        result = await cache_with_mocked_manager.get('123')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_with_exception(self, cache_with_mocked_manager, mock_client_manager):
        """Testa get quando ocorre exceção (silently fail)"""
        mock_client = await mock_client_manager.get_client()
        mock_client.get_item.side_effect = Exception("DynamoDB error")
        
        result = await cache_with_mocked_manager.get('123')
        assert result is None  # Falha silenciosa
    
    @pytest.mark.asyncio
    async def test_set_cache_disabled(self, cache_with_mocked_manager):
        """Testa set quando cache está desabilitado"""
        cache_with_mocked_manager.enabled = False
        result = await cache_with_mocked_manager.set('123', {'temp': 25})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_set_success(self, cache_with_mocked_manager, mock_client_manager):
        """Testa set com sucesso"""
        mock_client = await mock_client_manager.get_client()
        mock_client.put_item.return_value = {}
        
        data = {'temperature': 25.5, 'city': 'Rio'}
        result = await cache_with_mocked_manager.set('123', data)
        
        assert result is True
        mock_client.put_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache_with_mocked_manager, mock_client_manager):
        """Testa set com TTL customizado"""
        mock_client = await mock_client_manager.get_client()
        mock_client.put_item.return_value = {}
        
        result = await cache_with_mocked_manager.set('123', {'temp': 25}, ttl_seconds=7200)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_with_exception(self, cache_with_mocked_manager, mock_client_manager):
        """Testa set quando ocorre exceção"""
        mock_client = await mock_client_manager.get_client()
        mock_client.put_item.side_effect = Exception("DynamoDB error")
        
        result = await cache_with_mocked_manager.set('123', {'temp': 25})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_cache_disabled(self, cache_with_mocked_manager):
        """Testa delete quando cache está desabilitado"""
        cache_with_mocked_manager.enabled = False
        result = await cache_with_mocked_manager.delete('123')
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_success(self, cache_with_mocked_manager, mock_client_manager):
        """Testa delete com sucesso"""
        mock_client = await mock_client_manager.get_client()
        mock_client.delete_item.return_value = {}
        
        result = await cache_with_mocked_manager.delete('123')
        assert result is True
        mock_client.delete_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_with_exception(self, cache_with_mocked_manager, mock_client_manager):
        """Testa delete quando ocorre exceção"""
        mock_client = await mock_client_manager.get_client()
        mock_client.delete_item.side_effect = Exception("DynamoDB error")
        
        result = await cache_with_mocked_manager.delete('123')
        assert result is False
    
    @pytest.mark.asyncio
    async def test_batch_get_cache_disabled(self, cache_with_mocked_manager):
        """Testa batch_get quando cache está desabilitado"""
        cache_with_mocked_manager.enabled = False
        result = await cache_with_mocked_manager.batch_get(['123', '456'])
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_batch_get_empty_list(self, cache_with_mocked_manager):
        """Testa batch_get com lista vazia"""
        result = await cache_with_mocked_manager.batch_get([])
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_batch_get_success(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_get com sucesso"""
        future_ttl = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_get_item.return_value = {
            'Responses': {
                'test-table': [
                    {
                        'cityId': {'S': '123'},
                        'data': {'S': '{"temp": 25}'},
                        'ttl': {'N': str(future_ttl)}
                    },
                    {
                        'cityId': {'S': '456'},
                        'data': {'S': '{"temp": 30}'},
                        'ttl': {'N': str(future_ttl)}
                    }
                ]
            }
        }
        
        result = await cache_with_mocked_manager.batch_get(['123', '456'])
        assert len(result) == 2
        assert result['123']['temp'] == 25
        assert result['456']['temp'] == 30
    
    @pytest.mark.asyncio
    async def test_batch_get_with_expired_items(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_get com itens expirados (devem ser ignorados)"""
        expired_ttl = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        future_ttl = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_get_item.return_value = {
            'Responses': {
                'test-table': [
                    {
                        'cityId': {'S': '123'},
                        'data': {'S': '{"temp": 25}'},
                        'ttl': {'N': str(expired_ttl)}  # Expirado
                    },
                    {
                        'cityId': {'S': '456'},
                        'data': {'S': '{"temp": 30}'},
                        'ttl': {'N': str(future_ttl)}  # Válido
                    }
                ]
            }
        }
        
        result = await cache_with_mocked_manager.batch_get(['123', '456'])
        assert len(result) == 1
        assert '123' not in result
        assert result['456']['temp'] == 30
    
    @pytest.mark.asyncio
    async def test_batch_get_with_exception(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_get quando ocorre exceção"""
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_get_item.side_effect = Exception("DynamoDB error")
        
        result = await cache_with_mocked_manager.batch_get(['123', '456'])
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_batch_set_cache_disabled(self, cache_with_mocked_manager):
        """Testa batch_set quando cache está desabilitado"""
        cache_with_mocked_manager.enabled = False
        items = {'123': {'temp': 25}, '456': {'temp': 30}}
        result = await cache_with_mocked_manager.batch_set(items)
        
        assert result == {'123': False, '456': False}
    
    @pytest.mark.asyncio
    async def test_batch_set_empty_items(self, cache_with_mocked_manager):
        """Testa batch_set com dict vazio"""
        result = await cache_with_mocked_manager.batch_set({})
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_batch_set_success(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_set com sucesso"""
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_write_item.return_value = {}
        
        items = {'123': {'temp': 25}, '456': {'temp': 30}}
        result = await cache_with_mocked_manager.batch_set(items)
        
        assert result == {'123': True, '456': True}
        mock_client.batch_write_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_set_with_unprocessed_items(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_set com itens não processados"""
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_write_item.return_value = {
            'UnprocessedItems': {
                'test-table': [
                    {
                        'PutRequest': {
                            'Item': {'cityId': {'S': '456'}}
                        }
                    }
                ]
            }
        }
        
        items = {'123': {'temp': 25}, '456': {'temp': 30}}
        result = await cache_with_mocked_manager.batch_set(items)
        
        assert result['123'] is True  # Processado
        assert result['456'] is False  # Não processado
    
    @pytest.mark.asyncio
    async def test_batch_set_with_exception(self, cache_with_mocked_manager, mock_client_manager):
        """Testa batch_set quando ocorre exceção"""
        mock_client = await mock_client_manager.get_client()
        mock_client.batch_write_item.side_effect = Exception("DynamoDB error")
        
        items = {'123': {'temp': 25}, '456': {'temp': 30}}
        result = await cache_with_mocked_manager.batch_set(items)
        
        assert result == {'123': False, '456': False}
    
    @pytest.mark.asyncio
    async def test_cleanup(self, cache_with_mocked_manager, mock_client_manager):
        """Testa cleanup"""
        await cache_with_mocked_manager.cleanup()
        mock_client_manager.cleanup.assert_called_once()
    
    def test_is_enabled(self, cache_with_mocked_manager):
        """Testa verificação de cache habilitado"""
        assert cache_with_mocked_manager.is_enabled() is True
        
        cache_with_mocked_manager.enabled = False
        assert cache_with_mocked_manager.is_enabled() is False
    
    def test_constructor_with_env_vars(self, monkeypatch):
        """Testa construtor com variáveis de ambiente"""
        monkeypatch.setenv('CACHE_TABLE_NAME', 'custom-table')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('CACHE_ENABLED', 'false')
        
        with patch('infrastructure.adapters.output.cache.async_dynamodb_cache.get_dynamodb_client_manager'):
            cache = AsyncDynamoDBCache()
            assert cache.table_name == 'custom-table'
            assert cache.region_name == 'us-east-1'
            assert cache.enabled is False


class TestGetAsyncCache:
    """Testes para factory singleton"""
    
    def test_get_async_cache_singleton(self):
        """Testa que get_async_cache retorna singleton"""
        with patch('infrastructure.adapters.output.cache.async_dynamodb_cache.get_dynamodb_client_manager'):
            # Resetar singleton
            import infrastructure.adapters.output.cache.async_dynamodb_cache as module
            module._async_cache_instance = None
            
            cache1 = get_async_cache(table_name='test-table')
            cache2 = get_async_cache(table_name='different-table')  # Deve retornar mesma instância
            
            assert cache1 is cache2
            assert cache1.table_name == 'test-table'  # Primeiro valor é mantido
