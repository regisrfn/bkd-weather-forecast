#!/usr/bin/env python3
"""
Gera um relatório em Markdown com contagens de requisições do API Gateway
usando CloudWatch Logs Insights.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError


SECTION_AND_IP_QUERY = """fields ip, resourcePath
| filter ip != "-" and ispresent(resourcePath)
| parse resourcePath '/api/*' as section
| stats count() as requests by section, resourcePath, ip
| sort requests desc
| limit {limit}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera relatório de acessos do API Gateway via CloudWatch Logs Insights."
    )
    parser.add_argument(
        "--log-group",
        default="/aws/apigateway/weather-forecast-api",
        help="Nome do log group do API Gateway.",
    )
    parser.add_argument(
        "--region",
        default="sa-east-1",
        help="Região AWS (ex.: sa-east-1).",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Janela de tempo (em horas) para a busca. Padrão: 24h.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Limite de linhas retornadas por consulta. Padrão: 50.",
    )
    parser.add_argument(
        "--output",
        default="output/api_gateway_access_report.md",
        help="Arquivo Markdown de saída.",
    )
    return parser.parse_args()


def run_insights_query(
    client,
    log_group: str,
    query: str,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    poll_interval: float = 1.0,
    max_attempts: int = 60,
) -> Dict:
    query_id = client.start_query(
        logGroupName=log_group,
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query.format(limit=limit),
        limit=limit,
    )["queryId"]

    for _ in range(max_attempts):
        response = client.get_query_results(queryId=query_id)
        status = response.get("status")

        if status == "Complete":
            return response
        if status in {"Failed", "Cancelled", "Timeout", "Unknown"}:
            raise RuntimeError(f"Query {status}: {response}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Query {query_id} não finalizou em tempo hábil.")


def results_to_rows(results: Iterable[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for result in results:
        row = {field["field"]: field.get("value", "") for field in result if field["field"] != "@ptr"}
        rows.append(row)
    return rows


def render_table(headers: List[str], rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "_Nenhum resultado encontrado para o intervalo solicitado._"

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for row in rows:
        values = [str(row.get(header, "")) for header in headers]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def geolocate_ip(ip: str, session: requests.Session, cache: Dict[str, Dict[str, Optional[str]]]) -> Dict[str, Optional[str]]:
    if ip in cache:
        return cache[ip]

    url = f"https://ipapi.co/{ip}/json/"
    try:
        resp = session.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            cache[ip] = {
                "city": data.get("city"),
                "country": data.get("country_name"),
            }
        else:
            cache[ip] = {"city": None, "country": None}
    except Exception:
        cache[ip] = {"city": None, "country": None}

    return cache[ip]


def build_markdown(
    log_group: str,
    region: str,
    window_start: datetime,
    window_end: datetime,
    section_rows: List[Dict[str, str]],
    limit: int,
) -> str:
    lines = []
    lines.append("# Relatório de acessos do API Gateway\n")
    lines.append(f"- Log group: `{log_group}` ({region})")
    lines.append(f"- Janela: {window_start.isoformat()} ➜ {window_end.isoformat()}")
    lines.append(f"- Gerado em: {datetime.now(timezone.utc).isoformat()}\n")

    lines.append("## Contagem por rota (seção) e IP")
    lines.append(
        render_table(
            headers=["seção", "rota", "ip", "cidade", "país", "requisições"],
            rows=[
                {
                    "seção": row.get("section", ""),
                    "rota": row.get("resourcePath", ""),
                    "ip": row.get("ip", ""),
                    "cidade": row.get("city", "-") or "-",
                    "país": row.get("country", "-") or "-",
                    "requisições": row.get("requests", "0"),
                }
                for row in section_rows
            ],
        )
    )
    lines.append("")

    lines.append("## Queries usadas (CloudWatch Logs Insights)")
    lines.append("```")
    lines.append(SECTION_AND_IP_QUERY.format(limit=limit))
    lines.append("```")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    if args.hours <= 0:
        print("Parâmetro --hours deve ser maior que 0.", file=sys.stderr)
        return 1

    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=args.hours)

    client = boto3.client("logs", region_name=args.region)

    # Busca métricas por rota e IP
    try:
        section_response = run_insights_query(
            client,
            log_group=args.log_group,
            query=SECTION_AND_IP_QUERY,
            start_time=window_start,
            end_time=window_end,
            limit=args.limit,
        )
    except (BotoCoreError, ClientError, RuntimeError, TimeoutError) as exc:
        print(f"Erro ao executar queries: {exc}", file=sys.stderr)
        return 1

    section_rows = results_to_rows(section_response.get("results", []))

    # Enriquecimento geográfico por IP
    session = requests.Session()
    geo_cache: Dict[str, Dict[str, Optional[str]]] = {}
    for row in section_rows:
        ip = row.get("ip")
        if not ip:
            continue
        geo = geolocate_ip(ip, session, geo_cache)
        row["city"] = geo.get("city")
        row["country"] = geo.get("country")

    report = build_markdown(
        log_group=args.log_group,
        region=args.region,
        window_start=window_start,
        window_end=window_end,
        section_rows=section_rows,
        limit=args.limit,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"Relatório salvo em {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
