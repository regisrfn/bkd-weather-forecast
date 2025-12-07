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
    "rainMmH": 15.5,
    "probabilityPercent": 85.0,
    "rainEndsAt": "2025-11-27T21:00:00-03:00"
  }
}
```

**Observação sobre `rainEndsAt`:**
- Representa o **fim do último intervalo de 3h com chuva**
- Exemplo: se tem chuva às 18h, o intervalo é 18h-21h, então `rainEndsAt` será 21h
- Se a chuva continuar além de 5 dias, o campo não é incluído

### Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `code` | string | Código único do alerta (ver catálogo completo abaixo) |
| `severity` | string | Nível de severidade: `info`, `warning`, `alert`, `danger` |
| `description` | string | Descrição em português com emoji para melhor UX |
| `timestamp` | string | Data/hora quando o alerta se aplica (ISO 8601) |
| `details` | object | Informações adicionais opcionais com valores numéricos |

## 📌 Critérios de chuva (intensidade primeiro)

- Alertas de chuva (DRIZZLE/LIGHT/MODERATE/HEAVY) são gerados **apenas** pela intensidade composta (`rainfallIntensity`), que combina volume × probabilidade. Códigos climáticos não forçam alerta sozinhos.
- STORM (códigos 2xx/95/96/99) só aparece se a intensidade atingir pelo menos o limiar de chuva moderada.
- **RAIN_EXPECTED** é gerado apenas quando:
  - `rain_1h == 0` **e** `rainfallIntensity == 0`
  - Probabilidade >= `RAIN_PROBABILITY_THRESHOLD` (80%)
  - Existe código de chuva (WMO/OWM)
  - Não há alertas de volume/intensidade para o mesmo horário

## 📊 Métrica de Intensidade de Chuva (rainfallIntensity)

**Nova implementação**: `rainfallIntensity` agora é uma **métrica composta** que combina volume de precipitação (mm/h) e probabilidade (%).

### Fórmula

```
rainfallIntensity = min(100, (rain_1h × rainProbability / 100) / 30.0 × 100)
```

Onde:
- `rain_1h`: Volume de precipitação em mm/h (da OpenWeatherMap API)
- `rainProbability`: Probabilidade de precipitação de 0-100% (campo `pop` da API)
- `30.0`: Threshold de referência (30mm/h = chuva forte)

### Escala de Valores

| Intensidade | Significado | Exemplo |
|-------------|-------------|----------|
| 0 | Sem chuva | 0mm × 100% = 0 pontos |
| 1-15 | Chuva fraca | 3mm × 100% = 10 pontos, garoa certa |
| 16-35 | Chuva moderada | 10mm × 60% = 20 pontos |
| 36-60 | Chuva forte | 15mm × 80% = 40 pontos |
| 61-100 | Chuva intensa | 30mm × 100% = 100 pontos, chuva forte garantida |

### Vantagens da Métrica Composta

✅ **Resolve "100% probabilidade mas 0mm"**: Retorna 0 pontos quando não há volume real  
✅ **Representa intensidade real**: Combina chance + quantidade de chuva  
✅ **Threshold 30mm/h**: Permite melhor distribuição visual de chuvas fortes  
✅ **Escala intuitiva**: 0-100 mantém compatibilidade com UI existente  
✅ **Cap em 100**: Chuvas extremas não quebram interface

### Campos Relacionados na API

- **`rainfallIntensity`**: Métrica composta (volume × probabilidade) - **usar para visualização principal**
- **`rainfallProbability`**: Probabilidade pura 0-100% - **exibir no painel de detalhes**
- **`rainVolumeHour`**: Volume puro em mm/h - usar para alertas técnicos
- **`dailyRainAccumulation`**: Total de chuva acumulada esperada no dia (mm) - **soma de todos os períodos de 3h do dia**

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
- **Details**: `{ "rainMmH": 1.5, "probabilityPercent": 75.0, "rainEndsAt": "2025-11-27T18:00:00-03:00" }`
- **Uso**: Informar sobre chuva muito leve que não interfere em atividades

#### LIGHT_RAIN
- **Código**: `LIGHT_RAIN`
- **Severidade**: `info`
- **Descrição**: 🌧️ Chuva fraca
- **Limiar**: 2.5-10 mm/h
- **Details**: `{ "rainMmH": 5.0, "probabilityPercent": 80.0, "rainEndsAt": "2025-11-27T19:00:00-03:00" }`
- **Uso**: Chuva leve, guarda-chuva recomendado

#### MODERATE_RAIN
- **Código**: `MODERATE_RAIN`
- **Severidade**: `warning`
- **Descrição**: 🌧️ Chuva moderada
- **Limiar**: 10-50 mm/h
- **Details**: `{ "rainMmH": 15.0, "probabilityPercent": 85.0, "rainEndsAt": "2025-11-27T21:00:00-03:00" }`
- **Uso**: Chuva considerável, evitar atividades externas

#### HEAVY_RAIN
- **Código**: `HEAVY_RAIN`
- **Severidade**: `alert`
- **Descrição**: ⚠️ ALERTA: Chuva forte
- **Limiar**: > 50 mm/h
- **Details**: `{ "rainMmH": 65.0, "probabilityPercent": 90.0, "rainEndsAt": "2025-11-28T02:00:00-03:00" }`
- **Uso**: Chuva intensa, risco de alagamentos

#### HEAVY_RAIN_DAY
- **Código**: `HEAVY_RAIN_DAY`
- **Severidade**: `warning` (ou `alert` quando o acumulado diário passa de 50mm)
- **Descrição**: Chuva forte prevista
- **Limiar**: Acumulado diário > 20mm com intensidade composta >= 25 (usa previsão diária)
- **Details**: `{ "date": "2025-11-27", "precipitationMm": 32.0, "probabilityPercent": 75.0 }`
- **Uso**: Destaca dias com volume alto; exibe apenas acumulado diário e probabilidade

#### RAIN_EXPECTED
- **Código**: `RAIN_EXPECTED`
- **Severidade**: `info`
- **Descrição**: 🌧️ Alta probabilidade de chuva
- **Limiar**: Códigos de chuva leve (500-501, 520-521, etc) com probabilidade ≥ 80% mas sem volume medido
- **Details**: `{ "weatherCode": 500, "probabilityPercent": 85.0 }`
- **Uso**: Avisar usuário para levar guarda-chuva quando API indica código de chuva mas não retorna volume
- **Nota**: Gerado apenas quando há código de chuva (500-599) exceto chuva forte, probabilidade alta, mas volume = 0

### ⛈️ Tempestade

#### STORM
- **Código**: `STORM`
- **Severidade**: `danger`
- **Descrição**: ⚠️ ALERTA: Tempestade com raios
- **Condição**: Códigos OpenWeather 200, 201, 202, 210, 211, 212, 221
- **Details**: `{ "weatherCode": 210, "rainMmH": 20.0, "probabilityPercent": 95.0, "rainEndsAt": "2025-11-28T00:00:00-03:00" }`
- **Uso**: Perigo de raios, buscar abrigo imediatamente

#### STORM_RAIN
- **Código**: `STORM_RAIN`
- **Severidade**: `alert`
- **Descrição**: ⚠️ Tempestade com chuva
- **Condição**: Outros códigos 2xx
- **Details**: `{ "weatherCode": 231, "rainMmH": 15.0, "probabilityPercent": 85.0, "rainEndsAt": "2025-11-27T23:00:00-03:00" }`
- **Uso**: Tempestade menos intensa, mas ainda requer cuidado

### 💨 Vento

#### MODERATE_WIND
- **Código**: `MODERATE_WIND`
- **Severidade**: `info`
- **Descrição**: 💨 Ventos moderados
- **Limiar**: 30-49 km/h
- **Details**: `{ "windSpeedKmh": 35.0 }`
- **Uso**: Informar sobre vento perceptível

#### STRONG_WIND
- **Código**: `STRONG_WIND`
- **Severidade**: `alert`
- **Descrição**: 💨 ALERTA: Ventos fortes
- **Limiar**: ≥ 50 km/h
- **Details**: `{ "windSpeedKmh": 65.0 }`
- **Uso**: Vento forte, cuidado com objetos soltos e árvores

### 🌡️ Temperatura

#### COLD
- **Código**: `COLD`
- **Severidade**: `alert`
- **Descrição**: 🧊 Frio
- **Limiar**: < 12°C
- **Details**: `{ "temperatureC": 11.0 }`
- **Uso**: Temperatura baixa para padrões brasileiros, agasalhos recomendados

#### VERY_COLD
- **Código**: `VERY_COLD`
- **Severidade**: `danger`
- **Descrição**: 🥶 ALERTA: Frio intenso
- **Limiar**: < 8°C
- **Details**: `{ "temperatureC": 6.0 }`
- **Uso**: Frio extremo para Brasil, proteção extra necessária

#### TEMP_DROP
- **Código**: `TEMP_DROP`
- **Severidade**: `warning`
- **Descrição**: 🌡️ Queda de temperatura (X°C em Y dias)
- **Limiar**: Variação > 8°C entre quaisquer dias da previsão (não apenas consecutivos)
- **Details**: 
```json
{
  "day1Date": "2025-11-27",
  "day1MaxC": 28.0,
  "day2Date": "2025-11-29",
  "day2MaxC": 15.0,
  "variationC": -13.0,
  "daysBetween": 2
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
  "day1Date": "2025-11-27",
  "day1MaxC": 18.0,
  "day2Date": "2025-11-30",
  "day2MaxC": 28.0,
  "variationC": 10.0,
  "daysBetween": 3
}
```
- **Uso**: Informar sobre aquecimento significativo. O sistema compara todos os pares de dias e retorna apenas o maior aumento detectado.

### ❄️ Neve

#### SNOW
- **Código**: `SNOW`
- **Severidade**: `info`
- **Descrição**: ❄️ Neve (raro no Brasil)
- **Condição**: Códigos OpenWeather 600-699
- **Details**: `{ "weatherCode": 600, "temperatureC": 0.5 }`
- **Uso**: Evento raro, principalmente em regiões serranas do Sul

### 🌫️ Visibilidade

#### LOW_VISIBILITY
- **Código**: `LOW_VISIBILITY`
- **Severidade**: `alert` (< 1km) ou `warning` (< 3km)
- **Descrição**: 🌫️ ALERTA: Visibilidade reduzida
- **Limiar**: < 3000 metros
- **Details**: `{ "visibilityMeters": 500 }`
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
        "rainMmH": 18.5,
        "probabilityPercent": 85.0,
        "rainEndsAt": "2025-11-27T21:00:00-03:00"
      }
    },
    {
      "code": "STRONG_WIND",
      "severity": "alert",
      "description": "💨 ALERTA: Ventos fortes",
      "timestamp": "2025-11-27T18:00:00-03:00",
      "details": {
        "windSpeedKmh": 55.0
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
        "rainMmH": 60.0,
        "probabilityPercent": 90.0,
        "rainEndsAt": "2025-11-28T02:00:00-03:00"
      }
    },
    {
      "code": "STORM",
      "severity": "danger",
      "description": "⚠️ ALERTA: Tempestade com raios",
      "timestamp": "2025-11-27T21:00:00-03:00",
      "details": {
        "weatherCode": 210,
        "rainMmH": 65.0,
        "probabilityPercent": 95.0,
        "rainEndsAt": "2025-11-28T00:00:00-03:00"
      }
    },
    {
      "code": "STRONG_WIND",
      "severity": "alert",
      "description": "💨 ALERTA: Ventos fortes",
      "timestamp": "2025-11-27T21:00:00-03:00",
      "details": {
        "windSpeedKmh": 70.0
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
        "day1Date": "2025-11-27",
        "day1MaxC": 28.0,
        "day2Date": "2025-11-29",
        "day2MaxC": 15.0,
        "variationC": -13.0,
        "daysBetween": 2
      }
    },
    {
      "code": "COLD",
      "severity": "alert",
      "description": "🧊 Frio",
      "timestamp": "2025-11-28T06:00:00-03:00",
      "details": {
        "temperatureC": 11.0
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
  
  if (details.rainMmH) {
    extraInfo.push(`${details.rainMmH} mm/h`);
  }
  if (details.probabilityPercent) {
    extraInfo.push(`${details.probabilityPercent}% chance`);
  }
  if (details.rainEndsAt) {
    const endTime = new Date(details.rainEndsAt);
    extraInfo.push(`até ${endTime.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`);
  }
  if (details.visibilityMeters) {
    extraInfo.push(`visibilidade ${details.visibilityMeters}m`);
  }
  if (details.windSpeedKmh) {
    extraInfo.push(`${details.windSpeedKmh} km/h`);
  }
  if (details.temperatureC !== undefined) {
    extraInfo.push(`${details.temperatureC}°C`);
  }
  if (details.variationC) {
    extraInfo.push(`variação de ${Math.abs(details.variationC)}°C`);
  }
  if (details.daysBetween) {
    extraInfo.push(`${details.daysBetween} ${details.daysBetween === 1 ? 'dia' : 'dias'}`);
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
