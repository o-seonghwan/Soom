"""GeoJSON for B2G-only cleanliness visualization of affected walking edges."""
from pyproj import Transformer
from walking_router import get_edge_line


def edge_cleanliness_geojson(graph, edge_risks):
    """Encode only risk-mapped walking edges; unscored paths stay unknown.

    Risk is represented by a minimum distance to each *whole edge*, then max
    across model points. This is not a measured air quality layer.
    """
    convert = Transformer.from_crs(graph.graph["crs"], "EPSG:4326", always_xy=True)
    features = []
    for (u, v, key), data in edge_risks.items():
        edge = graph.get_edge_data(u, v, key)
        if edge is None:
            raise ValueError(f"위험 점수와 일치하는 보행 링크 없음: {u},{v},{key}")
        line = get_edge_line(graph, u, v, edge)
        coordinates = [[float(lng), float(lat)]
                       for lng, lat in (convert.transform(x, y) for x, y in line.coords)]
        if len(coordinates) < 2:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "properties": {
                "edgeId": f"{u}:{v}:{key}",
                "score": round(float(data["score"]), 2),
                "cleanIndex": round(float(data["cleanIndex"]), 2),
            },
        })
    return {"type": "FeatureCollection", "features": features}
