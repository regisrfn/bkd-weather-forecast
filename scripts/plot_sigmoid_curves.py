"""
Script de visualização de curvas sigmoide
Compara diferentes valores de k e midpoint
"""
import sys
import os
import math
import matplotlib.pyplot as plt
import numpy as np

# Adiciona o diretório lambda ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from domain.alerts.primitives import (
    RAIN_INTENSITY_REFERENCE,
    RAIN_PROBABILITY_REFERENCE,
    RAIN_PROBABILITY_SIGMOID_K
)


def calculate_sigmoid_weight(probability, k, midpoint):
    """Calcula peso da sigmoide com parâmetros customizados"""
    sigmoid = 1.0 / (1.0 + math.exp(-k * (probability - midpoint)))
    max_sigmoid = 1.0 / (1.0 + math.exp(-k * (100.0 - midpoint)))
    return sigmoid / max_sigmoid


def calculate_intensity(probability, volume, k, midpoint):
    """Calcula intensidade com parâmetros customizados"""
    if volume == 0:
        return 0.0
    weight = calculate_sigmoid_weight(probability, k, midpoint)
    return min(100.0, (volume / RAIN_INTENSITY_REFERENCE) * weight * 100.0)


def plot_sigmoid_curves():
    """Plota curvas sigmoide com diferentes valores de k"""
    
    probabilities = np.linspace(0, 100, 200)
    k_values = [0.05, 0.1, 0.2, 0.3, 0.5]
    midpoint = RAIN_PROBABILITY_REFERENCE
    
    plt.figure(figsize=(14, 10))
    
    # 1. Comparação de diferentes k values
    plt.subplot(2, 3, 1)
    for k in k_values:
        weights = [calculate_sigmoid_weight(p, k, midpoint) for p in probabilities]
        plt.plot(probabilities, weights, label=f'k={k}', linewidth=2)
    
    plt.axvline(x=midpoint, color='gray', linestyle='--', alpha=0.5, label=f'Midpoint={midpoint}%')
    plt.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Peso Sigmoide', fontsize=11)
    plt.title('1. Comparação de Inclinação (k)', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. Diferentes midpoints
    plt.subplot(2, 3, 2)
    midpoints = [50, 60, 70, 80]
    k = RAIN_PROBABILITY_SIGMOID_K
    
    for mid in midpoints:
        weights = [calculate_sigmoid_weight(p, k, mid) for p in probabilities]
        plt.plot(probabilities, weights, label=f'Midpoint={mid}%', linewidth=2)
    
    plt.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Peso Sigmoide', fontsize=11)
    plt.title(f'2. Comparação de Midpoint (k={k})', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 3. Intensidade com 10mm/h para diferentes k
    plt.subplot(2, 3, 3)
    volume = 10
    
    for k in k_values:
        intensities = [calculate_intensity(p, volume, k, midpoint) for p in probabilities]
        plt.plot(probabilities, intensities, label=f'k={k}', linewidth=2)
    
    plt.axvline(x=midpoint, color='gray', linestyle='--', alpha=0.5)
    plt.axhline(y=20, color='red', linestyle=':', alpha=0.5, label='Threshold Alerta')
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Intensidade', fontsize=11)
    plt.title(f'3. Intensidade com {volume}mm/h (diferentes k)', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 4. Intensidade com 30mm/h para diferentes k
    plt.subplot(2, 3, 4)
    volume = 30
    
    for k in k_values:
        intensities = [calculate_intensity(p, volume, k, midpoint) for p in probabilities]
        plt.plot(probabilities, intensities, label=f'k={k}', linewidth=2)
    
    plt.axvline(x=midpoint, color='gray', linestyle='--', alpha=0.5)
    plt.axhline(y=60, color='red', linestyle=':', alpha=0.5, label='Threshold Danger')
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Intensidade', fontsize=11)
    plt.title(f'4. Intensidade com {volume}mm/h (diferentes k)', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 5. Heatmap de intensidade (k atual)
    plt.subplot(2, 3, 5)
    volumes = np.linspace(5, 50, 100)
    probs = np.linspace(0, 100, 100)
    k = RAIN_PROBABILITY_SIGMOID_K
    
    intensity_matrix = np.zeros((len(volumes), len(probs)))
    for i, vol in enumerate(volumes):
        for j, prob in enumerate(probs):
            intensity_matrix[i, j] = calculate_intensity(prob, vol, k, midpoint)
    
    im = plt.contourf(probs, volumes, intensity_matrix, levels=20, cmap='YlOrRd')
    plt.colorbar(im, label='Intensidade')
    plt.axvline(x=midpoint, color='blue', linestyle='--', linewidth=2, alpha=0.7)
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Volume (mm/h)', fontsize=11)
    plt.title(f'5. Mapa de Calor (k={k}, mid={midpoint}%)', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # 6. Comparação linear vs sigmoide
    plt.subplot(2, 3, 6)
    k = RAIN_PROBABILITY_SIGMOID_K
    volume = 20
    
    # Sigmoide atual
    intensities_sigmoid = [calculate_intensity(p, volume, k, midpoint) for p in probabilities]
    plt.plot(probabilities, intensities_sigmoid, label='Sigmoide (atual)', linewidth=2, color='blue')
    
    # Linear (sem sigmoide)
    intensities_linear = [(volume / RAIN_INTENSITY_REFERENCE) * (p / 100.0) * 100.0 for p in probabilities]
    intensities_linear = [min(100.0, i) for i in intensities_linear]
    plt.plot(probabilities, intensities_linear, label='Linear (sem sigmoide)', linewidth=2, color='red', linestyle='--')
    
    plt.axvline(x=midpoint, color='gray', linestyle='--', alpha=0.5)
    plt.xlabel('Probabilidade (%)', fontsize=11)
    plt.ylabel('Intensidade', fontsize=11)
    plt.title(f'6. Sigmoide vs Linear ({volume}mm/h)', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/sigmoid_comparison.png', dpi=150, bbox_inches='tight')
    print("\n✓ Gráfico salvo em: output/sigmoid_comparison.png")
    plt.show()


def plot_intensity_3d():
    """Plota gráfico 3D de intensidade"""
    from mpl_toolkits.mplot3d import Axes3D
    
    fig = plt.figure(figsize=(16, 6))
    
    k_values = [0.1, 0.2, 0.5]
    midpoint = RAIN_PROBABILITY_REFERENCE
    
    for idx, k in enumerate(k_values, 1):
        ax = fig.add_subplot(1, 3, idx, projection='3d')
        
        volumes = np.linspace(5, 50, 50)
        probs = np.linspace(0, 100, 50)
        V, P = np.meshgrid(volumes, probs)
        
        I = np.zeros_like(V)
        for i in range(len(probs)):
            for j in range(len(volumes)):
                I[i, j] = calculate_intensity(P[i, j], V[i, j], k, midpoint)
        
        surf = ax.plot_surface(P, V, I, cmap='YlOrRd', alpha=0.8, edgecolor='none')
        
        ax.set_xlabel('Probabilidade (%)', fontsize=10)
        ax.set_ylabel('Volume (mm/h)', fontsize=10)
        ax.set_zlabel('Intensidade', fontsize=10)
        ax.set_title(f'k={k}, midpoint={midpoint}%', fontsize=11, fontweight='bold')
        
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
    
    plt.tight_layout()
    plt.savefig('output/sigmoid_3d_comparison.png', dpi=150, bbox_inches='tight')
    print("✓ Gráfico 3D salvo em: output/sigmoid_3d_comparison.png")
    plt.show()


def print_comparison_table():
    """Imprime tabela comparativa de diferentes k values"""
    print("\n" + "="*100)
    print("TABELA COMPARATIVA: PROBABILIDADE MÍNIMA PARA ATINGIR THRESHOLD (Intensidade ≥ 40)")
    print("="*100)
    
    k_values = [0.05, 0.1, 0.2, 0.3, 0.5]
    volumes = [10, 15, 20, 30]
    threshold = 40
    midpoint = RAIN_PROBABILITY_REFERENCE
    
    # Header
    header = f"{'Volume':<12}"
    for k in k_values:
        header += f"k={k:<7}"
    print(header)
    print("-"*100)
    
    for volume in volumes:
        row = f"{volume} mm/h{'':<4}"
        for k in k_values:
            min_prob = None
            for prob in range(0, 101):
                if calculate_intensity(prob, volume, k, midpoint) >= threshold:
                    min_prob = prob
                    break
            
            if min_prob is not None:
                row += f"{min_prob}%{'':<8}"
            else:
                row += f"N/A{'':<8}"
        print(row)
    
    print("\n" + "="*100)
    print("ANÁLISE:")
    print("  - k menor (0.05): Curva suave, transição gradual")
    print("  - k maior (0.5): Curva abrupta, transição rápida")
    print(f"  - Midpoint: {midpoint}% (ponto onde peso = 0.5)")
    print("="*100 + "\n")


if __name__ == "__main__":
    print("\n" + "="*100)
    print("ANÁLISE DE CURVAS SIGMOIDE PARA INTENSIDADE DE CHUVA")
    print("="*100)
    print(f"\nConfiguração atual:")
    print(f"  - RAIN_INTENSITY_REFERENCE = {RAIN_INTENSITY_REFERENCE} mm/h")
    print(f"  - RAIN_PROBABILITY_REFERENCE = {RAIN_PROBABILITY_REFERENCE}%")
    print(f"  - RAIN_PROBABILITY_SIGMOID_K = {RAIN_PROBABILITY_SIGMOID_K}")
    print("="*100)
    
    print_comparison_table()
    
    print("\nGerando gráficos...")
    plot_sigmoid_curves()
    plot_intensity_3d()
    
    print("\n✓ Análise completa!")
