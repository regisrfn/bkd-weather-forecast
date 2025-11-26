"""
DynamoDB Client Manager - Singleton para gerenciar cliente aioboto3
Reutiliza cliente entre invocações Lambda (warm starts)
"""
import asyncio
from typing import Optional
import aioboto3
from botocore.config import Config
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class DynamoDBClientManager:
    """
    Gerenciador singleton de cliente DynamoDB com aioboto3
    
    Benefícios:
    - Reutiliza cliente entre invocações Lambda (warm starts)
    - Detecta mudanças de event loop (asyncio.run cria novos loops)
    - Recria cliente automaticamente quando necessário
    - Gerencia lifecycle completo do cliente
    - Thread-safe para Lambda (single-threaded por invocação)
    
    Uso:
        manager = DynamoDBClientManager.get_instance()
        client = await manager.get_client()
        response = await client.get_item(...)
    """
    
    _instance: Optional['DynamoDBClientManager'] = None
    _lock = asyncio.Lock()  # Lock para garantir inicialização thread-safe
    
    def __init__(
        self,
        region_name: str = 'sa-east-1',
        max_pool_connections: int = 100,
        connect_timeout: int = 3,
        read_timeout: int = 3
    ):
        """
        Inicializa gerenciador de cliente DynamoDB
        
        Args:
            region_name: Região AWS
            max_pool_connections: Tamanho do pool de conexões
            connect_timeout: Timeout de conexão (segundos)
            read_timeout: Timeout de leitura (segundos)
        """
        self.region_name = region_name
        
        # aioboto3 Session (thread-safe, reutilizável)
        self.session = aioboto3.Session()
        
        # Config otimizado para client pooling
        self.boto_config = Config(
            region_name=self.region_name,
            max_pool_connections=max_pool_connections,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries={'max_attempts': 2, 'mode': 'adaptive'}
        )
        
        # Client state
        self._client = None
        self._client_loop_id = None
        self._client_context_manager = None
        
        logger.info(
            "DynamoDBClientManager initialized",
            region=self.region_name,
            max_pool_connections=max_pool_connections
        )
    
    @classmethod
    def get_instance(
        cls,
        region_name: str = 'sa-east-1',
        max_pool_connections: int = 100,
        connect_timeout: int = 3,
        read_timeout: int = 3
    ) -> 'DynamoDBClientManager':
        """
        Retorna instância singleton do gerenciador
        
        Args:
            region_name: Região AWS (usado apenas na primeira criação)
            max_pool_connections: Tamanho do pool (usado apenas na primeira criação)
            connect_timeout: Timeout de conexão (usado apenas na primeira criação)
            read_timeout: Timeout de leitura (usado apenas na primeira criação)
        
        Returns:
            Instância singleton do DynamoDBClientManager
        """
        if cls._instance is None:
            cls._instance = cls(
                region_name=region_name,
                max_pool_connections=max_pool_connections,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout
            )
            logger.info("DynamoDBClientManager singleton created")
        
        return cls._instance
    
    async def get_client(self):
        """
        Retorna cliente DynamoDB (cria ou reutiliza)
        
        Estratégia OTIMIZADA para Lambda:
        - Cliente persiste DENTRO do mesmo event loop
        - Recria quando event loop muda (asyncio.run fecha o loop anterior)
        - TRUE REUSE: Cliente reutilizado em múltiplas chamadas no MESMO loop
        
        Returns:
            Cliente DynamoDB async
        """
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            logger.error("No running event loop found")
            raise
        
        # Se cliente existe E está no mesmo event loop, REUTILIZAR
        if self._client is not None and self._client_loop_id == current_loop_id:
            logger.info(
                "♻️  REUSING existing DynamoDB client",
                loop_id=current_loop_id,
                reused=True
            )
            return self._client
        
        # Loop mudou ou cliente não existe - precisa recriar
        if self._client is not None:
            logger.info(
                "Event loop changed - recreating client",
                old_loop_id=self._client_loop_id,
                new_loop_id=current_loop_id
            )
            await self._close_client()
        
        # Criar novo cliente para o event loop atual
        try:
            logger.info(
                "🔨 Creating NEW DynamoDB client",
                loop_id=current_loop_id,
                region=self.region_name,
                reused=False
            )
            
            self._client_context_manager = self.session.client(
                'dynamodb',
                region_name=self.region_name,
                config=self.boto_config
            )
            
            # Enter context manager
            self._client = await self._client_context_manager.__aenter__()
            self._client_loop_id = current_loop_id
            
            logger.info(
                "✅ DynamoDB client CREATED and CACHED for reuse",
                loop_id=current_loop_id,
                region=self.region_name
            )
        
        except Exception as e:
            logger.error(
                "Failed to create DynamoDB client",
                error=str(e)
            )
            self._client = None
            self._client_loop_id = None
            self._client_context_manager = None
            raise
        
        return self._client
    
    async def _close_client(self) -> None:
        """
        Fecha cliente DynamoDB existente (cleanup)
        """
        if self._client is not None:
            try:
                # Exit context manager properly
                if self._client_context_manager is not None:
                    await self._client_context_manager.__aexit__(None, None, None)
                
                logger.info(
                    "DynamoDB client closed",
                    loop_id=self._client_loop_id
                )
            
            except Exception as e:
                logger.warning(
                    "Error closing DynamoDB client",
                    error=str(e),
                    loop_id=self._client_loop_id
                )
            
            finally:
                self._client = None
                self._client_loop_id = None
                self._client_context_manager = None
    
    async def cleanup(self) -> None:
        """
        Cleanup completo - fecha cliente e libera recursos
        Deve ser chamado ao final de cada invocação Lambda (opcional)
        """
        await self._close_client()
        logger.info("DynamoDBClientManager cleanup completed")
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (útil para testes)
        """
        if cls._instance is not None:
            # Não podemos fazer cleanup assíncrono aqui
            # Cleanup deve ser feito antes de reset
            cls._instance = None
            logger.info("DynamoDBClientManager instance reset")


# Factory function para facilitar uso
def get_dynamodb_client_manager(
    region_name: str = 'sa-east-1',
    max_pool_connections: int = 100,
    connect_timeout: int = 3,
    read_timeout: int = 3
) -> DynamoDBClientManager:
    """
    Factory function para obter instância singleton do gerenciador
    
    Args:
        region_name: Região AWS
        max_pool_connections: Tamanho do pool de conexões
        connect_timeout: Timeout de conexão (segundos)
        read_timeout: Timeout de leitura (segundos)
    
    Returns:
        Instância singleton do DynamoDBClientManager
    """
    return DynamoDBClientManager.get_instance(
        region_name=region_name,
        max_pool_connections=max_pool_connections,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout
    )
