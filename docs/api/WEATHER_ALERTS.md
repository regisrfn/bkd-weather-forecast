# Alertas Meteorológicos

## Visão Geral

A API de previsão do tempo inclui um sistema avançado de alertas meteorológicos que analisa as previsões dos próximos 5 dias e identifica condições climáticas que requerem atenção.

## Características

- ✅ **Análise automática** - Alertas gerados a partir das previsões da OpenWeather API
- ✅ **Múltiplos critérios** - Baseados em códigos climáticos, volume de chuva (mm/h), velocidade do vento e temperatura
- ✅ **Variação de temperatura** - Detecta mudanças bruscas entre dias consecutivos
- ✅ **Campo details opcional** - Informações adicionais para o frontend decidir exibir ou não
- ✅ **Deduplição automática** - Cada código de alerta aparece apenas uma vez
- ✅ **Horário local** - Timestamps em horário de Brasília (America/Sao_Paulo)

## Estrutura de um Alerta

```json
{
  "code": "MODERATE_RAIN",
  "severity": "warning",
  "description": "🌧️ Chuva moderada",
  "timestamp": "2025-11-27T18:00:00-03:00",
  "details": {
    "rain_mm_h": 15.5,
    "probability_percent": 85.0,
    "rain_ends_at": "2025-11-27T21:00:00-03:00"
  }
}
```

**Observação sobre `rain_ends_at`:**
- Representa o **fim do último intervalo de 3h com chuva**
- Exemplo: se tem chuva às 18h, o intervalo é 18h-21h, então `rain_ends_at` será 21h
- Se a chuva continuar além de 5 dias, o campo não é incluído

### Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `code` | string | Código único do alerta (ver catálogo completo abaixo) |
| `severity` | string | Nível de severidade: `info`, `warning`, `alert`, `danger` |
| `description` | string | Descrição em português com emoji para melhor UX |
| `timestamp` | string | Data/hora quando o alerta se aplica (ISO 8601) |
| `details` | object | Informações adicionais opcionais com valores numéricos |

## 📌 Importante: Threshold de Probabilidade

**Todos os alertas baseados em volume de chuva requerem probabilidade >= 80%** para serem gerados. Isso inclui:
- DRIZZLE (Garoa)
- LIGHT_RAIN (Chuva fraca)
- MODERATE_RAIN (Chuva moderada)
- HEAVY_RAIN (Chuva forte por volume)
- RAIN_EXPECTED (Alta probabilidade de chuva)

**Exceções que SEMPRE geram alerta (independente da probabilidade):**
- STORM / STORM_RAIN - Tempestades (códigos 2xx)
- HEAVY_RAIN por código (códigos 502-504)

Este threshold reduz falsos positivos enquanto mantém alertas críticos de tempestades.

## 📊 Métrica de Intensidade de Chuva (rainfallIntensity)

**Nova implementação**: `rainfallIntensity` agora é uma **métrica composta** que combina volume de precipitação (mm/h) e probabilidade (%).

### Fórmula

```
rainfallIntensity = min(100, (rain_1h × rain_probability / 100) / 10.0 × 100)
```

Onde:
- `rain_1h`: Volume de precipitação em mm/h (da OpenWeatherMap API)
- `rain_probability`: Probabilidade de precipitação de 0-100% (campo `pop` da API)
- `10.0`: Threshold de referência (10mm/h = início de chuva moderada segundo WMO)

### Escala de Valores

| Intensidade | Significado | Exemplo |
|-------------|-------------|----------|
| 0 | Sem chuva | 0mm × 100% = 0 pontos |
| 1-25 | Chuva leve | 2mm × 50% = 10 pontos, garoa com média probabilidade |
| 26-50 | Chuva moderada | 5mm × 80% = 40 pontos, chuva fraca provável |
| 51-75 | Chuva forte | 8mm × 90% = 72 pontos, chuva considerável |
| 76-100 | Chuva intensa | 10mm × 100% = 100 pontos, chuva moderada garantida |

### Vantagens da Métrica Composta

