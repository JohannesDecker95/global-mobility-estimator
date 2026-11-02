// All-in cost per month for each length of stay, coloured by the rules that apply.
// A line with dots, not bars: the axis does not start at zero, and a line shows that honestly.
import type { AdviceRow } from "./api";
import { money0 } from "./format";

type Regime = "relief" | "swiss" | "uk";
const regime = (r: AdviceRow): Regime => (r.social_security === "UK" ? "uk" : r.relief ? "relief" : "swiss");
export const REGIME_LABELS: Record<Regime, string> = {
  relief: "Swiss social security, housing relief",
  swiss: "Swiss social security, no housing relief",
  uk: "UK National Insurance, no housing relief",
};

/** A round step (1, 2 or 5 times a power of ten) giving about `n` intervals. */
function niceStep(span: number, n: number): number {
  const raw = span / n;
  const p = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((k) => k * p).find((s) => s >= raw) ?? 10 * p;
}

export function AdviceChart({ rows, planned, cheapest }: { rows: AdviceRow[]; planned: number; cheapest: number }) {
  const W = 760, H = 270, L = 70, R = 16, T = 26, B = 40;
  const values = rows.map((r) => Number(r.per_month));
  const step = niceStep(Math.max(...values) - Math.min(...values) || 1000, 4);
  const y0 = Math.floor(Math.min(...values) / step) * step;
  const y1 = Math.ceil(Math.max(...values) / step) * step;
  const ticks: number[] = [];
  for (let t = y0; t <= y1 + step / 2; t += step) ticks.push(t);
  const first = rows[0].months, last = rows[rows.length - 1].months;
  const x = (m: number) => L + ((m - first) / Math.max(last - first, 1)) * (W - L - R);
  const y = (v: number) => T + (H - T - B) * (1 - (v - y0) / (y1 - y0 || 1));

  // one path per run of the same rules, so the jump at 24 months is not drawn as a slope
  const runs: { regime: Regime; rows: AdviceRow[] }[] = [];
  for (const r of rows) {
    const g = regime(r);
    if (runs.length && runs[runs.length - 1].regime === g) runs[runs.length - 1].rows.push(r);
    else runs.push({ regime: g, rows: [r] });
  }
  const present = Array.from(new Set(rows.map(regime)));
  const marks = rows.filter((r) => r.months === planned || r.months === cheapest);

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`All-in cost per month for stays of ${first} to ${last} months. Cheapest ${cheapest} months, planned ${planned} months.`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="grid-line" />
            <text x={L - 8} y={y(t) + 4} className="axis" textAnchor="end">{money0(t)}</text>
          </g>
        ))}
        {rows.filter((r) => r.months % 6 === 0 || r.months === first).map((r) => (
          <text key={r.months} x={x(r.months)} y={H - B + 18} className="axis" textAnchor="middle">{r.months}</text>
        ))}
        {runs.map((run) => (
          <polyline key={run.rows[0].months} className={`run ${run.regime}`} fill="none"
                    points={run.rows.map((r) => `${x(r.months)},${y(Number(r.per_month))}`).join(" ")} />
        ))}
        {rows.map((r) => (
          <circle key={r.months} cx={x(r.months)} cy={y(Number(r.per_month))} r={3.2} className={`dot ${regime(r)}`}>
            <title>{`${r.months} months: ${money0(r.per_month)} a month, ${money0(r.all_in)} in all`}</title>
          </circle>
        ))}
        {marks.map((r) => {
          const kind = r.months === cheapest ? "cheapest" : "planned";
          const label = r.months === cheapest && r.months === planned ? "planned, cheapest" : kind;
          return (
            <g key={kind}>
              <circle cx={x(r.months)} cy={y(Number(r.per_month))} r={6} className={`mark ${kind}`} />
              <text x={x(r.months)} y={y(Number(r.per_month)) + 20} className={`mark-label ${kind}`} textAnchor="middle">
                {label}, {r.months}
              </text>
            </g>
          );
        })}
        <text x={(L + W - R) / 2} y={H - 4} className="axis" textAnchor="middle">Length of stay, months</text>
      </svg>
      <figcaption className="legend">
        {present.map((p) => <span key={p}><i className={`swatch ${p}`} />{REGIME_LABELS[p]}</span>)}
        <span className="muted">Cost per month, all-in</span>
      </figcaption>
    </figure>
  );
}
