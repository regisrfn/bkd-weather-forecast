"""
Configuração centralizada de logging para a aplicação
Configura o logger AWS Lambda Powertools com service name do Datadog
"""
import os
from aws_lambda_powertools import Logger


def get_logger(service_name: str = None, child: bool = False) -> Logger:
    """
    Retorna uma instância configurada do Logger
    
    Args:
        service_name: Nome do serviço (se None, usa DD_SERVICE do ambiente)
        child: Se True, cria um child logger
    
    Returns:
        Logger configurado
    """
    if service_name is None:
        service_name = os.environ.get('DD_SERVICE', 'weather-forecast')
    
    if child:
        return Logger(service=service_name, child=True)
    
    return Logger(service=service_name)


# Logger principal da aplicação
logger = get_logger()