✅ **Resolve "100% probabilidade mas 0mm"**: Retorna 0 pontos quando não há volume real  
✅ **Representa intensidade real**: Combina chance + quantidade de chuva  
✅ **Baseada em padrões WMO**: 10mm/h como referência de chuva moderada  
✅ **Escala intuitiva**: 0-100 mantém compatibilidade com UI existente  
✅ **Cap em 100**: Chuvas extremas não quebram interface

### Comparação com Campos Separados

- **`rainfallIntensity`**: Métrica composta (volume × probabilidade) - **usar para visualização**
- **`rainVolumeHour`**: Volume puro em mm/h - usar para alertas técnicos
- **`rain_probability`**: Probabilidade pura 0-100% - disponível internamente

## Níveis de Severidade

| Severidade | Cor Sugerida | Uso | Ação Recomendada |
|------------|--------------|-----|------------------|
| `info` 🔵 | Azul | Informativo | Apenas informar o usuário |
| `warning` 🟡 | Amarelo | Atenção | Preparação recomendada |
| `alert` 🟠 | Laranja | Alerta | Ação necessária |
| `danger` 🔴 | Vermelho | Perigo | Ação imediata necessária |

## Catálogo de Alertas

### 🌧️ Precipitação (baseados em volume mm/h)

#### DRIZZLE
- **Código**: `DRIZZLE`
- **Severidade**: `info`
- **Descrição**: 🌦️ Garoa
- **Limiar**: < 2.5 mm/h
- **Details**: `{ "rain_mm_h": 1.5, "probability_percent": 75.0, "rain_ends_at": "2025-11-27T18:00:00-03:00" }`
- **Uso**: Informar sobre chuva muito leve que não interfere em atividades

#### LIGHT_RAIN
- **Código**: `LIGHT_RAIN`
- **Severidade**: `info`
- **Descrição**: 🌧️ Chuva fraca
- **Limiar**: 2.5-10 mm/h
- **Details**: `{ "rain_mm_h": 5.0, "probability_percent": 80.0, "rain_ends_at": "2025-11-27T19:00:00-03:00" }`
- **Uso**: Chuva leve, guarda-chuva recomendado

#### MODERATE_RAIN
- **Código**: `MODERATE_RAIN`
- **Severidade**: `warning`
- **Descrição**: 🌧️ Chuva moderada
- **Limiar**: 10-50 mm/h
- **Details**: `{ "rain_mm_h": 15.0, "probability_percent": 85.0, "rain_ends_at": "2025-11-27T21:00:00-03:00" }`
- **Uso**: Chuva considerável, evitar atividades externas

#### HEAVY_RAIN
- **Código**: `HEAVY_RAIN`
- **Severidade**: `alert`
- **Descrição**: ⚠️ ALERTA: Chuva forte
- **Limiar**: > 50 mm/h
- **Details**: `{ "rain_mm_h": 65.0, "probability_percent": 90.0, "rain_ends_at": "2025-11-28T02:00:00-03:00" }`
- **Uso**: Chuva intensa, risco de alagamentos

#### RAIN_EXPECTED
- **Código**: `RAIN_EXPECTED`
- **Severidade**: `info`
- **Descrição**: 🌧️ Alta probabilidade de chuva
- **Limiar**: Probabilidade ≥ 70% (sem volume medido)
- **Details**: `{ "probability_percent": 85.0 }`
- **Uso**: Avisar usuário para levar guarda-chuva

### ⛈️ Tempestade

#### STORM
- **Código**: `STORM`
- **Severidade**: `danger`
- **Descrição**: ⚠️ ALERTA: Tempestade com raios
- **Condição**: Códigos OpenWeather 200, 201, 202, 210, 211, 212, 221
- **Details**: `{ "weather_code": 210, "rain_mm_h": 20.0, "probability_percent": 95.0, "rain_ends_at": "2025-11-28T00:00:00-03:00" }`
- **Uso**: Perigo de raios, buscar abrigo imediatamente

#### STORM_RAIN
- **Código**: `STORM_RAIN`
- **Severidade**: `alert`
- **Descrição**: ⚠️ Tempestade com chuva
- **Condição**: Outros códigos 2xx
- **Details**: `{ "weather_code": 231, "rain_mm_h": 15.0, "probability_percent": 85.0, "rain_ends_at": "2025-11-27T23:00:00-03:00" }`
- **Uso**: Tempestade menos intensa, mas ainda requer cuidado

