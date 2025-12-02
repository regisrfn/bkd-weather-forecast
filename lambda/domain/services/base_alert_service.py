"""
Classe base abstrata para serviços de alerta
Reduz duplicação de código e padroniza interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

from domain.alerts.primitives import WeatherAlert, AlertSeverity


class BaseAlertService(ABC):
    """
    Classe base para todos os serviços de alerta
    
    Define interface comum e fornece métodos utilitários compartilhados.
    Cada serviço concreto implementa apenas a lógica específica de geração.
    """
    
    @abstractmethod
    def generate_alerts(self, data: Any) -> List[WeatherAlert]:
        """
        Método abstrato para gerar alertas
        
        Args:
            data: Input específico de cada serviço (dataclass)
        
        Returns:
            Lista de WeatherAlert gerados
        """
        pass
    
    @staticmethod
    def create_alert(
        code: str,
        severity: AlertSeverity,
        description: str,
        timestamp: datetime,
        details: Dict[str, Any]
    ) -> WeatherAlert:
        """
        Factory method para criar alertas de forma padronizada
        
        Args:
            code: Código único do alerta (ex: "HEAVY_RAIN")
            severity: Severidade do alerta
            description: Descrição amigável
            timestamp: Timestamp do forecast
            details: Detalhes adicionais (dict)
        
        Returns:
            WeatherAlert configurado
        """
        return WeatherAlert(
            code=code,
            severity=severity,
            description=description,
            timestamp=timestamp,
            details=details
        )
    
    @staticmethod
    def round_details(details: Dict[str, Any], precision: int = 1) -> Dict[str, Any]:
        """
        Arredonda valores numéricos em details
        
        Args:
            details: Dicionário de detalhes
            precision: Casas decimais
        
        Returns:
            Dict com valores arredondados
        """
        rounded = {}
        for key, value in details.items():
            if isinstance(value, float):
                rounded[key] = round(value, precision)
            else:
                rounded[key] = value
        return rounded
