import { useEffect } from "react";
import L from "leaflet";
import { useMap } from "react-leaflet";
import type { CleanEdgeFeature } from "../types/cleanliness";
import { getCleanColor } from "../utils/cleanColor";

interface Props {
  edges: CleanEdgeFeature[];
}

/** B2G-only translucent canvas heat layer.
 * Samples visible walking links into 18px cells and paints radial gradients.
 * Color represents the model-derived clean index (not measured air quality).
 * This is a display approximation; it is not a KDE of observed smoke.
 */
export default function B2GHeatmap({ edges }: Props) {
  const map = useMap();

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.className = "leaflet-zoom-hide";
    canvas.style.position = "absolute";
    canvas.style.pointerEvents = "none";
    const overlay = map.getPanes().overlayPane;
    overlay.appendChild(canvas);

    const draw = () => {
      const size = map.getSize();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(size.x * scale));
      canvas.height = Math.max(1, Math.round(size.y * scale));
      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;
      L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.clearRect(0, 0, size.x, size.y);

      const grid = new Map<string, { x: number; y: number; clean: number }>();
      const cell = 18;
      const add = (x: number, y: number, clean: number) => {
        if (x < -40 || y < -40 || x > size.x + 40 || y > size.y + 40) return;
        const gx = Math.round(x / cell);
        const gy = Math.round(y / cell);
        const key = `${gx}:${gy}`;
        const current = grid.get(key);
        if (!current || clean < current.clean) {
          grid.set(key, { x: gx * cell, y: gy * cell, clean });
        }
      };
      for (const edge of edges) {
        const clean = edge.properties.cleanIndex;
        const coords = edge.geometry.coordinates;
        for (let i = 1; i < coords.length; i++) {
          const a = map.latLngToContainerPoint([coords[i - 1][1], coords[i - 1][0]]);
          const b = map.latLngToContainerPoint([coords[i][1], coords[i][0]]);
          // Sample along projected line segments; limit extreme long edges.
          const count = Math.max(1, Math.min(250, Math.ceil(a.distanceTo(b) / 12)));
          for (let t = 0; t <= count; t++) {
            const fraction = t / count;
            add(a.x + (b.x - a.x) * fraction, a.y + (b.y - a.y) * fraction, clean);
          }
        }
      }
      for (const { x, y, clean } of grid.values()) {
        const color = getCleanColor(clean);
        const rgb = color.slice(1);
        const r = Number.parseInt(rgb.slice(0, 2), 16);
        const g = Number.parseInt(rgb.slice(2, 4), 16);
        const b = Number.parseInt(rgb.slice(4, 6), 16);
        const gradient = ctx.createRadialGradient(x, y, 1, x, y, 34);
        gradient.addColorStop(0, `rgba(${r},${g},${b},0.30)`);
        gradient.addColorStop(0.45, `rgba(${r},${g},${b},0.13)`);
        gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, 34, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    map.on("moveend zoomend resize", draw);
    draw();
    return () => {
      map.off("moveend zoomend resize", draw);
      canvas.remove();
    };
  }, [map, edges]);
  return null;
}