### 💨 Vento

#### MODERATE_WIND
- **Código**: `MODERATE_WIND`
- **Severidade**: `info`
- **Descrição**: 💨 Ventos moderados
- **Limiar**: 30-49 km/h
- **Details**: `{ "wind_speed_kmh": 35.0 }`
- **Uso**: Informar sobre vento perceptível

#### STRONG_WIND
- **Código**: `STRONG_WIND`
- **Severidade**: `alert`
- **Descrição**: 💨 ALERTA: Ventos fortes
- **Limiar**: ≥ 50 km/h
- **Details**: `{ "wind_speed_kmh": 65.0 }`
- **Uso**: Vento forte, cuidado com objetos soltos e árvores

### 🌡️ Temperatura

#### COLD
- **Código**: `COLD`
- **Severidade**: `alert`
- **Descrição**: 🧊 Frio
- **Limiar**: < 12°C
- **Details**: `{ "temperature_c": 11.0 }`
- **Uso**: Temperatura baixa para padrões brasileiros, agasalhos recomendados

#### VERY_COLD
- **Código**: `VERY_COLD`
- **Severidade**: `danger`
- **Descrição**: 🥶 ALERTA: Frio intenso
- **Limiar**: < 8°C
- **Details**: `{ "temperature_c": 6.0 }`
- **Uso**: Frio extremo para Brasil, proteção extra necessária

#### TEMP_DROP
- **Código**: `TEMP_DROP`
- **Severidade**: `warning`
- **Descrição**: 🌡️ Queda de temperatura (X°C em Y dias)
- **Limiar**: Variação > 8°C entre quaisquer dias da previsão (não apenas consecutivos)
- **Details**: 
```json
{
  "day_1_date": "2025-11-27",
  "day_1_max_c": 28.0,
  "day_2_date": "2025-11-29",
  "day_2_max_c": 15.0,
  "variation_c": -13.0,
  "days_between": 2
}
```
- **Uso**: Alertar sobre mudança brusca de temperatura para preparação. O sistema compara todos os pares de dias e retorna apenas a maior queda detectada.

#### TEMP_RISE
- **Código**: `TEMP_RISE`
- **Severidade**: `info`
- **Descrição**: 🌡️ Aumento de temperatura (+X°C em Y dias)
- **Limiar**: Variação > 8°C entre quaisquer dias da previsão (não apenas consecutivos)
- **Details**:
```json
{
  "day_1_date": "2025-11-27",
  "day_1_max_c": 18.0,
  "day_2_date": "2025-11-30",
  "day_2_max_c": 28.0,
  "variation_c": 10.0,
  "days_between": 3
}
```
- **Uso**: Informar sobre aquecimento significativo. O sistema compara todos os pares de dias e retorna apenas o maior aumento detectado.

### ❄️ Neve

#### SNOW
- **Código**: `SNOW`
- **Severidade**: `info`
- **Descrição**: ❄️ Neve (raro no Brasil)
- **Condição**: Códigos OpenWeather 600-699
- **Details**: `{ "weather_code": 600, "temperature_c": 0.5 }`
- **Uso**: Evento raro, principalmente em regiões serranas do Sul

### 🌫️ Visibilidade

#### LOW_VISIBILITY
- **Código**: `LOW_VISIBILITY`
- **Severidade**: `alert` (< 1km) ou `warning` (< 3km)
- **Descrição**: 🌫️ ALERTA: Visibilidade reduzida
- **Limiar**: < 3000 metros
- **Details**: `{ "visibility_m": 500 }`
- **Uso**: Neblina, névoa ou fumaça reduzindo visibilidade. Importante para segurança no trânsito

## Exemplos de Resposta da API

### Exemplo 1: Chuva Moderada + Vento Forte

