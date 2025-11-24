#!/usr/bin/env python3
"""
Script de teste de performance com 100 cidades
Invoca POST /api/weather/regional e mede métricas de performance
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

# Adicionar lambda ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

def load_test_cities(limit=100):
    """Carrega IDs das primeiras N cidades do arquivo de teste"""
    test_file = Path(__file__).parent.parent / 'lambda' / 'data' / 'test_100_municipalities.json'
    
    with open(test_file, 'r', encoding='utf-8') as f:
        municipalities = json.load(f)
    
    city_ids = [m['id'] for m in municipalities[:limit]]
    return city_ids


def run_performance_test(api_url, city_ids):
    """
    Executa teste de performance invocando API
    
    Returns:
        dict: Resultados do teste com métricas detalhadas
    """
    print(f"\n{'='*70}")
    print(f"🚀 TESTE DE PERFORMANCE - {len(city_ids)} CIDADES")
    print(f"{'='*70}")
    print(f"API URL: {api_url}")
    print(f"Cidades: {len(city_ids)}")
    print(f"{'='*70}\n")
    
    # Preparar payload
    print("⏳ Preparando payload...")
    prep_start = time.time()
    payload = {'cityIds': city_ids}
    payload_json = json.dumps(payload)
    prep_time = time.time() - prep_start
    print(f"   Payload preparado em {prep_time*1000:.2f}ms ({len(payload_json)} bytes)")
    
    # Medir tempo de resposta com checkpoints
    print("\n⏳ Enviando requisição HTTP...")
    request_start = time.time()
    start_timestamp = datetime.now().isoformat()
    
    try:
        # Tempo de conexão + envio
        conn_start = time.time()
        response = requests.post(
            f"{api_url}/api/weather/regional",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=180  # 3 minutos timeout
        )
        request_time = time.time() - conn_start
        
        # Tempo de parsing
        parse_start = time.time()
        lambda_request_id = response.headers.get('x-amzn-RequestId', 'unknown')
        status_code = response.status_code
        
        # Parse response
        if status_code == 200:
            data = response.json()
            cities_returned = len(data) if isinstance(data, list) else 0
        else:
            data = None
            cities_returned = 0
        parse_time = time.time() - parse_start
        
        total_time = time.time() - request_start
        
        # Compilar resultados com breakdown de tempo
        results = {
            'test_timestamp': start_timestamp,
            'test_type': 'baseline',
            'api_url': api_url,
            'cities_requested': len(city_ids),
            'cities_returned': cities_returned,
            'status_code': status_code,
            'timings': {
                'prep_ms': round(prep_time * 1000, 2),
                'request_ms': round(request_time * 1000, 2),
                'parse_ms': round(parse_time * 1000, 2),
                'total_ms': round(total_time * 1000, 2),
                'total_seconds': round(total_time, 3)
            },
            'payload_size_bytes': len(payload_json),
            'lambda_request_id': lambda_request_id,
            'success': status_code == 200,
            'error': None if status_code == 200 else response.text[:500]
        }
        
        # Print resultado com breakdown
        print(f"\n{'='*70}")
        print(f"📊 RESULTADOS")
        print(f"{'='*70}")
        print(f"✅ Status: {status_code}")
        print(f"⏱️  Breakdown de tempo:")
        print(f"   - Preparação: {results['timings']['prep_ms']:.2f}ms")
        print(f"   - Request HTTP: {results['timings']['request_ms']:.2f}ms")
        print(f"   - Parse resposta: {results['timings']['parse_ms']:.2f}ms")
        print(f"   - TOTAL: {results['timings']['total_ms']:.2f}ms ({results['timings']['total_seconds']:.3f}s)")
        print(f"🏙️  Cidades processadas: {cities_returned}/{len(city_ids)}")
        print(f"📝 Lambda Request ID: {lambda_request_id}")
        
        if status_code == 200:
            # Estatísticas
            avg_per_city_ms = results['timings']['total_ms'] / len(city_ids) if city_ids else 0
            throughput = len(city_ids) / results['timings']['total_seconds'] if results['timings']['total_seconds'] > 0 else 0
            print(f"📊 Tempo médio por cidade: {avg_per_city_ms:.2f}ms")
            print(f"🚀 Throughput: {throughput:.2f} cidades/segundo")
        else:
            print(f"❌ Erro: {results['error']}")
        
        return results
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - request_start
        print(f"\n⏰ TIMEOUT após {elapsed:.1f}s")
        return {
            'test_timestamp': start_timestamp,
            'test_type': 'baseline',
            'api_url': api_url,
            'cities_requested': len(city_ids),
            'cities_returned': 0,
            'status_code': 0,
            'timings': {
                'prep_ms': round(prep_time * 1000, 2),
                'request_ms': round(elapsed * 1000, 2),
                'parse_ms': 0,
                'total_ms': round(elapsed * 1000, 2),
                'total_seconds': round(elapsed, 3)
            },
            'payload_size_bytes': len(payload_json),
            'lambda_request_id': 'timeout',
            'success': False,
            'error': f'Request timeout after {elapsed:.1f}s (limit: 180s)'
        }
    
    except Exception as e:
        elapsed = time.time() - request_start
        print(f"\n❌ ERRO: {e}")
        return {
            'test_timestamp': start_timestamp,
            'test_type': 'baseline',
            'api_url': api_url,
            'cities_requested': len(city_ids),
            'cities_returned': 0,
            'status_code': 0,
            'timings': {
                'prep_ms': round(prep_time * 1000, 2) if 'prep_time' in locals() else 0,
                'request_ms': round(elapsed * 1000, 2),
                'parse_ms': 0,
                'total_ms': round(elapsed * 1000, 2),
                'total_seconds': round(elapsed, 3)
            },
            'payload_size_bytes': len(payload_json) if 'payload_json' in locals() else 0,
            'lambda_request_id': 'error',
            'success': False,
            'error': str(e)
        }


def save_results(results, output_dir='output'):
    """Salva resultados em arquivo JSON"""
    output_path = Path(__file__).parent.parent / output_dir
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_{results['test_type']}_{timestamp}.json"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados salvos: {filepath}")
    return filepath


def main():
    # Carregar API URL
    api_url_file = Path(__file__).parent.parent / 'API_URL.txt'
    
    if not api_url_file.exists():
        print("❌ Arquivo API_URL.txt não encontrado!")
        print("Execute deploy primeiro: bash scripts/deploy-main.sh")
        sys.exit(1)
    
    with open(api_url_file, 'r') as f:
        api_url = f.read().strip()
    
    # Carregar cidades de teste
    city_ids = load_test_cities(limit=100)
    
    # Executar teste
    results = run_performance_test(api_url, city_ids)
    
    # Salvar resultados
    save_results(results)
    
    print(f"\n{'='*70}")
    if results['success']:
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
    else:
        print("❌ TESTE FALHOU")
    print(f"{'='*70}\n")
    
    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
