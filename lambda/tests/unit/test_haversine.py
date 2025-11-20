"""
Testes Unitários - Utilidade Haversine
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from shared.utils.haversine import calculate_distance


def test_calculate_distance_ribeiro_preto_sao_carlos():
    """Testa cálculo de distância entre Ribeirão Preto e São Carlos"""
    # Ribeirão Preto: -21.1704, -47.8103
    # São Carlos: -22.0074, -47.8911
    distance = calculate_distance(-21.1704, -47.8103, -22.0074, -47.8911)
    
    # Distância esperada: ~95 km
    assert 90 <= distance <= 100, f"Esperado ~95km, obtido {distance}km"


def test_calculate_distance_zero():
    """Testa distância da mesma coordenada (deve ser 0)"""
    distance = calculate_distance(-21.1704, -47.8103, -21.1704, -47.8103)
    assert distance == 0.0


def test_calculate_distance_positive():
    """Testa que distância é sempre positiva"""
    distance = calculate_distance(-21.1704, -47.8103, -22.0074, -47.8911)
    assert distance > 0


def test_calculate_distance_symmetric():
    """Testa que distância é simétrica (A->B = B->A)"""
    dist1 = calculate_distance(-21.1704, -47.8103, -22.0074, -47.8911)
    dist2 = calculate_distance(-22.0074, -47.8911, -21.1704, -47.8103)
    assert dist1 == dist2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
