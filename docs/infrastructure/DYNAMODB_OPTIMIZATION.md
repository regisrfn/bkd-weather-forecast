# Otimização de Performance - DynamoDB Cache

## 📊 Diagnóstico Atual

### Métricas Observadas
- **Tabela:** `weather-forecast-cache-prod`
- **Billing Mode:** PAY_PER_REQUEST (On-Demand)
- **Item Count:** 276 items
- **Table Size:** 4.4 MB

### Performance Atual
| Métrica | Valor | Status |
|---------|-------|--------|
| Leitura Média | 148ms | ⚠️ Razoável |
| Escrita Média | 178ms | ⚠️ Razoável |
| **P99 Leitura** | **237ms** | ❌ Alto |
| **P99 Escrita** | **537ms** | ❌ Muito Alto |
| Throughput Paralelo | 11.8 ops/s | ❌ Baixo |
| Cache Hit Rate | 100% | ✅ Excelente |

### Problema Identificado
**Latências altas no P99 (percentil 99):**
- 1% das escritas levam >537ms
- 1% das leituras levam >237ms
- **Impacto:** Em requisições com 100 cidades, se 1 cidade demora 4s, toda a requisição demora 4s

---

## 🔧 Soluções Recomendadas

### Solução 1: Mudar para Provisioned Capacity (Recomendado para Produção)

**Vantagens:**
- ✅ Latência consistente e previsível
- ✅ Elimina cold starts
- ✅ Performance garantida
- ✅ Custo previsível

**Desvantagens:**
- ❌ Custo fixo (mesmo sem uso)
- ❌ Precisa gerenciar capacidade

**Implementação:**

```hcl
# terraform/modules/dynamodb/main.tf
resource "aws_dynamodb_table" "cache" {
  name           = var.table_name
  billing_mode   = "PROVISIONED"
  read_capacity  = 10  # 10 RCU = 10 leituras/s de até 4KB
  write_capacity = 5   # 5 WCU = 5 escritas/s de até 1KB
  
  hash_key = "cityId"
  
  attribute {
    name = "cityId"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Auto Scaling (recomendado)
  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
  }
  
  tags = var.tags
}

# Auto Scaling para Read Capacity
resource "aws_appautoscaling_target" "dynamodb_read" {
  max_capacity       = 100  # Máximo 100 RCU
  min_capacity       = 5    # Mínimo 5 RCU
  resource_id        = "table/${aws_dynamodb_table.cache.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "dynamodb_read_policy" {
  name               = "${var.table_name}-read-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.dynamodb_read.resource_id
  scalable_dimension = aws_appautoscaling_target.dynamodb_read.scalable_dimension
  service_namespace  = aws_appautoscaling_target.dynamodb_read.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = 70.0  # Escalar quando uso atingir 70%
  }
}

# Auto Scaling para Write Capacity
resource "aws_appautoscaling_target" "dynamodb_write" {
  max_capacity       = 50   # Máximo 50 WCU
  min_capacity       = 5    # Mínimo 5 WCU
  resource_id        = "table/${aws_dynamodb_table.cache.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "dynamodb_write_policy" {
  name               = "${var.table_name}-write-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.dynamodb_write.resource_id
  scalable_dimension = aws_appautoscaling_target.dynamodb_write.scalable_dimension
  service_namespace  = aws_appautoscaling_target.dynamodb_write.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = 70.0
  }
}
```

**Estimativa de Custo:**
- Provisioned: 5 RCU + 5 WCU = ~$3/mês (sa-east-1)
- Com Auto Scaling: $3-15/mês (dependendo do tráfego)
- On-Demand atual: Variável, pode ser mais caro com tráfego alto

---

### Solução 2: Aumentar Connection Pool do aioboto3

**Benefício:** Reduz latência de conexões simultâneas

```python
# lambda/infrastructure/adapters/cache/async_dynamodb_cache.py

from botocore.config import Config

# Na inicialização do DynamoDB client
config = Config(
    region_name=self.region_name,
    max_pool_connections=100,  # Aumentar de 10 (default) para 100
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)

async with session.client('dynamodb', config=config) as dynamodb:
    # ...
```

