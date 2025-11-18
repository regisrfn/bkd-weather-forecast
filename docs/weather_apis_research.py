"""
Pesquisa e documentação de APIs de Previsão do Tempo

APIs Brasileiras e Internacionais disponíveis
"""

# ========================================
# 1. INMET - Instituto Nacional de Meteorologia
# ========================================

INMET_API = {
    'name': 'INMET - Instituto Nacional de Meteorologia',
    'country': 'Brasil',
    'documentation': 'https://portal.inmet.gov.br/manual/manual-de-uso-da-api-esta%C3%A7%C3%B5es',
    'free': True,
    'requires_key': False,
    'coverage': 'Brasil',
    
    'endpoints': {
        'estacoes_automaticas': {
            'url': 'https://apitempo.inmet.gov.br/estacao/{data_inicio}/{data_fim}/{codigo_estacao}',
            'method': 'GET',
            'description': 'Dados de estações automáticas',
            'example': 'https://apitempo.inmet.gov.br/estacao/2025-11-17/2025-11-18/A701',
            'params': {
                'data_inicio': 'YYYY-MM-DD',
                'data_fim': 'YYYY-MM-DD',
                'codigo_estacao': 'Ex: A701'
            },
            'response_fields': [
                'DC_NOME (nome da estação)',
                'UF',
                'VL_LATITUDE',
                'VL_LONGITUDE',
                'CHUVA (mm)',
                'TEM_INS (temperatura instantânea °C)',
                'TEM_MAX (temperatura máxima °C)',
                'TEM_MIN (temperatura mínima °C)',
                'UMD_INS (umidade instantânea %)',
                'VEN_VEL (velocidade do vento m/s)'
            ]
        },
        
        'lista_estacoes': {
            'url': 'https://apitempo.inmet.gov.br/estacoes/T',
            'method': 'GET',
            'description': 'Lista todas as estações meteorológicas',
            'params': {
                'T': 'Tipo (T = Todas, A = Automáticas, M = Manuais)'
            }
        }
    },
    
    'pros': [
        'Dados oficiais do governo brasileiro',
        'Gratuito e sem necessidade de chave de API',
        'Dados em tempo real de estações reais',
        'Cobertura nacional'
    ],
    
    'cons': [
        'Cobertura limitada (apenas onde há estações)',
        'Não fornece previsão, apenas dados observados',
        'API instável às vezes',
        'Sem coordenadas exatas dos municípios'
    ]
}


# ========================================
# 2. OpenWeatherMap
# ========================================

OPENWEATHER_API = {
    'name': 'OpenWeatherMap',
    'country': 'Internacional',
    'documentation': 'https://openweathermap.org/api',
    'free': True,  # Plano gratuito disponível
    'requires_key': True,
    'coverage': 'Mundial',
    
    'plans': {
        'free': {
            'calls_per_minute': 60,
            'calls_per_day': 1000,
            'price': 0,
            'features': ['Current weather', 'Forecast 5 days']
        },
        'startup': {
            'calls_per_minute': 600,
            'calls_per_month': 100000,
            'price': 40  # USD/month
        }
    },
    
    'endpoints': {
        'current_weather': {
            'url': 'https://api.openweathermap.org/data/2.5/weather',
            'method': 'GET',
            'description': 'Clima atual',
            'params': {
                'lat': 'Latitude',
                'lon': 'Longitude',
                'appid': 'API Key',
                'units': 'metric (Celsius)',
                'lang': 'pt_br'
            },
            'example': 'https://api.openweathermap.org/data/2.5/weather?lat=-22.7572&lon=-49.9439&appid=YOUR_KEY&units=metric&lang=pt_br'
        },
        
        'forecast_5days': {
            'url': 'https://api.openweathermap.org/data/2.5/forecast',
            'method': 'GET',
            'description': 'Previsão 5 dias (a cada 3 horas)',
            'params': {
                'lat': 'Latitude',
                'lon': 'Longitude',
                'appid': 'API Key',
                'units': 'metric'
            }
        }
    },
    
    'pros': [
        'API estável e bem documentada',
        'Cobertura mundial',
        'Previsão de 5 dias incluída no plano gratuito',
        'Muitos dados: temperatura, chuva, vento, umidade, pressão, etc.',
        'SDKs oficiais em várias linguagens'
    ],
    
    'cons': [
        'Requer chave de API',
        'Limite de chamadas no plano gratuito',
        'Dados podem não ser precisos para pequenas cidades'
    ]
}


# ========================================
# 3. CPTEC/INPE
# ========================================

