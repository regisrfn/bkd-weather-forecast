#!/usr/bin/env python3
"""
Análise detalhada do OpenWeather One Call API 3.0
Foco em períodos de chuva e previsão diária
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List
import requests

# Configurações
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
RIBEIRAO_DO_SUL = {
    "name": "Ribeirão do Sul",
    "lat": -22.7572,
    "lon": -49.9439,
    "city_id": "3543204"
}


def fetch_openweather_data(lat: float, lon: float) -> Dict[str, Any]:
    """Busca dados do OpenWeather One Call API 3.0"""
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "pt_br",
        "exclude": "minutely,alerts"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def classify_rain(rain_mm: float) -> tuple[str, str]:
    """Classifica intensidade de chuva"""
    if rain_mm == 0:
        return "🌤️  Sem chuva", ""
    elif rain_mm < 2.5:
        return "🌦️  Garoa leve", ""
    elif rain_mm < 10:
        return "🌧️  Chuva fraca", ""
    elif rain_mm < 50:
        return "🌧️  Chuva moderada", "⚠️"
    else:
        return "⛈️  Chuva forte", "🚨"


def classify_probability(prob: float) -> tuple[str, str]:
    """Classifica probabilidade de chuva"""
    prob_pct = prob * 100
    if prob_pct >= 70:
        return "⚠️  ALTA probabilidade de chuva", "🔴"
    elif prob_pct >= 50:
        return "⚡ Probabilidade moderada", "🟡"
    elif prob_pct >= 30:
        return "🌤️  Baixa probabilidade", "🟢"
    else:
        return "☀️  Improvável", "🟢"


def classify_uv(uvi: float) -> str:
    """Classifica índice UV"""
    if uvi <= 2:
        return "Baixo"
    elif uvi <= 5:
        return "Moderado"
    elif uvi <= 7:
        return "Alto"
    elif uvi <= 10:
        return "Muito Alto"
    else:
        return "Extremo"


def format_datetime(timestamp: int) -> str:
    """Formata timestamp Unix para datetime legível"""
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")


def format_time(timestamp: int) -> str:
    """Formata timestamp Unix para hora"""
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")


def format_date(timestamp: int) -> str:
    """Formata timestamp Unix para data"""
    dt = datetime.fromtimestamp(timestamp)
    weekday = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][dt.weekday()]
    return f"{dt.strftime('%d/%m/%Y')} ({weekday})"


def print_header(title: str, char: str = "="):
    """Imprime cabeçalho formatado"""
    width = 80
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")


def print_current_weather(data: Dict[str, Any]):
    """Imprime dados meteorológicos atuais"""
    current = data["current"]
    
    print_header("🌡️  DADOS ATUAIS")
    
    print(f"Data/Hora: {format_datetime(current['dt'])}")
    print(f"Temperatura: {current['temp']:.1f}°C")
    print(f"Sensação Térmica: {current['feels_like']:.1f}°C")
    print(f"Umidade: {current['humidity']}%")
    print(f"Pressão: {current['pressure']} hPa")
    print(f"Vento: {current['wind_speed']:.1f} m/s ({current['wind_deg']}°)")
    print(f"Nuvens: {current['clouds']}%")
    print(f"Visibilidade: {current['visibility'] / 1000:.1f} km")
    print(f"Descrição: {current['weather'][0]['description']}")


def print_daily_forecast(data: Dict[str, Any]):
    """Imprime previsão diária detalhada"""
    print_header("📅 PREVISÃO DIÁRIA (8 DIAS) - ANÁLISE DE CHUVA")
    
    for day in data["daily"]:
        print(f"\n📆 DIA: {format_date(day['dt'])}")
        print("━" * 80)
        
        # Temperaturas
        print("\n🌡️  TEMPERATURAS:")
        print(f"   • Mínima: {day['temp']['min']:.1f}°C")
        print(f"   • Máxima: {day['temp']['max']:.1f}°C")
        print(f"   • Manhã: {day['temp']['morn']:.1f}°C")
        print(f"   • Dia: {day['temp']['day']:.1f}°C")
        print(f"   • Tarde: {day['temp']['eve']:.1f}°C")
        print(f"   • Noite: {day['temp']['night']:.1f}°C")
        
        # Chuva
        rain_mm = day.get('rain', 0)
        rain_class, rain_alert = classify_rain(rain_mm)
        prob_status, prob_alert = classify_probability(day['pop'])
        
        print("\n💧 CHUVA:")
        print(f"   • Volume estimado: {rain_mm:.1f} mm")
        print(f"   • Probabilidade: {day['pop'] * 100:.0f}%")
        print(f"   • Classificação: {rain_class} {rain_alert}")
        print(f"   • Status: {prob_status} {prob_alert}")
        
        # Condições
        uv_class = classify_uv(day['uvi'])
        print("\n🌤️  CONDIÇÕES:")
        print(f"   • Descrição: {day['weather'][0]['description']}")
        print(f"   • Umidade: {day['humidity']}%")
        print(f"   • Vento: {day['wind_speed']:.1f} m/s")
        print(f"   • Nuvens: {day['clouds']}%")
        print(f"   • Pressão: {day['pressure']} hPa")
        print(f"   • Índice UV: {day['uvi']:.1f} ({uv_class})")
        
        # Astronomia
        daylight_hours = (day['sunset'] - day['sunrise']) / 3600
        print("\n🌅 ASTRONOMIA:")
        print(f"   • Nascer do Sol: {format_time(day['sunrise'])}")
        print(f"   • Pôr do Sol: {format_time(day['sunset'])}")
        print(f"   • Duração do dia: {daylight_hours:.2f} horas")


def print_rain_summary(data: Dict[str, Any]):
    """Imprime resumo de períodos de chuva"""
    print_header("📊 RESUMO DE PERÍODOS DE CHUVA")
    
    rainy_days = [
        day for day in data["daily"]
        if day.get('rain', 0) > 0 or day['pop'] >= 0.3
    ]
    
    if rainy_days:
        print(f"Total de dias com possibilidade de chuva: {len(rainy_days)} dias")
        print("━" * 80)
        
        for day in rainy_days:
            date = datetime.fromtimestamp(day['dt']).strftime('%d/%m')
            rain_mm = day.get('rain', 0)
            prob_pct = day['pop'] * 100
            desc = day['weather'][0]['description']
            
            rain_class, _ = classify_rain(rain_mm)
            _, prob_alert = classify_probability(day['pop'])
            
            print(f"{prob_alert} {date} - {desc} | {rain_mm:.1f}mm | Prob: {prob_pct:.0f}%")
    else:
        print("✅ Nenhum período significativo de chuva previsto nos próximos 8 dias")


def print_statistics(data: Dict[str, Any]):
    """Imprime estatísticas gerais"""
    print_header("📈 ESTATÍSTICAS GERAIS")
    
    daily = data["daily"]
    
    # Temperaturas
    temps_min = [day['temp']['min'] for day in daily]
    temps_max = [day['temp']['max'] for day in daily]
    
    print("🌡️  TEMPERATURAS:")
    print(f"   • Mínima absoluta: {min(temps_min):.1f}°C")
    print(f"   • Máxima absoluta: {max(temps_max):.1f}°C")
    print(f"   • Média das mínimas: {sum(temps_min) / len(temps_min):.1f}°C")
    print(f"   • Média das máximas: {sum(temps_max) / len(temps_max):.1f}°C")
    
    # Chuva
    total_rain = sum(day.get('rain', 0) for day in daily)
    avg_prob = sum(day['pop'] for day in daily) / len(daily) * 100
    
    max_rain_day = max(daily, key=lambda d: d.get('rain', 0))
    max_rain_date = datetime.fromtimestamp(max_rain_day['dt']).strftime('%d/%m')
    max_rain_mm = max_rain_day.get('rain', 0)
    
    print("\n💧 CHUVA:")
    print(f"   • Total acumulado (8 dias): {total_rain:.1f} mm")
    print(f"   • Dia com mais chuva: {max_rain_date} ({max_rain_mm:.1f} mm)")
    print(f"   • Média de probabilidade: {avg_prob:.0f}%")
    
    # Condições
    avg_humidity = sum(day['humidity'] for day in daily) / len(daily)
    avg_wind = sum(day['wind_speed'] for day in daily) / len(daily)
    max_uv = max(day['uvi'] for day in daily)
    
    print("\n🌤️  CONDIÇÕES:")
    print(f"   • Umidade média: {avg_humidity:.0f}%")
    print(f"   • Vento médio: {avg_wind:.1f} m/s")
    print(f"   • Índice UV máximo: {max_uv:.1f}")


def save_report(data: Dict[str, Any], city: Dict[str, str], filename: str = None):
    """Salva relatório em JSON"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openweather_report_{city['city_id']}_{timestamp}.json"
    
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo em: {filepath}")


def main():
    """Função principal"""
    city = RIBEIRAO_DO_SUL
    
    print(f"\n{'=' * 80}")
    print(f"📊 ANÁLISE OPENWEATHER ONE CALL API 3.0 - {city['name']}")
    print(f"{'=' * 80}")
    
    try:
        print("\n🔄 Buscando dados da API...")
        data = fetch_openweather_data(city['lat'], city['lon'])
        
        # Análises
        print_current_weather(data)
        print_daily_forecast(data)
        print_rain_summary(data)
        print_statistics(data)
        
        # Salvar relatório
        save_report(data, city)
        
        print_header("✅ Análise concluída!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erro ao buscar dados da API: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