```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "temperature": 22.0,
  "weatherAlert": [
    {
      "code": "MODERATE_RAIN",
      "severity": "warning",
      "description": "🌧️ Chuva moderada",
      "timestamp": "2025-11-27T15:00:00-03:00",
      "details": {
        "rain_mm_h": 18.5,
        "probability_percent": 85.0,
        "rain_ends_at": "2025-11-27T21:00:00-03:00"
      }
    },
    {
      "code": "STRONG_WIND",
      "severity": "alert",
      "description": "💨 ALERTA: Ventos fortes",
      "timestamp": "2025-11-27T18:00:00-03:00",
      "details": {
        "wind_speed_kmh": 55.0
      }
    }
  ]
}
```

### Exemplo 2: Tempestade Severa

```json
{
  "cityId": "3548708",
  "cityName": "São Carlos",
  "temperature": 24.0,
  "weatherAlert": [
    {
      "code": "HEAVY_RAIN",
      "severity": "alert",
      "description": "⚠️ ALERTA: Chuva forte",
      "timestamp": "2025-11-27T20:00:00-03:00",
      "details": {
        "rain_mm_h": 60.0,
        "probability_percent": 90.0,
        "rain_ends_at": "2025-11-28T02:00:00-03:00"
      }
    },
    {
      "code": "STORM",
      "severity": "danger",
      "description": "⚠️ ALERTA: Tempestade com raios",
      "timestamp": "2025-11-27T21:00:00-03:00",
      "details": {
        "weather_code": 210,
        "rain_mm_h": 65.0,
        "probability_percent": 95.0,
        "rain_ends_at": "2025-11-28T00:00:00-03:00"
      }
    },
    {
      "code": "STRONG_WIND",
      "severity": "alert",
      "description": "💨 ALERTA: Ventos fortes",
      "timestamp": "2025-11-27T21:00:00-03:00",
      "details": {
        "wind_speed_kmh": 70.0
      }
    }
  ]
}
```

### Exemplo 3: Queda de Temperatura

```json
{
  "cityId": "3509502",
  "cityName": "Campinas",
  "temperature": 26.0,
  "weatherAlert": [
    {
      "code": "TEMP_DROP",
      "severity": "warning",
      "description": "🌡️ Queda de temperatura (13°C em 2 dias)",
      "timestamp": "2025-11-28T00:00:00-03:00",
      "details": {
        "day_1_date": "2025-11-27",
        "day_1_max_c": 28.0,
        "day_2_date": "2025-11-29",
        "day_2_max_c": 15.0,
        "variation_c": -13.0,
        "days_between": 2
      }
    },
    {
      "code": "COLD",
      "severity": "alert",
      "description": "🧊 Frio",
      "timestamp": "2025-11-28T06:00:00-03:00",
      "details": {
        "temperature_c": 11.0
      }
    }
  ]
}
```

## Implementação no Frontend

### Filtrar por Severidade

```javascript
const criticalAlerts = weather.weatherAlert.filter(alert => 
  alert.severity === 'danger' || alert.severity === 'alert'
);

if (criticalAlerts.length > 0) {
  showEmergencyNotification(criticalAlerts);
}
```

### Exibir Badge de Alerta

```javascript
function getAlertBadge(severity) {
  const badges = {
    'info': { color: 'blue', icon: 'ℹ️' },
    'warning': { color: 'yellow', icon: '⚠️' },
    'alert': { color: 'orange', icon: '🚨' },
    'danger': { color: 'red', icon: '⛔' }
  };
  return badges[severity];
}
```

### Agrupar por Tipo

```javascript
const alertsByType = weather.weatherAlert.reduce((acc, alert) => {
  const type = alert.code.includes('RAIN') ? 'rain' :
               alert.code.includes('WIND') ? 'wind' :
               alert.code.includes('TEMP') || alert.code.includes('COLD') ? 'temperature' :
               'other';
  
  if (!acc[type]) acc[type] = [];
  acc[type].push(alert);
  return acc;
}, {});
```

### Usar Detalhes Opcionalmente

