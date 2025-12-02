"""
Script para buscar dados reais das APIs de clima
Usado para criar fixtures para testes
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# Adicionar path do lambda ao sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.adapters.output.providers.openweather.openweather_provider import OpenWeatherProvider
from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import OpenMeteoProvider
from domain.constants import API


async def fetch_real_data():
    """Busca dados reais para Ribeirão Preto"""
    
    # Coordenadas de Ribeirão Preto
    RIBEIRAO_PRETO = {
        "city_id": "3451682",
        "name": "Ribeirão Preto",
        "state": "SP",
        "latitude": -21.1704,
        "longitude": -47.8103
    }
    
    print("🌍 Buscando dados reais das APIs...")
    print(f"📍 Cidade: {RIBEIRAO_PRETO['name']}, {RIBEIRAO_PRETO['state']}")
    print(f"📍 Coordenadas: {RIBEIRAO_PRETO['latitude']}, {RIBEIRAO_PRETO['longitude']}")
    print()
    
    fixtures = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "city": RIBEIRAO_PRETO,
            "note": "Dados reais capturados das APIs para testes"
        }
    }
    
    # 1. OpenWeather - Current Weather
    print("🔵 OpenWeather - Current Weather...")
    try:
        openweather = OpenWeatherProvider()
        weather = await openweather.get_current_weather(
            latitude=RIBEIRAO_PRETO['latitude'],
            longitude=RIBEIRAO_PRETO['longitude'],
            city_id=RIBEIRAO_PRETO['city_id'],
            city_name=RIBEIRAO_PRETO['name']
        )
        
        fixtures["openweather_current"] = {
            "response": weather.to_api_response(),
            "timestamp": weather.timestamp.isoformat(),
            "notes": "Current weather com forecast de 5 dias (3h intervals)"
        }
        print(f"   ✅ Sucesso: {weather.temperature}°C, {weather.description}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        fixtures["openweather_current"] = {"error": str(e)}
    
    print()
    
    # 2. Open-Meteo - Daily Forecast
    print("🟢 Open-Meteo - Daily Forecast...")
    try:
        openmeteo = OpenMeteoProvider()
        daily_forecasts = await openmeteo.get_daily_forecast(
            latitude=RIBEIRAO_PRETO['latitude'],
            longitude=RIBEIRAO_PRETO['longitude'],
            city_id=RIBEIRAO_PRETO['city_id']
        )
        
        fixtures["openmeteo_daily"] = {
            "count": len(daily_forecasts),
            "forecasts": [f.to_api_response() for f in daily_forecasts],
            "notes": f"Daily forecast para {len(daily_forecasts)} dias"
        }
        print(f"   ✅ Sucesso: {len(daily_forecasts)} dias de previsão")
        if daily_forecasts:
            first = daily_forecasts[0]
            print(f"   📅 Primeiro dia: {first.date}, {first.temp_max}°C max, {first.temp_min}°C min")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        fixtures["openmeteo_daily"] = {"error": str(e)}
    
    print()
    
    # 3. Open-Meteo - Hourly Forecast
    print("🟢 Open-Meteo - Hourly Forecast...")
    try:
        openmeteo = OpenMeteoProvider()
        hourly_forecasts = await openmeteo.get_hourly_forecast(
            latitude=RIBEIRAO_PRETO['latitude'],
            longitude=RIBEIRAO_PRETO['longitude'],
            city_id=RIBEIRAO_PRETO['city_id']
        )
        
        fixtures["openmeteo_hourly"] = {
            "count": len(hourly_forecasts),
            "forecasts": [f.to_api_response() for f in hourly_forecasts[:24]],  # Apenas primeiras 24h
            "notes": f"Hourly forecast - salvando apenas primeiras 24h de {len(hourly_forecasts)} disponíveis"
        }
        print(f"   ✅ Sucesso: {len(hourly_forecasts)} horas de previsão (salvando 24h)")
        if hourly_forecasts:
            first = hourly_forecasts[0]
            print(f"   🕐 Primeira hora: {first.timestamp}, {first.temperature}°C")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        fixtures["openmeteo_hourly"] = {"error": str(e)}
    
    # Salvar fixtures
    fixtures_path = Path(__file__).parent / "fixtures" / "real_api_data.json"
    fixtures_path.parent.mkdir(exist_ok=True)
    
    with open(fixtures_path, 'w', encoding='utf-8') as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"✅ Fixtures salvas em: {fixtures_path}")
    print(f"📊 Total de dados: {len(fixtures) - 1} endpoints")
    
    return fixtures


async def main():
    """Main function"""
    try:
        fixtures = await fetch_real_data()
        
        print()
        print("=" * 60)
        print("📋 RESUMO DOS DADOS CAPTURADOS")
        print("=" * 60)
        
        for key, value in fixtures.items():
            if key == "metadata":
                continue
            
            if "error" in value:
                print(f"❌ {key}: ERRO")
            else:
                if "count" in value:
                    print(f"✅ {key}: {value['count']} items")
                else:
                    print(f"✅ {key}: OK")
        
        print()
        print("🎯 Use estes dados como fixtures nos testes!")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
