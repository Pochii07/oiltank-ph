import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { fetchLatestPositions } from "./api";
import { Map } from "./components/Map";
import { SubtypeFilter } from "./components/SubtypeFilter";
import { VesselPanel } from "./components/VesselPanel";
import { Subtype, VesselSummary } from "./types";

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

const DEFAULT_SUBTYPES: Subtype[] = ["crude_oil", "product"];

export default function App() {
  const [subtypes, setSubtypes] = useState<Subtype[]>(DEFAULT_SUBTYPES);
  const [vessels, setVessels] = useState<VesselSummary[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [selected, setSelected] = useState<VesselSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLatestPositions(subtypes);
      setVessels(data);
      setUpdatedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [subtypes]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Philippine Oil Tanker Tracker</h1>
        <SubtypeFilter selected={subtypes} onChange={setSubtypes} />
        <button onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
        <span className="updated">
          {error
            ? `Error: ${error}`
            : updatedAt
              ? `${vessels.length} vessels · updated ${updatedAt.toLocaleTimeString()}`
              : "Loading…"}
        </span>
      </header>

      <div className="app-body">
        {MAPS_KEY ? (
          <Map apiKey={MAPS_KEY} vessels={vessels} onSelect={setSelected} />
        ) : (
          <div style={{ padding: 16 }}>
            Set <code>VITE_GOOGLE_MAPS_API_KEY</code> to display the map.
          </div>
        )}
        {selected && <VesselPanel vessel={selected} onClose={() => setSelected(null)} />}
      </div>
    </div>
  );
}
