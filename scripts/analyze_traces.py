#!/usr/bin/env python3
"""
Script para análise de traces do sistema de observabilidade.
Gera relatório markdown organizado por @trace_operation.
"""

import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

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
    """Calcula estatísticas de performance por span."""
    span_durations = defaultdict(list)
    span_traces = defaultdict(set)
    
    for trace_id, trace_logs in traces.items():
        # Agrupar logs do trace por span_name
        span_groups = defaultdict(list)
        for log in trace_logs:
            span_name = log.get('span_name')
            if span_name:
                span_groups[span_name].append(log)
                span_traces[span_name].add(trace_id)
        
        # Calcular duração de cada span no trace
        for span_name, span_logs_in_trace in span_groups.items():
            if len(span_logs_in_trace) >= 2:
                first_log = min(span_logs_in_trace, key=lambda x: x['timestamp'])
                last_log = max(span_logs_in_trace, key=lambda x: x['timestamp'])
                
                t1 = datetime.fromisoformat(first_log['timestamp'].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(last_log['timestamp'].replace('Z', '+00:00'))
                
                duration_ms = (t2 - t1).total_seconds() * 1000
                span_durations[span_name].append(duration_ms)
    
    # Calcular estatísticas
    stats = {}
    for span_name in span_durations:
        durations = span_durations[span_name]
        if durations:
            stats[span_name] = {
                'count': len(durations),
                'traces': len(span_traces[span_name]),
                'avg': sum(durations) / len(durations),
                'min': min(durations),
                'max': max(durations),
                'total': sum(durations)
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
            
            md.append(f"{i}. [{timestamp.strftime('%H:%M:%S.%f')[:-3]}] **[{span}]** {level}: {msg}")
        
        md.append("")
    
    return '\n'.join(md)

def main():
    """Função principal."""
    input_file = '/tmp/observability_logs_new.json'
    output_file = '/tmp/trace_analysis_new.md'
    
    print("🔄 Carregando logs...")
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
