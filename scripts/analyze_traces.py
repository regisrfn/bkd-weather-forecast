#!/usr/bin/env python3
"""
Script para análise de traces do sistema de observabilidade.
Gera relatório markdown organizado por @trace_operation.
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List, Any

# Configurações
OBSERVABILITY_API_URL = "https://4w4dmecaff.execute-api.sa-east-1.amazonaws.com/dev"
SERVICE_NAME = "api-lambda-weather-forecast"
TIME_WINDOW_MINUTES = 15  # Buscar logs dos últimos N minutos

def fetch_logs_from_api(minutes: int = TIME_WINDOW_MINUTES) -> List[Dict[str, Any]]:
    """Busca logs da API de observabilidade."""
    print(f"🔄 Buscando logs dos últimos {minutes} minutos...")
    
    # Calcular janela de tempo
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)
    
    start_time = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Construir URL
    url = f"{OBSERVABILITY_API_URL}/logs/query"
    url += f"?service_name={SERVICE_NAME}"
    url += f"&start_time={start_time}"
    url += f"&end_time={end_time}"
    url += "&limit=1000"
    
    print(f"   Período: {start_time} → {end_time}")
    
    # Fazer requisição usando curl
    try:
        result = subprocess.run(
            ['curl', '-s', url],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Erro ao buscar logs: {result.stderr}")
            return []
        
        data = json.loads(result.stdout)
        logs = data.get('logs', [])
        
        print(f"✅ {len(logs)} logs recuperados")
        return logs
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout ao buscar logs")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar resposta JSON: {e}")
        return []
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return []

def load_logs(filepath: str) -> List[Dict[str, Any]]:
    """Carrega logs do arquivo JSON."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get('logs', [])

def filter_app_logs(logs: List[Dict]) -> List[Dict]:
    """Filtra apenas logs de aplicação (remove START, END, REPORT, INIT_START)."""
    app_logs = []
    for log in logs:
        msg = log.get('message', '')
        if not any(msg.startswith(x) for x in ['START', 'END', 'REPORT', 'INIT_START']):
            app_logs.append(log)
    return app_logs

