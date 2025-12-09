# Regras de Alertas

## Severidades e formato
- Severidades (`AlertSeverity`): `info`, `warning`, `alert`, `danger`.
- Estrutura de retorno: `code`, `severity`, `description`, `timestamp` (ISO) e `details` (campos específicos).
- Alertas são deduplicados por `code`, priorizando o timestamp mais próximo do evento.

## Pipeline de geração
```mermaid
flowchart LR
  HF[HourlyForecast] & DF[DailyForecast] --> AG[AlertsGenerator]
  AG --> ORCH[WeatherAlertOrchestrator]
  ORCH --> Rain[RainAlertService]
  ORCH --> Wind[WindAlertService]
  ORCH --> Vis[VisibilityAlertService]
  ORCH --> Temp[TemperatureAlertService]
  AG --> Trends[Análise de tendências\n(temp/precip dia)]
  AG --> Output[weather_alert[]]
```

### Fontes de dados
- **HourlyForecast** (preferencial): usa `rainfall_intensity`, `precipitation_probability`, `precipitation`, `wind_speed`, `visibility`, `temperature`.
- **DailyForecast** (complemento): adiciona acumulado diário, vento máximo e índice UV para dias não cobertos por hourly.

## Códigos e gatilhos
| Código | Severidade | Gatilho (thresholds) | Detalhes adicionais |
|--------|------------|----------------------|---------------------|
| `DRIZZLE` | info | `rainfall_intensity >= 1` | `probabilityPercent`, `rainMmH?` |
| `LIGHT_RAIN` | info | `rainfall_intensity >= 10` | idem |
| `MODERATE_RAIN` | warning | `rainfall_intensity >= 25` | idem |
| `HEAVY_RAIN` | alert | `rainfall_intensity >= 60` | idem |
| `STORM` | alert | `rainfall_intensity >= 40` **e** `rain_prob >= 70` | idem |
| `RAIN_EXPECTED` | info | `rain_prob >= 90` **e** `rain_1h >= 0.3` quando intensidade < 1 | `probabilityPercent`, `rainMmH` |
| `HEAVY_RAIN_DAY` | warning/alert | Acumulado diário > 20 mm e intensidade efetiva >= 25; severidade `alert` se > 50 mm | `date`, `precipitationMm`, `probabilityPercent` |
| `STRONG_WIND` | alert | `wind_speed >= 50 km/h` | `windSpeedKmh` |
| `MODERATE_WIND` | info | `wind_speed >= 30 km/h` | `windSpeedKmh` |
| `STRONG_WIND_DAY` | warning/alert | Vento diário > 40/60 km/h (wind_speed_max) | `date`, `windSpeedKmh` |
| `LOW_VISIBILITY` | warning/alert | `< 3000 m` (warning) ou `< 1000 m` (alert) | `visibilityMeters` |
| `SNOW` | info | Códigos de neve ou `temperature_c < 2` com precipitação | `temperatureC`, `weatherCode` |
| `COLD` | alert | `temperature_c < 12°C` | `temperatureC` |
| `VERY_COLD` | danger | `temperature_c < 8°C` | `temperatureC` |
| `TEMP_DROP` | info | Queda >= 8°C entre máximas de dias próximos (janela de 3 dias) | Datas e variação em `details` |
| `TEMP_RISE` | warning | Aumento >= 8°C entre máximas de dias próximos | Datas e variação em `details` |
| `EXTREME_UV` | warning | `uv_index >= 11` | `uvIndex`, `date` |

## Cálculo de intensidade de chuva
- **Composta**: `(rain_volume_mm_h / 30) * sigmoid(prob, k=0.2, midpoint=70) * 100`, capado em 100.
- Usada para classificar chuva (DRIZZLE → STORM) e para detectar `HEAVY_RAIN_DAY`.
- `rainEndsAt` é adicionado para alertas de chuva quando existem 2h consecutivas sem chuva após o pico.

## Estratégia de cobertura
- `generate_alerts_for_weather` combina hourly + daily até 7 dias:
  - Usa hourly para dias com >=20 horas disponíveis (cobertura completa).
  - Complementa com daily nos dias sem cobertura horária.
  - Analisa tendências de temperatura com janela deslizante (O(n)).
- Regional e city reusam os mesmos dados já buscados (sem refetch).

## Campos em `details`
- Probabilidade/volume de chuva: `probabilityPercent`, `rainMmH`, `rainEndsAt?`
- Vento: `windSpeedKmh`
- Visibilidade: `visibilityMeters`
- Tendência de temperatura: `day1Date`, `day1MaxC`, `day2Date`, `day2MaxC`, `variationC`, `daysBetween`
- UV: `uvIndex`, `date`
