#!/usr/bin/env python3
"""
Análise de Performance do Cache DynamoDB
Mede latência de leitura/escrita e identifica gargalos
"""
import asyncio
import time
import statistics
from datetime import datetime, timedelta
import aioboto3
import os
import sys

# Adicionar path do projeto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from infrastructure.adapters.cache.async_dynamodb_cache import AsyncDynamoDBCache
import shared.config.settings as settings


async def test_cache_performance(num_operations: int = 100):
    """Testa performance do cache DynamoDB"""
    
    print("="*70)
    print("🔍 ANÁLISE DE PERFORMANCE - DYNAMODB CACHE")
    print("="*70)
    print(f"Tabela: {settings.CACHE_TABLE_NAME}")
    print(f"Região: {settings.AWS_REGION}")
    print(f"Operações: {num_operations}")
    print("="*70)
    
    cache = AsyncDynamoDBCache()
    
    # Teste 1: Write Performance - SEQUENCIAL
    print("\n📝 Teste 1: Performance de ESCRITA SEQUENCIAL")
    print("-" * 70)
    
    write_times = []
    test_data = {
        'temperature': 25.5,
        'humidity': 60,
        'windSpeed': 10.5,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    for i in range(num_operations):
        city_id = f"test_city_{i}"
        start = time.perf_counter()
        await cache.set(city_id, test_data, ttl_seconds=3600)
        elapsed = (time.perf_counter() - start) * 1000
        write_times.append(elapsed)
        
        if i % 20 == 0:
            print(f"  Progresso: {i}/{num_operations} - Última: {elapsed:.2f}ms")
    
    print(f"\n✅ Escritas sequenciais completadas:")
    print(f"  • Média: {statistics.mean(write_times):.2f}ms")
    print(f"  • Mediana: {statistics.median(write_times):.2f}ms")
    print(f"  • Min: {min(write_times):.2f}ms")
    print(f"  • Max: {max(write_times):.2f}ms")
    print(f"  • P95: {statistics.quantiles(write_times, n=20)[18]:.2f}ms")
    print(f"  • P99: {statistics.quantiles(write_times, n=100)[98]:.2f}ms")
    print(f"  • Tempo total: {sum(write_times):.2f}ms")
    print(f"  • Throughput: {(num_operations / sum(write_times)) * 1000:.1f} ops/s")
    
    # Teste 2: Read Performance (Cache Hit) - SEQUENCIAL
    print("\n📖 Teste 2: Performance de LEITURA SEQUENCIAL (Cache Hit)")
    print("-" * 70)
    
    read_times = []
    hits = 0
    
    for i in range(num_operations):
        city_id = f"test_city_{i}"
        start = time.perf_counter()
        result = await cache.get(city_id)
        elapsed = (time.perf_counter() - start) * 1000
        read_times.append(elapsed)
        
        if result:
            hits += 1
        
        if i % 20 == 0:
            print(f"  Progresso: {i}/{num_operations} - Última: {elapsed:.2f}ms")
    
    hit_rate = (hits / num_operations) * 100
    
    print(f"\n✅ Leituras sequenciais completadas:")
    print(f"  • Cache Hit Rate: {hit_rate:.1f}% ({hits}/{num_operations})")
    print(f"  • Média: {statistics.mean(read_times):.2f}ms")
    print(f"  • Mediana: {statistics.median(read_times):.2f}ms")
    print(f"  • Min: {min(read_times):.2f}ms")
    print(f"  • Max: {max(read_times):.2f}ms")
    print(f"  • P95: {statistics.quantiles(read_times, n=20)[18]:.2f}ms")
    print(f"  • P99: {statistics.quantiles(read_times, n=100)[98]:.2f}ms")
    print(f"  • Tempo total: {sum(read_times):.2f}ms")
    print(f"  • Throughput: {(num_operations / sum(read_times)) * 1000:.1f} ops/s")
    
    # Teste 3: Parallel Reads (Simula carga real)
    print("\n⚡ Teste 3: Performance PARALELA (100 leituras simultâneas)")
    print("-" * 70)
    
    city_ids = [f"test_city_{i}" for i in range(100)]
    
    start_parallel = time.perf_counter()
    tasks = [cache.get(city_id) for city_id in city_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed_parallel = (time.perf_counter() - start_parallel) * 1000
    
    successes = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
    errors = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"\n✅ Leituras paralelas completadas:")
    print(f"  • Tempo total: {elapsed_parallel:.2f}ms")
    print(f"  • Throughput: {(100 / elapsed_parallel) * 1000:.1f} ops/s")
    print(f"  • Latência média por operação: {elapsed_parallel/100:.2f}ms")
    print(f"  • Sucessos: {successes}/100")
    print(f"  • Erros: {errors}/100")
    
    # Teste 4: Cache Miss Performance
    print("\n❌ Teste 4: Performance de CACHE MISS")
    print("-" * 70)
    
    miss_times = []
    
    for i in range(20):
        city_id = f"nonexistent_city_{i}"
        start = time.perf_counter()
        result = await cache.get(city_id)
        elapsed = (time.perf_counter() - start) * 1000
        miss_times.append(elapsed)
    
    print(f"\n✅ Cache Misses completados:")
    print(f"  • Média: {statistics.mean(miss_times):.2f}ms")
    print(f"  • Mediana: {statistics.median(miss_times):.2f}ms")
    print(f"  • Min: {min(miss_times):.2f}ms")
    print(f"  • Max: {max(miss_times):.2f}ms")
    
    # Cleanup
    print("\n🧹 Limpando dados de teste...")
    delete_tasks = [cache.delete(f"test_city_{i}") for i in range(num_operations)]
    await asyncio.gather(*delete_tasks, return_exceptions=True)
    print("✅ Cleanup completado")
    
    # Análise Final
    print("\n" + "="*70)
    print("📊 ANÁLISE FINAL")
    print("="*70)
    
    # Comparar leituras vs escritas
    read_avg = statistics.mean(read_times)
    write_avg = statistics.mean(write_times)
    read_total = sum(read_times)
    write_total = sum(write_times)
    
    print(f"\n1. Comparação SEQUENCIAL Leitura vs Escrita:")
    print(f"   • Leitura: {read_avg:.2f}ms (média), {read_total:.2f}ms (total)")
    print(f"   • Escrita: {write_avg:.2f}ms (média), {write_total:.2f}ms (total)")
    print(f"   • Diferença média: {abs(read_avg - write_avg):.2f}ms")
    print(f"   • Throughput leitura: {(num_operations / read_total) * 1000:.1f} ops/s")
    print(f"   • Throughput escrita: {(num_operations / write_total) * 1000:.1f} ops/s")
    
    # Identificar outliers
    read_p99 = statistics.quantiles(read_times, n=100)[98]
    write_p99 = statistics.quantiles(write_times, n=100)[98]
    
    print(f"\n2. Outliers (P99):")
    print(f"   • Leitura P99: {read_p99:.2f}ms")
    print(f"   • Escrita P99: {write_p99:.2f}ms")
    
    if read_p99 > 100:
        print(f"   ⚠️  ALERTA: P99 de leitura está alto (>{read_p99:.0f}ms)")
        print(f"      Possíveis causas:")
        print(f"      - Throttling do DynamoDB (PAY_PER_REQUEST)")
        print(f"      - Cold start da conexão")
        print(f"      - Latência de rede")
    
    if write_p99 > 100:
        print(f"   ⚠️  ALERTA: P99 de escrita está alto (>{write_p99:.0f}ms)")
    
    print(f"\n3. Performance Paralela:")
    print(f"   • Throughput: {(100 / elapsed_parallel) * 1000:.1f} ops/s")
    
    if elapsed_parallel / 100 > 50:
        print(f"   ⚠️  ALERTA: Latência paralela alta ({elapsed_parallel/100:.1f}ms/op)")
        print(f"      Considere:")
        print(f"      - Mudar para Provisioned Capacity")
        print(f"      - Aumentar connection pool do aioboto3")
        print(f"      - Usar DAX (DynamoDB Accelerator)")
    else:
        print(f"   ✅ Latência paralela OK ({elapsed_parallel/100:.1f}ms/op)")
    
    print("\n" + "="*70)
    
    await cache.cleanup()


async def check_table_metrics():
    """Verifica métricas da tabela DynamoDB"""
    print("\n📊 MÉTRICAS DA TABELA DYNAMODB")
    print("="*70)
    
    session = aioboto3.Session()
    async with session.client('dynamodb', region_name=settings.AWS_REGION) as dynamodb:
        try:
            response = await dynamodb.describe_table(TableName=settings.CACHE_TABLE_NAME)
            table = response['Table']
            
            print(f"Nome: {table['TableName']}")
            print(f"Status: {table['TableStatus']}")
            print(f"Item Count: {table.get('ItemCount', 'N/A'):,}")
            print(f"Size: {table.get('TableSizeBytes', 0) / 1024 / 1024:.2f} MB")
            
            if 'BillingModeSummary' in table:
                billing = table['BillingModeSummary']['BillingMode']
                print(f"Billing Mode: {billing}")
                
                if billing == 'PAY_PER_REQUEST':
                    print("\n⚠️  Usando PAY_PER_REQUEST (On-Demand)")
                    print("   Vantagens: Sem gerenciamento de capacidade")
                    print("   Desvantagens: Pode ter latências maiores em cold start")
                    print("   Recomendação: OK para tráfego variável")
            
            if 'ProvisionedThroughput' in table:
                pt = table['ProvisionedThroughput']
                if pt.get('ReadCapacityUnits', 0) > 0:
                    print(f"Read Capacity: {pt['ReadCapacityUnits']} RCU")
                    print(f"Write Capacity: {pt['WriteCapacityUnits']} WCU")
            
        except Exception as e:
            print(f"❌ Erro ao obter métricas: {e}")
    
    print("="*70)


if __name__ == '__main__':
    print("\n🚀 Iniciando análise de performance do cache...\n")
    
    asyncio.run(check_table_metrics())
    asyncio.run(test_cache_performance(num_operations=100))
    
    print("\n✅ Análise completada!\n")
