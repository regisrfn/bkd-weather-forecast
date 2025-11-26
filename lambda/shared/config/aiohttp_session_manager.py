"""
Aiohttp Session Manager - Singleton para gerenciar sessão HTTP global
Reutiliza sessão entre invocações Lambda (warm starts)
"""
import asyncio
from typing import Optional
import aiohttp
from aws_lambda_powertools import Logger

logger = Logger(child=True)


class AiohttpSessionManager:
    """
    Gerenciador singleton de sessão aiohttp
    
    Benefícios:
    - Reutiliza sessão entre invocações Lambda (warm starts)
    - Detecta mudanças de event loop (asyncio.run cria novos loops)
    - Recria sessão automaticamente quando necessário
    - Pool de conexões eficiente
    - Thread-safe para Lambda (single-threaded por invocação)
    
    Uso:
        manager = AiohttpSessionManager.get_instance()
        session = await manager.get_session()
        async with session.get(url) as response:
            data = await response.json()
    """
    
    _instance: Optional['AiohttpSessionManager'] = None
    
    def __init__(
        self,
        total_timeout: int = 15,
        connect_timeout: int = 5,
        sock_read_timeout: int = 10,
        limit: int = 100,
        limit_per_host: int = 30,
        ttl_dns_cache: int = 300
    ):
        """
        Inicializa gerenciador de sessão aiohttp
        
        Args:
            total_timeout: Timeout total em segundos
            connect_timeout: Timeout de conexão em segundos
            sock_read_timeout: Timeout de leitura em segundos
            limit: Limite total de conexões no pool
            limit_per_host: Limite de conexões por host
            ttl_dns_cache: TTL do cache DNS em segundos
        """
        self.total_timeout = total_timeout
        self.connect_timeout = connect_timeout
        self.sock_read_timeout = sock_read_timeout
        self.limit = limit
        self.limit_per_host = limit_per_host
        self.ttl_dns_cache = ttl_dns_cache
        
        # Session state
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_loop_id: Optional[int] = None
        
        logger.info(
            "AiohttpSessionManager initialized",
            total_timeout=total_timeout,
            limit=limit,
            limit_per_host=limit_per_host
        )
    
    @classmethod
    def get_instance(
        cls,
        total_timeout: int = 15,
        connect_timeout: int = 5,
        sock_read_timeout: int = 10,
        limit: int = 100,
        limit_per_host: int = 30,
        ttl_dns_cache: int = 300
    ) -> 'AiohttpSessionManager':
        """
        Retorna instância singleton do gerenciador
        
        Args:
            total_timeout: Timeout total em segundos (usado apenas na primeira criação)
            connect_timeout: Timeout de conexão (usado apenas na primeira criação)
            sock_read_timeout: Timeout de leitura (usado apenas na primeira criação)
            limit: Limite total de conexões (usado apenas na primeira criação)
            limit_per_host: Limite por host (usado apenas na primeira criação)
            ttl_dns_cache: TTL do cache DNS (usado apenas na primeira criação)
        
        Returns:
            Instância singleton do AiohttpSessionManager
        """
        if cls._instance is None:
            cls._instance = cls(
                total_timeout=total_timeout,
                connect_timeout=connect_timeout,
                sock_read_timeout=sock_read_timeout,
                limit=limit,
                limit_per_host=limit_per_host,
                ttl_dns_cache=ttl_dns_cache
            )
            logger.info("AiohttpSessionManager singleton created")
        
        return cls._instance
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Retorna sessão aiohttp (cria ou reutiliza)
        
        Estratégia OTIMIZADA para Lambda:
        - Sessão persiste DENTRO do mesmo event loop
        - Recria quando event loop muda (asyncio.run fecha o loop anterior)
        - TRUE REUSE: Sessão reutilizada em múltiplas chamadas no MESMO loop
        
        Returns:
            Sessão aiohttp
        """
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            logger.error("No running event loop found")
            raise
        
        # Se sessão existe, não está fechada E está no mesmo event loop, REUTILIZAR
        if (self._session is not None and 
            not self._session.closed and 
            self._session_loop_id == current_loop_id):
            logger.info(
                "♻️  REUSING existing aiohttp session",
                loop_id=current_loop_id,
                reused=True
            )
            return self._session
        
        # Loop mudou, sessão fechada, ou não existe - precisa recriar
        if self._session is not None and not self._session.closed:
            logger.info(
                "Event loop changed - recreating session",
                old_loop_id=self._session_loop_id,
                new_loop_id=current_loop_id
            )
            await self._close_session()
        
        # Criar nova sessão para o event loop atual
        try:
            logger.info(
                "🔨 Creating NEW aiohttp session",
                loop_id=current_loop_id,
                limit=self.limit,
                reused=False
            )
            
            # Timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=self.total_timeout,
                connect=self.connect_timeout,
                sock_read=self.sock_read_timeout
            )
            
            # Connector com pool de conexões
            connector = aiohttp.TCPConnector(
                limit=self.limit,
                limit_per_host=self.limit_per_host,
                ttl_dns_cache=self.ttl_dns_cache
            )
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            self._session_loop_id = current_loop_id
            
            logger.info(
                "✅ Aiohttp session CREATED and CACHED for reuse",
                loop_id=current_loop_id,
                limit=self.limit,
                limit_per_host=self.limit_per_host
            )
        
        except Exception as e:
            logger.error(
                "Failed to create aiohttp session",
                error=str(e)
            )
            self._session = None
            self._session_loop_id = None
            raise
        
        return self._session
    
    async def _close_session(self) -> None:
        """
        Fecha sessão aiohttp existente (cleanup)
        """
        if self._session is not None and not self._session.closed:
            try:
                await self._session.close()
                
                logger.info(
                    "Aiohttp session closed",
                    loop_id=self._session_loop_id
                )
            
            except Exception as e:
                logger.warning(
                    "Error closing aiohttp session",
                    error=str(e),
                    loop_id=self._session_loop_id
                )
            
            finally:
                self._session = None
                self._session_loop_id = None
    
    async def cleanup(self) -> None:
        """
        Cleanup completo - fecha sessão e libera recursos
        Deve ser chamado ao final de cada invocação Lambda (opcional)
        """
        await self._close_session()
        logger.info("AiohttpSessionManager cleanup completed")
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (útil para testes)
        """
        if cls._instance is not None:
            # Não podemos fazer cleanup assíncrono aqui
            # Cleanup deve ser feito antes de reset
            cls._instance = None
            logger.info("AiohttpSessionManager instance reset")


# Factory function para facilitar uso
def get_aiohttp_session_manager(
    total_timeout: int = 15,
    connect_timeout: int = 5,
    sock_read_timeout: int = 10,
    limit: int = 100,
    limit_per_host: int = 30,
    ttl_dns_cache: int = 300
) -> AiohttpSessionManager:
    """
    Factory function para obter instância singleton do gerenciador
    
    Args:
        total_timeout: Timeout total em segundos
        connect_timeout: Timeout de conexão em segundos
        sock_read_timeout: Timeout de leitura em segundos
        limit: Limite total de conexões no pool
        limit_per_host: Limite de conexões por host
        ttl_dns_cache: TTL do cache DNS em segundos
    
    Returns:
        Instância singleton do AiohttpSessionManager
    """
    return AiohttpSessionManager.get_instance(
        total_timeout=total_timeout,
        connect_timeout=connect_timeout,
        sock_read_timeout=sock_read_timeout,
        limit=limit,
        limit_per_host=limit_per_host,
        ttl_dns_cache=ttl_dns_cache
    )
