"""
Rainfall Intensity Calculator - Cálculo de intensidade de chuva composta
Helper utilitário para cálculo de intensidade (volume × probabilidade)
"""
import math
from domain.alerts.primitives import (
    RAIN_INTENSITY_REFERENCE,
    RAIN_PROBABILITY_REFERENCE,
    RAIN_PROBABILITY_SIGMOID_K
)


def _calculate_probability_weight(rain_probability: float) -> float:
    """
    Calcula o peso da probabilidade usando função sigmoide.
    
    A função sigmoide cria uma curva S que:
    - Mantém peso baixo para probabilidades < RAIN_PROBABILITY_REFERENCE
    - Cresce rapidamente acima de RAIN_PROBABILITY_REFERENCE
    - Maximiza o impacto de altas probabilidades (>85%)
    
    Fórmula: 1 / (1 + e^(-k * (prob - reference)))
    
    Args:
        rain_probability: Probabilidade de chuva (0-100%)
    
    Returns:
        Peso normalizado (0-1) com comportamento sigmoide
    """
    # Sigmoide centrada na probabilidade de referência
    sigmoid = 1.0 / (1.0 + math.exp(-RAIN_PROBABILITY_SIGMOID_K * (rain_probability - RAIN_PROBABILITY_REFERENCE)))
    
    # Normaliza para que 100% de probabilidade = 1.0
    max_sigmoid = 1.0 / (1.0 + math.exp(-RAIN_PROBABILITY_SIGMOID_K * (100.0 - RAIN_PROBABILITY_REFERENCE)))
    
    return sigmoid / max_sigmoid


def calculate_rainfall_intensity(rain_probability: float, rain_volume: float) -> float:
    """
    Calcula intensidade de chuva composta (0-100)
    
    Fórmula: (volume_mm/h / ref_volume) × peso_sigmoide(probabilidade) × 100
    
    A intensidade composta considera tanto o volume quanto a probabilidade,
    com peso não-linear para probabilidade (sigmoide) que dá mais importância
    a altas certezas de chuva.
    
    Exemplos com sigmoide (k=0.2, midpoint=70):
        - 10mm/h com 30% prob = ~0.7 intensidade (peso muito baixo)
        - 10mm/h com 50% prob = ~2.4 intensidade (peso baixo)
        - 10mm/h com 70% prob = ~16.7 intensidade (peso médio - ponto de inflexão)
        - 10mm/h com 85% prob = ~29.3 intensidade (peso alto - crescimento rápido)
        - 30mm/h com 100% prob = 100 intensidade (peso máximo)
    
    Args:
        rain_probability: Probabilidade de chuva (0-100%)
        rain_volume: Volume de chuva em mm/h
    
    Returns:
        Intensidade composta 0-100 (0 = sem chuva, 100 = chuva muito intensa)
    """
    if rain_volume == 0:
        return 0.0
    
    # Aplica peso sigmoide na probabilidade
    prob_weight = _calculate_probability_weight(rain_probability)
    
    # Calcula intensidade: (volume normalizado) × (peso da probabilidade) × 100
    composite = (rain_volume / RAIN_INTENSITY_REFERENCE) * prob_weight * 100.0
    
    return min(100.0, composite)
