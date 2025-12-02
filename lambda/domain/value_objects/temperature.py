"""
Value Object para temperatura
Encapsula conversões e validações de temperatura
"""
from dataclasses import dataclass
from enum import Enum


class TemperatureScale(Enum):
    """Escalas de temperatura suportadas"""
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


@dataclass(frozen=True)
class Temperature:
    """
    Value Object para temperatura
    
    Características:
    - Imutável (frozen=True)
    - Conversões automáticas entre escalas
    - Métodos de domínio (is_freezing, is_hot)
    - Type-safe
    """
    celsius: float
    
    def __post_init__(self):
        """Valida temperatura no momento da criação"""
        # Validação: não pode ser abaixo do zero absoluto
        if self.celsius < -273.15:
            raise ValueError(
                f"Temperatura impossível: {self.celsius}°C. "
                f"Abaixo do zero absoluto (-273.15°C)."
            )
    
    @property
    def fahrenheit(self) -> float:
        """
        Converte para Fahrenheit
        
        Returns:
            Temperatura em °F
        """
        return (self.celsius * 9/5) + 32
    
    @property
    def kelvin(self) -> float:
        """
        Converte para Kelvin
        
        Returns:
            Temperatura em K
        """
        return self.celsius + 273.15
    
    def is_freezing(self) -> bool:
        """
        Verifica se está congelando (≤ 0°C)
        
        Returns:
            True se temperatura ≤ 0°C
        """
        return self.celsius <= 0
    
    def is_cold(self) -> bool:
        """
        Verifica se está frio (< 12°C)
        
        Returns:
            True se temperatura < 12°C
        """
        return self.celsius < 12
    
    def is_hot(self) -> bool:
        """
        Verifica se está quente (> 30°C)
        
        Returns:
            True se temperatura > 30°C
        """
        return self.celsius > 30
    
    def is_very_cold(self) -> bool:
        """
        Verifica se está muito frio (< 8°C)
        
        Returns:
            True se temperatura < 8°C
        """
        return self.celsius < 8
    
    def is_very_hot(self) -> bool:
        """
        Verifica se está muito quente (> 35°C)
        
        Returns:
            True se temperatura > 35°C
        """
        return self.celsius > 35
    
    def format(self, scale: TemperatureScale = TemperatureScale.CELSIUS) -> str:
        """
        Formata temperatura na escala especificada
        
        Args:
            scale: Escala desejada
        
        Returns:
            String formatada (ex: "25.5°C")
        """
        if scale == TemperatureScale.CELSIUS:
            return f"{self.celsius:.1f}{scale.value}"
        elif scale == TemperatureScale.FAHRENHEIT:
            return f"{self.fahrenheit:.1f}{scale.value}"
        elif scale == TemperatureScale.KELVIN:
            return f"{self.kelvin:.1f}{scale.value}"
        return f"{self.celsius:.1f}°C"
    
    def __str__(self) -> str:
        """String representation padrão em Celsius"""
        return self.format(TemperatureScale.CELSIUS)
    
    def __float__(self) -> float:
        """Permite conversão para float (retorna Celsius)"""
        return self.celsius
    
    @classmethod
    def from_fahrenheit(cls, fahrenheit: float) -> 'Temperature':
        """
        Factory method para criar a partir de Fahrenheit
        
        Args:
            fahrenheit: Temperatura em °F
        
        Returns:
            Instância de Temperature
        """
        celsius = (fahrenheit - 32) * 5/9
        return cls(celsius=celsius)
    
    @classmethod
    def from_kelvin(cls, kelvin: float) -> 'Temperature':
        """
        Factory method para criar a partir de Kelvin
        
        Args:
            kelvin: Temperatura em K
        
        Returns:
            Instância de Temperature
        """
        celsius = kelvin - 273.15
        return cls(celsius=celsius)
