import { useEffect, useMemo, useRef } from "react";
import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import { MarkerClusterer } from "@googlemaps/markerclusterer";
import { VesselSummary } from "../types";

const containerStyle = { width: "100%", height: "100%" };

// Centered on the Philippine archipelago
const center = { lat: 12.5, lng: 122.0 };

function loadRatio(v: VesselSummary): number | null {
  if (v.current_draught_m == null || v.design_draught_m == null || v.design_draught_m <= 0) {
    return null;
  }
  return Math.max(0, Math.min(1, v.current_draught_m / v.design_draught_m));
}

function colorFor(v: VesselSummary): string {
  const ratio = loadRatio(v);
  if (ratio == null) return "#a0aec0"; // grey
  if (ratio >= 0.75) return "#c53030"; // laden — red
  if (ratio >= 0.55) return "#dd6b20"; // partial — orange
  return "#3182ce"; // ballast — blue
}

interface Props {
  apiKey: string;
  vessels: VesselSummary[];
  onSelect: (v: VesselSummary) => void;
}

export function Map({ apiKey, vessels, onSelect }: Props) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map",
    googleMapsApiKey: apiKey,
  });

  const mapRef = useRef<google.maps.Map | null>(null);
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);

  const positioned = useMemo(
    () => vessels.filter((v) => v.last_position != null),
    [vessels],
  );

  useEffect(() => {
    if (!isLoaded || !mapRef.current) return;

    for (const m of markersRef.current) m.setMap(null);
    clustererRef.current?.clearMarkers();

    const markers = positioned.map((v) => {
      const marker = new google.maps.Marker({
        position: {
          lat: v.last_position!.latitude,
          lng: v.last_position!.longitude,
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 6,
          fillColor: colorFor(v),
          fillOpacity: 0.9,
          strokeColor: "#1a202c",
          strokeWeight: 1,
        },
        title: v.name ?? String(v.mmsi),
      });
      marker.addListener("click", () => onSelect(v));
      return marker;
    });

    markersRef.current = markers;
    clustererRef.current = new MarkerClusterer({ map: mapRef.current, markers });
  }, [isLoaded, positioned, onSelect]);

  if (loadError) return <div style={{ padding: 16 }}>Failed to load Google Maps: {loadError.message}</div>;
  if (!isLoaded) return <div style={{ padding: 16 }}>Loading map…</div>;

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={6}
      onLoad={(m) => {
        mapRef.current = m;
      }}
      options={{
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      }}
    />
  );
}
