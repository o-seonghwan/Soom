"""Reproducible route-weight simulation over REAL local model CSV and walking graph.

Usage (repo root):
  $env:LUNG_RISK_CSV = "<absolute-path-to-1_위험지도_지점.csv>"
  python app/backend/simulate_avoidance.py --pairs 80 --output avoidance_results.csv
"""
import argparse
import csv
import os
import random
import statistics
from pathlib import Path

import networkx as nx

from risk_provider import get_risk_snapshot
from risk_mapper import map_risks_to_edges
from safe_router import AVOIDANCE_WEIGHTS
from walking_router import load_walking_graph

WEIGHTS = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0)


def edge_metric(graph, risk_map, path, weight):
    distance = risk_cost = 0.0
    for u, v in zip(path, path[1:]):
        key, item = min(
            graph[u][v].items(),
            key=lambda pair: float(pair[1]["length"]) *
            (1 + weight * float(risk_map.get((u, v, pair[0]), {}).get("normalizedRisk", 0)))
        )
        length = float(item["length"])
        distance += length
        risk_cost += length * float(risk_map.get((u, v, key), {}).get("normalizedRisk", 0))
    return distance, risk_cost


def weight_function(risks, strength):
    def cost(u, v, data):
        return min(
            float(e["length"]) * (1 + strength * float(
                risks.get((u, v, k), {}).get("normalizedRisk", 0)
            ))
            for k, e in data.items()
        )
    return cost


def simulate(graph, risks, pairs=80, seed=20261116):
    rng = random.Random(seed)
    nodes = list(graph.nodes)
    if len(nodes) < 2:
        raise ValueError("보행 그래프의 노드가 부족합니다.")
    rows = []
    attempts = 0
    while len(rows) < pairs and attempts < pairs * 40:
        attempts += 1
        start, end = rng.sample(nodes, 2)
        try:
            base = nx.shortest_path(graph, start, end, weight=weight_function(risks, 0))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        base_dist, base_risk = edge_metric(graph, risks, base, 0)
        if not 300 <= base_dist <= 4500:
            continue
        choices = []
        for strength in WEIGHTS:
            chosen = nx.shortest_path(
                graph, start, end, weight=weight_function(risks, strength)
            )
            distance, cost = edge_metric(graph, risks, chosen, strength)
            choices.append((
                100 * (distance / base_dist - 1),
                None if base_risk <= 0 else 100 * (1 - cost / base_risk),
            ))
        rows.append(choices)
    if len(rows) < pairs:
        raise RuntimeError(
            f"유효한 출발지·도착지 {len(rows)}쌍만 생성됨: 분석 범위를 확인하세요."
        )
    results = []
    for pos, strength in enumerate(WEIGHTS):
        detours = sorted(row[pos][0] for row in rows)
        reductions = [row[pos][1] for row in rows if row[pos][1] is not None]
        results.append({
            "weight": strength,
            "pairs": len(rows),
            "exposure_comparable_pairs": len(reductions),
            "mean_detour_pct": round(statistics.mean(detours), 2),
            "p90_detour_pct": round(detours[min(len(detours) - 1, int(len(detours) * .9))], 2),
            "mean_model_risk_cost_reduction_pct": round(statistics.mean(reductions), 2)
            if reductions else "",
            "detour_over_20_pct_share": round(100 * sum(d > 20 for d in detours) / len(detours), 2),
        })
    return results


def cleanliness_distribution(graph, edge_risks):
    """Length weighted percentile; UNMAPPED roads remain unknown, not clean."""
    scored = []
    for edge_id, values in edge_risks.items():
        edge = graph.get_edge_data(*edge_id)
        if edge is None:
            continue
        length = float(edge.get("length", 0))
        clean = float(values["cleanIndex"])
        if length > 0 and 0 <= clean <= 100:
            scored.append((clean, length))
    if not scored:
        raise ValueError("모델 위험이 매핑된 보행로가 없습니다.")
    scored.sort()
    total = sum(length for _, length in scored)
    def quantile(fraction):
        target, count = total * fraction, 0.0
        for clean, length in scored:
            count += length
            if count >= target:
                return round(clean, 1)
        return round(scored[-1][0], 1)
    return {
        "mapped_edge_count": len(scored),
        "mapped_length_m": round(total, 1),
        "clean_p20": quantile(.2),
        "clean_p40": quantile(.4),
        "clean_p60": quantile(.6),
        "clean_p80": quantile(.8),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--output", type=Path, default=Path("avoidance_results.csv"))
    args = parser.parse_args()
    if args.pairs <= 0:
        parser.error("--pairs must be > 0")
    if not os.environ.get("LUNG_RISK_CSV"):
        parser.error("LUNG_RISK_CSV에 실제 AI 모델 CSV 전체 경로를 지정하세요.")
    graph = load_walking_graph()
    snapshot = get_risk_snapshot()
    if snapshot["source"] != "model-csv":
        raise RuntimeError("실제 AI 모델 결과가 연결되지 않았습니다.")
    risks = map_risks_to_edges(graph, snapshot["locations"])
    if not risks:
        raise RuntimeError("보행로에 모델 위험이 매핑되지 않았습니다.")
    print("실제 모델 기반 청정지수 분포:", cleanliness_distribution(graph, risks))
    results = simulate(graph, risks, pairs=args.pairs, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    for item in results:
        print(item)
    print("현재 서비스 가중치:", AVOIDANCE_WEIGHTS)
    print("결과 파일:", args.output.resolve())


if __name__ == "__main__":
    main()
