"""B2G walking-edge GeoJSON with scored links and explicitly unknown links.

Unscored links are not considered clean/safe: their model scores remain null.
The caller exposes this collection only when a real model CSV is connected.
"""
from pyproj import Transformer
from walking_router import get_edge_line


def edge_cleanliness_geojson(graph, edge_risks):
    """Return every walking link; only scored links receive cleanliness values."""
    convert = Transformer.from_crs(graph.graph["crs"], "EPSG:4326", always_xy=True)

    # Reject invalid model-to-graph link associations before serializing.
    for u, v, key in edge_risks:
        if graph.get_edge_data(u, v, key) is None:
            raise ValueError(f"위험 점수와 일치하는 보행 링크 없음: {u},{v},{key}")

    features = []
    for u, v, key, edge in graph.edges(keys=True, data=True):
        line = get_edge_line(graph, u, v, edge)
        coordinates = [
            [float(lng), float(lat)]
            for lng, lat in (convert.transform(x, y) for x, y in line.coords)
        ]
        if len(coordinates) < 2:
            continue

        risk = edge_risks.get((u, v, key))
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {
                "edgeId": f"{u}:{v}:{key}",
                "score": round(float(risk["score"]), 2) if risk is not None else None,
                "cleanIndex": round(float(risk["cleanIndex"]), 2) if risk is not None else None,
            },
        })

    return {"type": "FeatureCollection", "features": features}
