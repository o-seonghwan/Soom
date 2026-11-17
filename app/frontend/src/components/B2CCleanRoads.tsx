import { useEffect } from "react";
import L from "leaflet";
import { useMap } from "react-leaflet";
import type { CleanEdgeFeature } from "../types/cleanliness";
import { deduplicateCleanEdges } from "../utils/deduplicateCleanEdges";

interface Props {
  edges: CleanEdgeFeature[];
}

// Avoid a solid block at district-wide zoom levels.
// Detailed walking links are shown at zoom 15 and above only.
export const B2C_MIN_WALKWAY_ZOOM = 15;
const GREEN: [number, number, number] = [22, 163, 74]; // #16a34a

/**
 * Render model-based B2C paths in one composited raster.
 * Per-pixel opacity is the MAX of covering paths, not the sum.
 * Therefore overlapping bidirectional/intersecting edges don't grow darker.
 * Unscored paths remain unpainted; routing and B2G display are untouched.
 */
export default function B2CCleanRoads({ edges }: Props) {
  const map = useMap();

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.className = "leaflet-zoom-hide";
    canvas.style.imageRendering = "auto";
    canvas.style.position = "absolute";
    canvas.style.pointerEvents = "none";
    const pane = map.getPanes().overlayPane;
    pane.appendChild(canvas);

    // Reuse one offscreen canvas to paint into independent intensity pixels.
    const intensityCanvas = document.createElement("canvas");
    const uniqueEdges = deduplicateCleanEdges(edges);
    let frame = 0;

    function render() {
      const size = map.getSize();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.ceil(size.x * scale));
      const height = Math.max(1, Math.ceil(size.y * scale));
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;
      L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));

      const output = canvas.getContext("2d");
      if (!output) return;
      output.clearRect(0, 0, width, height);

      if (map.getZoom() < B2C_MIN_WALKWAY_ZOOM) return;

      intensityCanvas.width = width;
      intensityCanvas.height = height;
      const intensity = intensityCanvas.getContext("2d", { willReadFrequently: true });
      if (!intensity) return;

      // Use 'lighten' on grayscale source: overlapping geometry retains
      // the maximum per-pixel opacity instead of alpha accumulating.
      // Opaque black underlayer is required: lighten on transparent canvas
      // would otherwise alpha-composite different links into a dark blob.
      intensity.globalCompositeOperation = "source-over";
      intensity.fillStyle = "#000";
      intensity.fillRect(0, 0, width, height);
      intensity.globalCompositeOperation = "lighten";
      intensity.lineWidth = (map.getZoom() >= 17 ? 3.2 : 2.2) * scale;
      intensity.lineCap = "round";
      intensity.lineJoin = "round";

      for (const edge of uniqueEdges) {
        const clean = Number(edge.properties.cleanIndex);
        if (!Number.isFinite(clean)) continue;
        const alpha = 0.18 + 0.67 * (Math.max(0, Math.min(100, clean)) / 100);
        const coords = edge.geometry.coordinates;
        if (coords.length < 2) continue;
        intensity.strokeStyle = `rgb(${Math.round(alpha * 255)}, ${Math.round(alpha * 255)}, ${Math.round(alpha * 255)})`;
        intensity.beginPath();
        for (let i = 0; i < coords.length; i++) {
          const point = map.latLngToContainerPoint([coords[i][1], coords[i][0]]);
          const x = point.x * scale;
          const y = point.y * scale;
          if (i === 0) intensity.moveTo(x, y);
          else intensity.lineTo(x, y);
        }
        intensity.stroke();
      }

      const mask = intensity.getImageData(0, 0, width, height);
      const pixels = output.createImageData(width, height);
      for (let i = 0; i < pixels.data.length; i += 4) {
        const alpha = mask.data[i]; // grayscale maximum from overlapping lines
        pixels.data[i] = GREEN[0];
        pixels.data[i + 1] = GREEN[1];
        pixels.data[i + 2] = GREEN[2];
        pixels.data[i + 3] = alpha;
      }
      output.putImageData(pixels, 0, 0);
    }

    // During map movement remove the stale overlay immediately to avoid
    // duplicated/ghost roads. Redraw only at a stable map position.
    const clear = () => { canvas.style.visibility = "hidden"; };
    const schedule = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        render();
        canvas.style.visibility = "visible";
      });
    };
    map.on("movestart zoomstart", clear);
    map.on("moveend zoomend resize", schedule);
    schedule();
    return () => {
      window.cancelAnimationFrame(frame);
      map.off("movestart zoomstart", clear);
      map.off("moveend zoomend resize", schedule);
      canvas.remove();
    };
  }, [map, edges]);

  return null;
}
