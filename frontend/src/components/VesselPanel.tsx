import { SUBTYPE_LABEL, VesselSummary } from "../types";

interface Props {
  vessel: VesselSummary;
  onClose: () => void;
}

function fmt(n: number | null, suffix = ""): string {
  if (n == null) return "—";
  return n.toLocaleString() + suffix;
}

export function VesselPanel({ vessel: v, onClose }: Props) {
  const hasEstimate = v.estimated_cargo_tonnes != null;

  return (
    <aside className="vessel-panel">
      <header>
        <h2>{v.name ?? `MMSI ${v.mmsi}`}</h2>
        <button className="close-btn" onClick={onClose} aria-label="Close">×</button>
      </header>

      <dl>
        <dt>Subtype</dt>
        <dd>{SUBTYPE_LABEL[v.subtype]}</dd>

        <dt>MMSI</dt>
        <dd>{v.mmsi}</dd>

        <dt>IMO</dt>
        <dd>{v.imo ?? "—"}</dd>

        <dt>Flag</dt>
        <dd>{v.flag ?? "—"}</dd>

        <dt>Dimensions</dt>
        <dd>
          {fmt(v.length_m, " m")} × {fmt(v.width_m, " m")}
        </dd>

        <dt>DWT</dt>
        <dd>{fmt(v.dwt, " t")}</dd>

        <dt>Design draught</dt>
        <dd>{fmt(v.design_draught_m, " m")}</dd>

        <dt>Current draught</dt>
        <dd>{fmt(v.current_draught_m, " m")}</dd>

        <dt>Estimated cargo</dt>
        <dd>
          {hasEstimate ? `${v.estimated_cargo_tonnes!.toLocaleString()} t` : "—"}
          {hasEstimate && (
            <span className="estimate-badge" title="Derived from draught × DWT">
              Est · {v.estimate_confidence}
            </span>
          )}
        </dd>

        <dt>Last seen</dt>
        <dd>{new Date(v.last_seen).toLocaleString()}</dd>
      </dl>

      {hasEstimate && (
        <p className="estimate-tooltip">
          Estimate = DWT × (current_draught / design_draught). Draught is self-reported
          by the crew via AIS and may lag actual conditions.
        </p>
      )}
    </aside>
  );
}
