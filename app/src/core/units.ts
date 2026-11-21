// Display units (decision 9.15): every level in the model is metres NAVD88, and feet appear only at the display
// edge. A number field's x-unit says what it holds; Units converts metres to the chosen display unit and back.
// The foot is the international foot, 0.3048 m exactly (the US survey foot was retired at the end of 2022).

export type LengthUnit = "m" | "ft";

export const M_PER_FT = 0.3048;

type Listener = (u: LengthUnit) => void;

/** x-units that are lengths in metres and so switch with the display unit. */
const LENGTH_UNITS: ReadonlySet<string> = new Set(["m"]);

export class Units {
  private unit: LengthUnit;
  private listeners = new Set<Listener>();

  private readonly storage: Pick<Storage, "getItem" | "setItem"> | null;

  constructor(initial: LengthUnit = "m", storage: Pick<Storage, "getItem" | "setItem"> | null = null) {
    this.storage = storage;
    const saved = storage?.getItem("cr.units");
    this.unit = saved === "ft" || saved === "m" ? saved : initial;
  }

  get length(): LengthUnit {
    return this.unit;
  }

  set(u: LengthUnit): void {
    if (u === this.unit) return;
    this.unit = u;
    this.storage?.setItem("cr.units", u);
    for (const fn of this.listeners) fn(u);
  }

  toggle(): void {
    this.set(this.unit === "m" ? "ft" : "m");
  }

  onChange(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  /** Whether values of this x-unit change with the display unit. */
  switches(xunit: string | undefined): boolean {
    return xunit !== undefined && LENGTH_UNITS.has(xunit);
  }

  /** The unit label a value of this x-unit shows with. */
  label(xunit: string | undefined): string {
    if (xunit === undefined) return "";
    if (this.switches(xunit)) return this.unit;
    if (xunit === "permille") return "‰";
    if (xunit === "percent") return "%";
    if (xunit === "count" || xunit === "index" || xunit === "ratio") return "";
    return xunit;
  }

  /** A stored value (in its x-unit) as the number to show. */
  toDisplay(v: number, xunit: string | undefined): number {
    return this.switches(xunit) && this.unit === "ft" ? v / M_PER_FT : v;
  }

  /** A typed display number back to the stored x-unit. */
  fromDisplay(v: number, xunit: string | undefined): number {
    return this.switches(xunit) && this.unit === "ft" ? v * M_PER_FT : v;
  }

  /** A stored value formatted for display: 3 decimals for levels in metres, 2 in feet, as given otherwise. */
  format(v: number | null | undefined, xunit: string | undefined, digits?: number): string {
    if (v === null || v === undefined || !Number.isFinite(v)) return "";
    const d = digits ?? (this.switches(xunit) ? (this.unit === "ft" ? 2 : 3) : xunit === "permille" ? 2 : 3);
    return trimZeros(this.toDisplay(v, xunit).toFixed(d));
  }

  /** Parse what Ben typed in the display unit. A trailing unit ("12 ft", "3.5m") overrides the display unit. */
  parse(text: string, xunit: string | undefined): number | null {
    const m = /^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)\s*(m|ft|')?\s*$/i.exec(text);
    if (!m?.[1]) return null;
    const v = Number(m[1]);
    if (!Number.isFinite(v)) return null;
    const typed = m[2]?.toLowerCase();
    if (typed && this.switches(xunit)) return typed === "m" ? v : v * M_PER_FT;
    return this.fromDisplay(v, xunit);
  }
}

function trimZeros(s: string): string {
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

/** A chainage as the readout shows it: 12+400.0 in metres, or feet to a tenth. */
export function formatChainage(c: number, units: Units): string {
  if (units.length === "ft") return `${(c / M_PER_FT).toFixed(1)} ft`;
  // Round to the tenth first, so 12,999.97 m reads 13+000.0 and not 12+1000.0.
  const r = Math.round(c * 10) / 10;
  const km = Math.floor(r / 1000);
  const rest = r - km * 1000;
  return `${km}+${rest.toFixed(1).padStart(5, "0")}`;
}
