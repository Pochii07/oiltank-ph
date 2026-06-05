import { ALL_SUBTYPES, Subtype, SUBTYPE_LABEL } from "../types";

interface Props {
  selected: Subtype[];
  onChange: (next: Subtype[]) => void;
}

export function SubtypeFilter({ selected, onChange }: Props) {
  function toggle(s: Subtype) {
    if (selected.includes(s)) {
      onChange(selected.filter((x) => x !== s));
    } else {
      onChange([...selected, s]);
    }
  }

  return (
    <div className="subtype-filter">
      {ALL_SUBTYPES.map((s) => (
        <label key={s}>
          <input
            type="checkbox"
            checked={selected.includes(s)}
            onChange={() => toggle(s)}
          />
          {SUBTYPE_LABEL[s]}
        </label>
      ))}
    </div>
  );
}
