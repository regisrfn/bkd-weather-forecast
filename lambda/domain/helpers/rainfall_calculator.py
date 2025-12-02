"""
Rainfall Intensity Calculator - Cálculo de intensidade de chuva composta
Helper utilitário para cálculo de intensidade (volume × probabilidade)
"""
from domain.alerts.primitives import RAIN_INTENSITY_REFERENCE


def calculate_rainfall_intensity(rain_probability: float, rain_volume: float) -> float:
    """
    Calcula intensidade de chuva composta (0-100)
    
    Fórmula: (volume_mm/h × probabilidade%) / referência × 100
    
    A intensidade composta considera tanto o volume quanto a probabilidade,
    fornecendo uma métrica mais realista do impacto da chuva.
    
    Exemplos:
        - 10mm/h com 50% prob = ~16.7 intensidade (chuva leve incerta)
        - 10mm/h com 100% prob = ~33.3 intensidade (chuva moderada certa)
        - 30mm/h com 100% prob = 100 intensidade (chuva muito forte)
    
    Args:
        rain_probability: Probabilidade de chuva (0-100%)
        rain_volume: Volume de chuva em mm/h
    
    Returns:
        Intensidade composta 0-100 (0 = sem chuva, 100 = chuva muito intensa)
    """
    if rain_volume == 0:
        return 0.0
    
    composite = (rain_volume * (rain_probability / 100.0)) / RAIN_INTENSITY_REFERENCE * 100.0
    return min(100.0, composite)
