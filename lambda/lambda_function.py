"""
Lambda Function Handler - Clean Architecture
Delega para o adapter HTTP
"""
from infrastructure.adapters.input.lambda_handler import lambda_handler

# Exportar lambda_handler para ser usado pela AWS Lambda
__all__ = ['lambda_handler']