```javascript
function formatAlertDetails(alert) {
  if (!alert.details) return alert.description;
  
  const details = alert.details;
  let extraInfo = [];
  
  if (details.rain_mm_h) {
    extraInfo.push(`${details.rain_mm_h} mm/h`);
  }
  if (details.probability_percent) {
    extraInfo.push(`${details.probability_percent}% chance`);
  }
  if (details.rain_ends_at) {
    const endTime = new Date(details.rain_ends_at);
    extraInfo.push(`até ${endTime.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`);
  }
  if (details.visibility_m) {
    extraInfo.push(`visibilidade ${details.visibility_m}m`);
  }
  if (details.wind_speed_kmh) {
    extraInfo.push(`${details.wind_speed_kmh} km/h`);
  }
  if (details.temperature_c !== undefined) {
    extraInfo.push(`${details.temperature_c}°C`);
  }
  if (details.variation_c) {
    extraInfo.push(`variação de ${Math.abs(details.variation_c)}°C`);
  }
  if (details.days_between) {
    extraInfo.push(`${details.days_between} ${details.days_between === 1 ? 'dia' : 'dias'}`);
  }
  
  return extraInfo.length > 0 
    ? `${alert.description} (${extraInfo.join(', ')})`
    : alert.description;
}
```

### Componente React Exemplo

```jsx
function WeatherAlerts({ alerts }) {
  const severityColors = {
    info: 'bg-blue-100 text-blue-800',
    warning: 'bg-yellow-100 text-yellow-800',
    alert: 'bg-orange-100 text-orange-800',
    danger: 'bg-red-100 text-red-800'
  };

  return (
    <div className="space-y-2">
      {alerts.map((alert, index) => (
        <div 
          key={index}
          className={`p-3 rounded-lg ${severityColors[alert.severity]}`}
        >
          <div className="font-semibold">{alert.description}</div>
          <div className="text-sm">
            {new Date(alert.timestamp).toLocaleString('pt-BR')}
          </div>
          {alert.details && (
            <div className="text-xs mt-1 opacity-75">
              {JSON.stringify(alert.details)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

## Considerações de Design

### Por que o campo `details` é opcional?

- **Retrocompatibilidade**: Frontends antigos não quebram
- **Flexibilidade**: Frontend escolhe se exibe ou não
- **Progressive Enhancement**: Pode adicionar tooltips/popovers com detalhes
- **Simplicidade**: Descrição já é informativa por si só

### Limiares Contextualizados para Brasil

Os limiares de temperatura consideram o clima brasileiro:

- **12°C**: Considerado frio na maior parte do país
- **8°C**: Frio intenso, comum apenas em regiões serranas do Sul

### Deduplição de Alertas

Cada código aparece apenas uma vez para evitar:
- ❌ Múltiplos alertas `STRONG_WIND` em horários diferentes
- ✅ Um único alerta `STRONG_WIND` com timestamp do primeiro evento

## Mapeamento de Códigos OpenWeather

| Código OW | Categoria | Alerta Gerado |
|-----------|-----------|---------------|
| 200-212, 221 | Tempestade com raios | `STORM` |
| 230-232 | Tempestade com garoa | `STORM_RAIN` |
| 300-321 | Garoa | `DRIZZLE` (se volume medido) |
| 500-531 | Chuva | `LIGHT_RAIN`, `MODERATE_RAIN`, `HEAVY_RAIN` |
| 600-622 | Neve | `SNOW` |
| 701-781 | Atmosfera (neblina, etc) | Sem alerta específico |
| 800 | Céu limpo | Sem alerta |
| 801-804 | Nuvens | Sem alerta |

## Roadmap Futuro

- [ ] Alertas de visibilidade (< 1km)
- [ ] Alertas de umidade extrema (> 90%)
- [ ] Alertas de pressão atmosférica anormal
- [ ] Alertas de UV index alto
- [ ] Integração com alertas do INMET
- [ ] Notificações push para alertas críticos
- [ ] Histórico de alertas por região
- [ ] Machine Learning para previsão de alertas

## Referências

- [OpenWeather Weather Conditions](https://openweathermap.org/weather-conditions)
- [INMET - Instituto Nacional de Meteorologia](https://portal.inmet.gov.br/)
- [Escala Beaufort - Velocidade do Vento](https://pt.wikipedia.org/wiki/Escala_de_Beaufort)
