#!/usr/bin/env python3
"""
Script para análise de traces do sistema de observabilidade.
Gera relatório markdown organizado por @trace_operation com gráficos de performance.
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import os

# Visualização
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend sem interface gráfica
    import matplotlib.pyplot as plt
    import numpy as np
    VISUALIZATION_ENABLED = True
except ImportError:
    VISUALIZATION_ENABLED = False
    print("⚠️  matplotlib/numpy não disponível - gráficos desabilitados")
    print("   Para habilitar: pip install matplotlib numpy")

# Configurações
OBSERVABILITY_API_URL = "https://4w4dmecaff.execute-api.sa-east-1.amazonaws.com/dev"
SERVICE_NAME = "api-lambda-weather-forecast"
TIME_WINDOW_MINUTES = 120  # Buscar logs dos últimos N minutos

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

def calculate_span_stats(traces: Dict[str, List[Dict]]) -> Tuple[Dict[str, Dict], Dict[str, List[float]]]:
    """
    Calcula estatísticas de performance por span.
    
    Calcula duração usando diferença de timestamps entre primeiro e último log de cada span.
    Filtra durações zero ao calcular min (quando há apenas 1 log no span).
    
    Returns:
        Tuple[Dict, Dict]: (estatísticas agregadas, durações por span para gráficos)
    """
    span_durations = defaultdict(list)
    span_traces = defaultdict(set)
    span_executions = defaultdict(int)
    
    for trace_id, trace_logs in traces.items():
        # Agrupar logs por span_name dentro deste trace
        span_logs = defaultdict(list)
        
        for log in trace_logs:
            span_name = log.get('span_name')
            if span_name:
                span_logs[span_name].append(log)
        
        # Para cada span neste trace, calcular duração
        for span_name, logs in span_logs.items():
            span_traces[span_name].add(trace_id)
            span_executions[span_name] += 1
            
            # Calcular duração por diferença de timestamps
            # Ordenar logs por timestamp para pegar primeiro e último
            logs_sorted = sorted(logs, key=lambda x: x.get('timestamp', ''))
            
            if len(logs_sorted) >= 2:
                try:
                    first_ts = datetime.fromisoformat(logs_sorted[0]['timestamp'].replace('Z', '+00:00'))
                    last_ts = datetime.fromisoformat(logs_sorted[-1]['timestamp'].replace('Z', '+00:00'))
                    duration_ms = (last_ts - first_ts).total_seconds() * 1000
                    
                    # Garantir que duração não seja negativa
                    if duration_ms < 0:
                        duration_ms = 0.0
                    
                    span_durations[span_name].append(duration_ms)
                except Exception:
                    # Se falhar parse, usar 0
                    span_durations[span_name].append(0.0)
            elif len(logs_sorted) == 1:
                # Apenas 1 log - duração não pode ser calculada, usar 0
                span_durations[span_name].append(0.0)
    
    # Calcular estatísticas
    stats = {}
    all_spans = set(span_traces.keys())
    
    for span_name in all_spans:
        durations = span_durations.get(span_name, [])
        executions = span_executions[span_name]
        
        # Filtrar durações > 0 para cálculo de min (ignorar casos com 1 log apenas)
        durations_non_zero = [d for d in durations if d > 0]
        
        stats[span_name] = {
            'count': executions,  # Número de execuções
            'traces': len(span_traces[span_name]),  # Número de traces únicos
            'avg': sum(durations_non_zero) / len(durations_non_zero) if durations_non_zero else 0,
            'min': min(durations_non_zero) if durations_non_zero else 0,
            'max': max(durations) if durations else 0,
            'total': sum(durations) if durations else 0
        }
    
    return stats, span_durations

def detect_trace_errors(traces: Dict[str, List[Dict]]) -> Dict[str, bool]:
    """
    Detecta se um trace teve erro.
    
    Um trace tem erro se:
    - Contém log com level='ERROR'
    - Contém metadata com status='failed'
    - Contém mensagem de exceção
    """
    trace_errors = {}
    
    for trace_id, trace_logs in traces.items():
        has_error = False
        
        for log in trace_logs:
            # Verificar nível de log
            if log.get('level', '').upper() == 'ERROR':
                has_error = True
                break
            
            # Verificar status no metadata
            metadata = log.get('metadata', {})
            if metadata.get('status') == 'failed':
                has_error = True
                break
            
            # Verificar mensagens de erro
            message = log.get('message', '').lower()
            if any(word in message for word in ['error', 'exception', 'failed', 'erro']):
                has_error = True
                break
        
        trace_errors[trace_id] = has_error
    
    return trace_errors

def generate_visualizations(traces: Dict[str, List[Dict]], span_stats: Dict, span_durations: Dict[str, List[float]], output_dir: str) -> List[str]:
    """
    Gera visualizações gráficas da análise de traces.
    
    Args:
        traces: Dicionário de traces com seus logs
        span_stats: Estatísticas agregadas por span
        span_durations: Durações brutas por span para gráficos
        output_dir: Diretório para salvar os gráficos
    
    Returns:
        Lista de caminhos dos arquivos de imagem gerados
    """
    if not VISUALIZATION_ENABLED:
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []
    
    # Preparar dados
    trace_data = []
    trace_errors = detect_trace_errors(traces)
    
    for trace_id, trace_logs in traces.items():
        if not trace_logs:
            continue
        
        duration = calculate_trace_duration(trace_logs)
        timestamp = datetime.fromisoformat(trace_logs[0]['timestamp'].replace('Z', '+00:00'))
        has_error = trace_errors.get(trace_id, False)
        
        # Identificar span principal
        span_name = None
        for log in trace_logs:
            if log.get('span_name'):
                span_name = log.get('span_name')
                break
        
        trace_data.append({
            'trace_id': trace_id,
            'timestamp': timestamp,
            'duration': duration,
            'has_error': has_error,
            'span_name': span_name or 'unknown'
        })
    
    if not trace_data:
        return []
    
    # Gráfico 1: Duração x Tempo (scatter plot)
    try:
        plt.figure(figsize=(14, 6))
        
        success_traces = [t for t in trace_data if not t['has_error']]
        error_traces = [t for t in trace_data if t['has_error']]
        
        if success_traces:
            times_success = [t['timestamp'] for t in success_traces]
            durations_success = [t['duration'] for t in success_traces]
            plt.scatter(times_success, durations_success, c='green', alpha=0.6, s=100, label='Sucesso')
        
        if error_traces:
            times_error = [t['timestamp'] for t in error_traces]
            durations_error = [t['duration'] for t in error_traces]
            plt.scatter(times_error, durations_error, c='red', alpha=0.8, s=150, marker='x', label='Erro', linewidths=3)
        
        plt.xlabel('Tempo', fontsize=12)
        plt.ylabel('Duração (ms)', fontsize=12)
        plt.title('📊 Duração de Traces ao Longo do Tempo', fontsize=14, fontweight='bold')
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        filepath = os.path.join(output_dir, 'trace_duration_timeline.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        generated_files.append(filepath)
        print(f"   ✓ Gráfico gerado: {filepath}")
    except Exception as e:
        print(f"   ⚠️  Erro ao gerar gráfico de timeline: {e}")
    
    # Gráfico 2: Distribuição de durações por span (box plot)
    if span_stats and span_durations:
        try:
            plt.figure(figsize=(12, 6))
            
            span_names = list(span_stats.keys())
            durations_by_span = []
            
            for span_name in span_names:
                # Usar durações já calculadas, filtrar zeros
                durations = span_durations.get(span_name, [])
                durations_non_zero = [d for d in durations if d > 0]
                # Se todos são zero, manter pelo menos um para o gráfico não quebrar
                durations_by_span.append(durations_non_zero if durations_non_zero else [0])
            
            bp = plt.boxplot(durations_by_span, tick_labels=span_names, patch_artist=True)
            
            # Colorir boxes
            colors = ['#90EE90', '#87CEEB', '#FFB6C1']
            for patch, color in zip(bp['boxes'], colors * len(span_names)):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            
            plt.ylabel('Duração (ms)', fontsize=12)
            plt.xlabel('Span', fontsize=12)
            plt.title('📦 Distribuição de Durações por Span', fontsize=14, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, axis='y', alpha=0.3)
            plt.tight_layout()
            
            filepath = os.path.join(output_dir, 'span_duration_distribution.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            print(f"   ✓ Gráfico gerado: {filepath}")
        except Exception as e:
            print(f"   ⚠️  Erro ao gerar gráfico de distribuição: {e}")
    
    # Gráfico 3: Performance por Span (bar chart)
    if span_stats:
        try:
            plt.figure(figsize=(12, 6))
            
            span_names = list(span_stats.keys())
            avg_durations = [span_stats[s]['avg'] for s in span_names]
            max_durations = [span_stats[s]['max'] for s in span_names]
            min_durations = [span_stats[s]['min'] for s in span_names]
            
            x = np.arange(len(span_names))
            width = 0.25
            
            plt.bar(x - width, min_durations, width, label='Min', alpha=0.7, color='lightgreen')
            plt.bar(x, avg_durations, width, label='Média', alpha=0.8, color='skyblue')
            plt.bar(x + width, max_durations, width, label='Max', alpha=0.7, color='lightcoral')
            
            plt.xlabel('Span', fontsize=12)
            plt.ylabel('Duração (ms)', fontsize=12)
            plt.title('⚡ Performance por Span (Min/Avg/Max)', fontsize=14, fontweight='bold')
            plt.xticks(x, span_names, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, axis='y', alpha=0.3)
            plt.tight_layout()
            
            filepath = os.path.join(output_dir, 'span_performance_comparison.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            print(f"   ✓ Gráfico gerado: {filepath}")
        except Exception as e:
            print(f"   ⚠️  Erro ao gerar gráfico de performance: {e}")
    
    # Gráfico 4: Taxa de erro (se houver erros)
    error_count = sum(1 for t in trace_data if t['has_error'])
    if error_count > 0:
        try:
            plt.figure(figsize=(8, 6))
            
            labels = ['Sucesso', 'Erro']
            sizes = [len(trace_data) - error_count, error_count]
            colors = ['#90EE90', '#FF6B6B']
            explode = (0, 0.1)
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                   shadow=True, startangle=90, textprops={'fontsize': 12})
            plt.title('🎯 Taxa de Sucesso vs Erro', fontsize=14, fontweight='bold')
            plt.axis('equal')
            
            filepath = os.path.join(output_dir, 'trace_success_rate.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            generated_files.append(filepath)
            print(f"   ✓ Gráfico gerado: {filepath}")
        except Exception as e:
            print(f"   ⚠️  Erro ao gerar gráfico de taxa de erro: {e}")
    
    return generated_files

def generate_markdown(logs: List[Dict], traces: Dict, spans: Dict, span_stats: Dict, graph_files: List[str] = None) -> str:
    """Gera relatório markdown."""
    md = []
    graph_files = graph_files or []
    
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
    
    # Adicionar informações sobre erros
    trace_errors = detect_trace_errors(traces)
    error_count = sum(1 for has_error in trace_errors.values() if has_error)
    success_rate = ((len(traces) - error_count) / len(traces) * 100) if traces else 0
    
    if error_count > 0:
        md.append(f"- **Traces com erro:** {error_count} ({error_count/len(traces)*100:.1f}%)")
        md.append(f"- **Taxa de sucesso:** {success_rate:.1f}%")
    
    md.append("")
    
    # Adicionar gráficos se disponíveis
    if graph_files:
        md.append("## 📈 Visualizações")
        md.append("")
        for graph_file in graph_files:
            # Usar caminho relativo para o markdown
            basename = os.path.basename(graph_file)
            md.append(f"### {basename.replace('_', ' ').replace('.png', '').title()}")
            md.append("")
            md.append(f"![{basename}]({basename})")
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
    trace_errors = detect_trace_errors(traces)
    
    for idx, (trace_id, trace_logs) in enumerate(sorted_traces[:10], 1):
        duration = calculate_trace_duration(trace_logs)
        has_error = trace_errors.get(trace_id, False)
        status_emoji = "❌" if has_error else "✅"
        
        md.append(f"### Trace #{idx}: `{trace_id[:12]}...` {status_emoji}")
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
    span_stats, span_durations = calculate_span_stats(traces)
    
    print("📈 Gerando visualizações...")
    # Definir diretório de saída para gráficos
    output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else '.'
    graph_files = generate_visualizations(traces, span_stats, span_durations, output_dir)
    
    print("📝 Gerando relatório markdown...")
    markdown = generate_markdown(app_logs, traces, spans, span_stats, graph_files)
    
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"\n✅ Relatório gerado: {output_file}")
    print(f"📊 {len(traces)} traces analisados")
    print(f"📝 {len(app_logs)} logs processados")
    print(f"🎯 {len(spans)} spans detectados")

if __name__ == '__main__':
    main()