CPTEC_API = {
    'name': 'CPTEC/INPE - Centro de Previsão de Tempo e Estudos Climáticos',
    'country': 'Brasil',
    'documentation': 'http://servicos.cptec.inpe.br/XML/',
    'free': True,
    'requires_key': False,
    'coverage': 'Brasil',
    
    'endpoints': {
        'previsao_cidade': {
            'url': 'http://servicos.cptec.inpe.br/XML/cidade/{codigo_cidade}/previsao.xml',
            'method': 'GET',
            'description': 'Previsão de 4 dias para uma cidade',
            'format': 'XML',
            'params': {
                'codigo_cidade': 'Código da cidade (diferente do IBGE)'
            }
        },
        
        'lista_cidades': {
            'url': 'http://servicos.cptec.inpe.br/XML/listaCidades',
            'method': 'GET',
            'description': 'Lista de todas as cidades disponíveis',
            'format': 'XML'
        }
    },
    
    'pros': [
        'Dados oficiais do INPE',
        'Gratuito',
        'Previsão de 4 dias',
        'Boa cobertura nacional'
    ],
    
    'cons': [
        'API antiga (XML)',
        'Códigos de cidade diferentes do IBGE',
        'Documentação limitada',
        'Sem dados de chuva detalhados'
    ]
}


# ========================================
# 4. WeatherAPI
# ========================================

WEATHERAPI = {
    'name': 'WeatherAPI',
    'country': 'Internacional',
    'documentation': 'https://www.weatherapi.com/docs/',
    'free': True,
    'requires_key': True,
    'coverage': 'Mundial',
    
    'plans': {
        'free': {
            'calls_per_day': 1000000,
            'price': 0,
            'features': ['Current weather', 'Forecast 3 days', 'Historical data 7 days']
        }
    },
    
    'endpoints': {
        'current': {
            'url': 'https://api.weatherapi.com/v1/current.json',
            'params': {
                'key': 'API Key',
                'q': 'Latitude,Longitude ou Nome da cidade',
                'lang': 'pt'
            }
        },
        
        'forecast': {
            'url': 'https://api.weatherapi.com/v1/forecast.json',
            'params': {
                'key': 'API Key',
                'q': 'Latitude,Longitude',
                'days': '1-3 (plano gratuito)',
                'lang': 'pt'
            }
        }
    },
    
    'pros': [
        'Plano gratuito generoso (1M chamadas/dia)',
        'API moderna e bem documentada',
        'Previsão de 3 dias no plano gratuito',
        'Dados de chuva por hora',
        'Suporte a português'
    ],
    
    'cons': [
        'Requer chave de API',
        'Empresa internacional (pode ter latência)',
        'Plano gratuito tem limitações de histórico'
    ]
}


# ========================================
# RECOMENDAÇÃO PARA O PROJETO
# ========================================

RECOMMENDATION = {
    'primary': {
        'api': 'OpenWeatherMap',
        'reason': 'Mais estável, bem documentada, e ampla adoção',
        'plan': 'Free (1000 calls/day)',
        'implementation': 'Usar para previsão e dados em tempo real'
    },
    
    'fallback': {
        'api': 'INMET',
        'reason': 'Dados oficiais brasileiros, sem custo',
        'implementation': 'Usar quando OpenWeather falhar ou para validação'
    },
    
    'future': {
        'api': 'WeatherAPI',
        'reason': 'Plano gratuito muito generoso',
        'when': 'Se precisar escalar além de 1000 chamadas/dia'
    }
}


# ========================================
# ESTRATÉGIA DE CACHE
# ========================================

CACHE_STRATEGY = {
    'weather_data': {
        'ttl': 300,  # 5 minutos
        'reason': 'Dados climáticos mudam lentamente'
    },
    
    'forecast': {
        'ttl': 1800,  # 30 minutos
        'reason': 'Previsões são atualizadas a cada hora'
    },
    
    'municipalities': {
        'ttl': 86400,  # 24 horas
        'reason': 'Dados estáticos, raramente mudam'
    }
}


if __name__ == '__main__':
    print("=" * 70)
    print("📡 APIs DE PREVISÃO DO TEMPO - ANÁLISE COMPARATIVA")
    print("=" * 70)
    
    for api in [INMET_API, OPENWEATHER_API, CPTEC_API, WEATHERAPI]:
        print(f"\n{'=' * 70}")
        print(f"🌤️  {api['name']}")
        print(f"{'=' * 70}")
        print(f"País: {api['country']}")
        print(f"Gratuita: {'Sim' if api['free'] else 'Não'}")
        print(f"Requer Chave: {'Sim' if api['requires_key'] else 'Não'}")
        print(f"Cobertura: {api['coverage']}")
        print(f"\n✅ Prós:")
        for pro in api['pros']:
            print(f"   - {pro}")
        print(f"\n❌ Contras:")
        for con in api['cons']:
            print(f"   - {con}")
    
    print(f"\n{'=' * 70}")
    print("🎯 RECOMENDAÇÃO FINAL")
    print(f"{'=' * 70}")
    print(f"\n📌 Principal: {RECOMMENDATION['primary']['api']}")
    print(f"   {RECOMMENDATION['primary']['reason']}")
    print(f"\n🔄 Fallback: {RECOMMENDATION['fallback']['api']}")
    print(f"   {RECOMMENDATION['fallback']['reason']}")
    print(f"\n🚀 Futuro: {RECOMMENDATION['future']['api']}")
    print(f"   {RECOMMENDATION['future']['reason']}")
