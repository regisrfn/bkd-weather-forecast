# Códigos de Condição Meteorológica (Proprietários)

Os códigos abaixo são calculados na camada de domínio (`domain/constants.py` → `WeatherCondition.classify_weather_condition`) a partir de intensidade de chuva, precipitação, vento, nuvens, visibilidade e temperatura. Eles substituem códigos genéricos de providers externos para manter consistência entre rotas e previsões.

## Tabela de códigos

| Faixa | Código | Descrição | Quando ocorre (resumo) |
|-------|--------|-----------|------------------------|
| 100–199 | 100 | Céu limpo | Nuvens \< 30% e sem precipitação |
| 200–299 | 200 | Parcialmente nublado | Nuvens 30–59% e sem precipitação |
| 300–349 | 300 | Nublado | Nuvens 60–84% e sem precipitação |
| 350–399 | 350 | Céu encoberto | Nuvens ≥ 85% e sem precipitação |
| 400–499 | 400 | Garoa leve | Intensidade de chuva 5–10 ou precipitação muito baixa |
| 410 | Garoa moderada | Intensidade de chuva 10–15 |
| 420 | Garoa intensa | Intensidade de chuva ≥ 15 (com precipitação baixa) |
| 500–599 | 500 | Chuva leve | Intensidade de chuva 25–30 |
| 510 | Chuva moderada | Intensidade de chuva 30–40 |
| 520 | Chuva forte | Intensidade de chuva 40–60 |
| 530 | Chuva muito forte | Intensidade de chuva ≥ 60 |
| 600–629 | 600 | Tempestade leve | Intensidade ≥ 40 com vento ≥ 30 km/h |
| 610 | Tempestade moderada | Intensidade ≥ 45 ou vento ≥ 45 km/h |
| 620 | Tempestade forte | Intensidade ≥ 55 ou vento ≥ 60 km/h |
| 630+ | Tempestade severa | Intensidade ≥ 70 ou vento ≥ 60 km/h (mais severo) |
| 700–719 | 700 | Neblina leve | Visibilidade \< 3000 m |
| 710 | Neblina | Visibilidade \< 1000 m |
| 720 | Nevoeiro denso | Visibilidade \< 500 m |
| 800 | 800 | Névoa seca | Visibilidade \< 5000 m sem precipitação |
| 900–999 | 900 | Neve leve | Temperatura \< 2 °C com precipitação baixa |
| 910 | Neve moderada | Temperatura \< 2 °C com precipitação moderada |
| 920 | Neve forte | Temperatura \< 2 °C com precipitação alta |

> Observação: valores intermediários são definidos exatamente em `domain/constants.py`. A tabela acima resume os principais degraus e critérios de prioridade.

## Prioridades de classificação (simplificado)
1. **Tempestade**: chuva intensa + vento forte (códigos 600–630).
2. **Chuva**: intensidade ≥ 25 (500–530).
3. **Garoa**: intensidade 5–25 (400–420).
4. **Neblina/Fog**: visibilidade baixa (700–720).
5. **Neve**: temperatura \< 2 °C + precipitação (900–920).
6. **Névoa seca**: visibilidade \< 5000 m sem chuva (800).
7. **Cobertura de nuvens**: define 100/200/300/350 quando não há precipitação relevante.

## Onde é usado
- `Weather`, `HourlyForecast`, `DailyForecast` recalculam `weatherCode`/`description` quando necessário.
- Rotas: `/api/weather/city/{id}`, `/api/weather/city/{id}/detailed`, `/api/weather/regional`.
- Frontend: ícones e descrições se baseiam nesses códigos para manter consistência visual.
