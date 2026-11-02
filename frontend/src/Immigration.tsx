// The immigration tab: route, eligibility, requirements by area, timeline and fees.
// It uses the cost form's inputs, so both tabs describe the same assignment.
import type { FieldErrors, ImmigrationResult, Status, TimelineStep } from "./api";
import { amount, money } from "./format";
import { SourcesCard } from "./Results";
import { RuleIds, SourceLinks } from "./Sources";

const STATUS_TEXT: Record<Status, string> = {
  met: "Met", "not met": "Not met", "to check": "To check", "not checked": "Not checked",
};
const AREA_PARTY: Record<string, string> = {
  work_permit: "Employee", business_visit: "Employee", passport: "Employee", company: "Employer",
};

function StatusBadge({ status }: { status: Status }) {
  return <span className={`status ${status.replace(" ", "-")}`}>{STATUS_TEXT[status]}</span>;
}

function Timeline({ steps, total }: { steps: TimelineStep[]; total: string }) {
  const weeks = Math.max(Number(total), 1);
  return (
    <div className="timeline" role="list">
      {steps.map((s) => {
        const start = Number(s.start_week), end = Number(s.end_week);
        const left = (start / weeks) * 100;
        const width = Math.max(((end - start) / weeks) * 100, 0);
        return (
          <div key={s.id} role="listitem" className={`tl-row ${s.party}${s.skipped ? " skipped" : ""}`}>
            <div className="tl-label">
              <span className="tl-party">{s.party === "employer" ? "Employer" : "Employee"}</span>
              <span>{s.step}</span>
              <span className="muted small">
                {s.skipped ? "Not needed: licence already held"
                  : Number(s.duration) ? `${s.duration} ${s.unit}, weeks ${start}–${end}` : `at week ${end}`}
              </span>
            </div>
            <div className="tl-track" aria-hidden="true">
              {width > 0
                ? <span className="tl-bar" style={{ left: `${left}%`, width: `${width}%` }} />
                : <span className="tl-dot" style={{ left: `calc(${left}% - 5px)` }} />}
            </div>
          </div>
        );
      })}
      <div className="tl-axis" aria-hidden="true">
        <span />
        <div className="tl-ticks">
          {Array.from({ length: Math.floor(weeks) + 1 }, (_, w) => (
            <span key={w} style={{ left: `${(w / weeks) * 100}%` }}>{w}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

interface Props {
  data: ImmigrationResult | null;
  errors: FieldErrors;
  busy: boolean;
  params: Record<string, string>;
  onRefresh: () => void;
  onEditInputs: () => void;
}

export function ImmigrationTab({ data, errors, busy, params, onRefresh, onEditInputs }: Props) {
  const errorList = Object.entries(errors);
  return (
    <div className="immigration">
      <section className="card">
        <div className="form-head">
          <h2>For this assignment</h2>
          <div className="form-actions-top">
            <button type="button" className="btn ghost" onClick={onEditInputs}>Change inputs</button>
            <button type="button" className="btn ghost" onClick={onRefresh} disabled={busy}>
              {busy ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>
        <p className="muted">
          Swiss national · {params.months ?? "24"} months in London ·{" "}
          {params.sponsor_size === "small" ? "small" : "medium or large"} UK sponsor
          {params.sponsor_licence_held === "true" ? " with a licence" : ""}
          {params.salary_gbp ? ` · base salary ${money(params.salary_gbp)} a year` : ""}
          {params.months_with_employer ? ` · ${params.months_with_employer} months with the employer` : ""}.
          These come from the cost form.
        </p>
        {errorList.length > 0 && (
          <div className="error-summary" role="alert">
            <ul>{errorList.map(([k, ms]) => ms.map((m) => <li key={k + m}>{m}</li>))}</ul>
          </div>
        )}
      </section>

      {data && (
        <>
          <section className="card route">
            <h2>{data.route.title}</h2>
            <p>{data.route.summary}</p>
            <SourceLinks sources={data.route.sources} />
          </section>

          <section className="card">
            <div className="form-head">
              <h2>Eligibility</h2>
              <StatusBadge status={data.eligibility.status} />
            </div>
            <p>{data.eligibility.summary}</p>
            <ul className="elig">
              {data.eligibility.checks.map((c) => (
                <li key={c.test}>
                  <StatusBadge status={c.status} />
                  <div>
                    <strong>{c.test}</strong>
                    <p className="muted">{c.detail}</p>
                    <RuleIds ids={c.rule_ids} rules={data.rules} />
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <div className="areas">
            {data.areas.map((area) => (
              <section key={area.key} className={`card area ${area.key}`}>
                <h2><span className="area-kicker">{AREA_PARTY[area.key] ?? ""}</span>{area.title}</h2>
                <ul className="reqs">
                  {area.items.map((item) => (
                    <li key={item.id}>
                      <p>{item.text}</p>
                      <div className="req-meta">
                        {item.time && <span><b>Time:</b> {item.time}</span>}
                        {item.cost && <span><b>Cost here:</b> {money(item.cost.amount)} ({item.cost.paid_by})</span>}
                      </div>
                      <SourceLinks sources={item.sources} />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>

          <section className="card">
            <h2>Timeline</h2>
            <p className="muted">
              Earliest dates in weeks from today, done in sequence: about {Number(data.timeline.total_weeks)} weeks until the
              assignment can start. The sponsor licence is the long step; nothing on the work visa can start before it.
            </p>
            <Timeline steps={data.timeline.steps} total={data.timeline.total_weeks} />
          </section>

          <section className="card">
            <h2>Fees</h2>
            <div className="table-wrap">
              <table className="diff-table">
                <thead><tr><th scope="col">Item</th><th scope="col">Paid by</th><th scope="col" className="num">£</th></tr></thead>
                <tbody>
                  {data.costs.items.map((c) => (
                    <tr key={c.key}>
                      <th scope="row">{c.label} <SourceLinks sources={c.sources} compact /></th>
                      <td>{c.paid_by}</td><td className="num">{money(c.amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot><tr><th scope="row">Total</th><td /><td className="num strong">{money(data.costs.total)}</td></tr></tfoot>
              </table>
            </div>
            <h3 className="sub">Optional extras</h3>
            <ul className="extras">
              {data.costs.optional_extras.map((x) => (
                <li key={x.label}>{x.label}: {amount(x.amount, x.currency)} <RuleIds ids={x.rule_ids} rules={data.rules} /></li>
              ))}
            </ul>
          </section>

          <SourcesCard rules={data.rules} />
        </>
      )}
    </div>
  );
}