**Impacto esperado:**
- ✅ Redução de 20-30% na latência paralela
- ✅ Melhor handling de burst de requisições

---

### Solução 3: Implementar DAX (DynamoDB Accelerator)

**Quando usar:**
- Tráfego muito alto (>1000 req/s)
- Orçamento permite ($200+/mês)
- Latência crítica (<10ms P99)

**Características:**
- ✅ Cache em memória (microsegundos)
- ✅ P99 < 10ms
- ❌ Custo alto (~$200/mês por nó)
- ❌ Complexidade adicional

**Não recomendado no momento** - PAY_PER_REQUEST com auto-scaling é suficiente.

---

### Solução 4: Batch Operations Otimizadas

**Implementação atual:** BatchGetItem já está implementado ✅

**Otimizações adicionais:**

```python
async def batch_get_optimized(
    self,
    city_ids: List[str],
    max_retries: int = 3
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Batch GET otimizado com retry e chunking
    """
    if not city_ids:
        return {}
    
    # Dividir em chunks de 100 (limite do BatchGetItem)
    chunks = [city_ids[i:i+100] for i in range(0, len(city_ids), 100)]
    
    all_results = {}
    
    for chunk in chunks:
        for attempt in range(max_retries):
            try:
                results = await self._batch_get_chunk(chunk)
                all_results.update(results)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Batch GET failed after {max_retries} retries", error=str(e))
                else:
                    await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
    
    return all_results
```

---

## 📈 Plano de Ação Recomendado

### Curto Prazo (Implementar Agora)

1. **✅ Aumentar Connection Pool**
   ```python
   max_pool_connections=100
   ```
   - Tempo: 5 minutos
   - Custo: $0
   - Impacto: Redução de 20-30% na latência

2. **✅ Adicionar CloudWatch Alarms**
   ```hcl
   # Alarme para latência alta
   resource "aws_cloudwatch_metric_alarm" "cache_latency" {
     alarm_name          = "dynamodb-cache-high-latency"
     comparison_operator = "GreaterThanThreshold"
     evaluation_periods  = 2
     metric_name         = "SuccessfulRequestLatency"
     namespace           = "AWS/DynamoDB"
     period              = 60
     statistic           = "Average"
     threshold           = 100  # 100ms
     alarm_description   = "Cache latency above 100ms"
     
     dimensions = {
       TableName = var.table_name
       Operation = "GetItem"
     }
   }
   ```

### Médio Prazo (Próxima Sprint)

3. **🔄 Migrar para Provisioned Capacity com Auto Scaling**
   - Tempo: 30 minutos
   - Custo: +$3-10/mês
   - Impacto: Latência consistente, P99 < 50ms

4. **📊 Implementar Métricas Customizadas**
   ```python
   # Adicionar métricas ao CloudWatch
   from aws_lambda_powertools.metrics import Metrics
   
   metrics = Metrics()
   metrics.add_metric(name="CacheLatency", unit="Milliseconds", value=latency_ms)
   metrics.add_metric(name="CacheHitRate", unit="Percent", value=hit_rate)
   ```

### Longo Prazo (Se Necessário)

5. **🚀 Considerar DAX** (apenas se P99 > 100ms após otimizações)
   - Custo: +$200/mês
   - Impacto: P99 < 10ms

---

## 🎯 Resultados Esperados Após Otimizações

| Métrica | Atual | Após Otimização | Melhoria |
|---------|-------|-----------------|----------|
| P99 Leitura | 237ms | <50ms | 79% |
| P99 Escrita | 537ms | <80ms | 85% |
| Throughput | 11.8 ops/s | >50 ops/s | 323% |
| Latência Média | 148ms | <30ms | 80% |

**Impacto no endpoint regional (100 cidades):**
- Atual: 9-15 segundos
- Após otimização: <3 segundos
- **Melhoria: 70-80% mais rápido**

---

## 📚 Referências

- [DynamoDB Provisioned Capacity](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html)
- [DynamoDB Auto Scaling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html)
- [DAX Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)
- [aioboto3 Configuration](https://aioboto3.readthedocs.io/en/latest/usage.html)