def group_by_trace(logs: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa logs por trace_id."""
    traces = defaultdict(list)
    for log in logs:
        trace_id = log.get('trace_id')
        if trace_id:
            traces[trace_id].append(log)
    
    # Ordenar logs dentro de cada trace por timestamp
    for trace_id in traces:
        traces[trace_id].sort(key=lambda x: x['timestamp'])
    
    return dict(traces)

def group_by_span(logs: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa logs por span_name."""
    spans = defaultdict(list)
    for log in logs:
        span_name = log.get('span_name')
        if span_name:
            spans[span_name].append(log)
    return dict(spans)

def calculate_trace_duration(trace_logs: List[Dict]) -> float:
    """Calcula duração de um trace em ms."""
    if len(trace_logs) < 2:
        return 0.0
    
    first_log = trace_logs[0]
    last_log = trace_logs[-1]
    
    t1 = datetime.fromisoformat(first_log['timestamp'].replace('Z', '+00:00'))
    t2 = datetime.fromisoformat(last_log['timestamp'].replace('Z', '+00:00'))
    
    return (t2 - t1).total_seconds() * 1000

def calculate_span_stats(traces: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Calcula estatísticas de performance por span usando duration_ms da API."""
    span_durations = defaultdict(list)
    span_traces = defaultdict(set)
    span_count = defaultdict(int)
    
    for trace_id, trace_logs in traces.items():
        # Processar cada log e extrair duration_ms
        for log in trace_logs:
            span_name = log.get('span_name')
            if span_name:
                span_traces[span_name].add(trace_id)
                span_count[span_name] += 1
                
                # Usar duration_ms fornecido pela API
                duration_ms = log.get('duration_ms', 0)
                if duration_ms and duration_ms > 0:
                    span_durations[span_name].append(float(duration_ms))
    
    # Calcular estatísticas
    stats = {}
    all_spans = set(span_traces.keys())
    
    for span_name in all_spans:
        durations = span_durations.get(span_name, [])
        stats[span_name] = {
            'count': span_count[span_name],
            'traces': len(span_traces[span_name]),
            'avg': sum(durations) / len(durations) if durations else 0,
            'min': min(durations) if durations else 0,
            'max': max(durations) if durations else 0,
            'total': sum(durations) if durations else 0
        }
    
    return stats

def generate_markdown(logs: List[Dict], traces: Dict, spans: Dict, span_stats: Dict) -> str:
    """Gera relatório markdown."""
    md = []
    
    # Header
    md.append("# 🔍 Análise de Traces - Observability Platform")
    md.append("")
    md.append(f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("")
    
    # Overview
    md.append("## 📊 Overview")
    md.append("")
    md.append(f"- **Total de logs:** {len(logs)}")
    md.append(f"- **Total de traces:** {len(traces)}")
    md.append(f"- **Total de spans:** {len(spans)}")
    md.append(f"- **Média de logs/trace:** {len(logs)/len(traces):.1f}")
    md.append("")
    
    # Análise de Spans (@trace_operation)
    md.append("## 🎯 Análise de Spans (@trace_operation)")
    md.append("")
    
    if span_stats:
        # Tabela de performance
        md.append("### Performance por Span")
        md.append("")
        md.append("| Span | Execuções | Traces | Média (ms) | Min (ms) | Max (ms) | Total (ms) |")
        md.append("|------|-----------|--------|------------|----------|----------|------------|")
        
        for span_name in sorted(span_stats.keys()):
            stats = span_stats[span_name]
            md.append(f"| `{span_name}` | {stats['count']} | {stats['traces']} | "
                     f"{stats['avg']:.2f} | {stats['min']:.2f} | {stats['max']:.2f} | {stats['total']:.2f} |")
        
        md.append("")
        
        # Detalhes por span
        md.append("### Detalhes por Span")
        md.append("")
        
        for span_name in sorted(spans.keys()):
            span_logs = spans[span_name]
            md.append(f"#### 📍 {span_name}")
            md.append("")
            md.append(f"**Total de logs:** {len(span_logs)}")
            
            if span_name in span_stats:
                stats = span_stats[span_name]
                md.append(f"**Execuções:** {stats['count']}")
                md.append(f"**Performance:** {stats['avg']:.2f}ms (min: {stats['min']:.2f}ms, max: {stats['max']:.2f}ms)")
            
            md.append("")
            md.append("**Mensagens:**")
            
            # Mostrar algumas mensagens de exemplo
            unique_messages = set()
            for log in span_logs[:10]:
                msg = log.get('message', '')
                if msg not in unique_messages:
                    unique_messages.add(msg)
                    timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                    md.append(f"- [{timestamp.strftime('%H:%M:%S')}] {msg}")
            
            if len(span_logs) > 10:
                md.append(f"- _(e mais {len(span_logs) - 10} logs...)_")
            
            md.append("")
    
    else:
        md.append("⚠️ Nenhum span detectado nos logs.")
        md.append("")
    
    # Traces Detalhados (primeiros 10)
    md.append("## 🔄 Traces Detalhados")
    md.append("")
    md.append("_Mostrando os primeiros 10 traces com mais logs_")
    md.append("")
    
    # Ordenar traces por número de logs (decrescente)
    sorted_traces = sorted(traces.items(), key=lambda x: len(x[1]), reverse=True)
    
    for idx, (trace_id, trace_logs) in enumerate(sorted_traces[:10], 1):
        duration = calculate_trace_duration(trace_logs)
        
        md.append(f"### Trace #{idx}: `{trace_id[:12]}...`")
        md.append(f"**Duração total:** {duration:.2f}ms | **Logs:** {len(trace_logs)}")
        md.append("")
        
        # Identificar spans neste trace
        trace_spans = set(log.get('span_name') for log in trace_logs if log.get('span_name'))
        if trace_spans:
            md.append(f"**Spans:** {', '.join(f'`{s}`' for s in sorted(trace_spans))}")
            md.append("")
        
        md.append("**Timeline:**")
        for i, log in enumerate(trace_logs, 1):
            timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            span = log.get('span_name', 'N/A')
            msg = log.get('message', '')
            level = log.get('level', 'INFO')
            duration = log.get('duration_ms', 0)
            
            # Adicionar duração se disponível
            duration_str = f" ({duration:.2f}ms)" if duration > 0 else ""
            md.append(f"{i}. [{timestamp.strftime('%H:%M:%S.%f')[:-3]}] **[{span}]** {level}: {msg}{duration_str}")
        
        md.append("")
    
    return '\n'.join(md)

def main():
    """Função principal."""
    import sys
    
    # Verificar se deve usar arquivo ou buscar da API
    use_api = '--api' in sys.argv or '-a' in sys.argv
    
    if use_api or len(sys.argv) == 1:
        # Buscar logs da API (comportamento padrão)
        all_logs = fetch_logs_from_api()
        
        if not all_logs:
            print("⚠️  Nenhum log encontrado. Tente aumentar a janela de tempo.")
            print(f"   Configuração atual: TIME_WINDOW_MINUTES = {TIME_WINDOW_MINUTES}")
            print("   Para usar arquivo: python3 analyze_traces.py <arquivo.json>")
            return
            
        output_file = f'trace_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        
    else:
        # Usar arquivo fornecido
        input_file = sys.argv[1]
        output_file = input_file.replace('.json', '_analysis.md')
        
        print(f"🔄 Carregando logs de {input_file}...")
        all_logs = load_logs(input_file)
    
    print("🔍 Filtrando logs de aplicação...")
    app_logs = filter_app_logs(all_logs)
    
    print("📦 Agrupando por trace_id...")
    traces = group_by_trace(app_logs)
    
    print("🎯 Agrupando por span_name...")
    spans = group_by_span(app_logs)
    
    print("📊 Calculando estatísticas de performance...")
    span_stats = calculate_span_stats(traces)
    
    print("📝 Gerando relatório markdown...")
    markdown = generate_markdown(app_logs, traces, spans, span_stats)
    
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"\n✅ Relatório gerado: {output_file}")
    print(f"📊 {len(traces)} traces analisados")
    print(f"📝 {len(app_logs)} logs processados")
    print(f"🎯 {len(spans)} spans detectados")

if __name__ == '__main__':
    main()
