"""
Primitivos de alertas (tipos e thresholds) compartilhados pelo domínio.
Separados para evitar ciclos entre serviços e entidades.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List

# Threshold de probabilidade para alertas de precipitação sem volume
RAIN_PROBABILITY_THRESHOLD = 80  # Mínimo de 80% para gerar alertas de chuva

# Threshold de referência para intensidade de chuva (métrica composta)
RAIN_INTENSITY_REFERENCE = 30.0  # mm/h


class AlertSeverity(Enum):
    """Níveis de severidade de alertas climáticos"""
    INFO = "info"      # Informativo
    WARNING = "warning"  # Atenção
    ALERT = "alert"    # Alerta
    DANGER = "danger"  # Perigo


@dataclass
class WeatherAlert:
    """Alerta climático estruturado"""
    code: str  # Código do alerta (ex: "STORM", "HEAVY_RAIN", "STRONG_WIND")
    severity: AlertSeverity  # Nível de severidade
    description: str  # Descrição em português
    timestamp: datetime  # Data/hora do alerta (quando se aplica)
    details: Optional[dict] = None  # Detalhes adicionais opcionais (ex: velocidade vento, mm chuva)
    
    def to_dict(self) -> dict:
        """Converte para dicionário para resposta da API"""
        result = {
            'code': self.code,
            'severity': self.severity.value,
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }
        if self.details is not None:
            result['details'] = self.details
        return result
