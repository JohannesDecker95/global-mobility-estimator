// The results view: method used, cost table, other methods, working, check figure,
// duration advice, immigration costs, assumptions and every source.
import { Fragment } from "react";
import type { Alternative, EstimateResult, Line, Rules } from "./api";
import { AdviceChart, REGIME_LABELS } from "./AdviceChart";
import { chf, money, signed, times } from "./format";
import { Help } from "./Help";
import { RuleIds, RuleList, SourceLinks } from "./Sources";

function Tag({ text }: { text: string }) {
  if (!text) return null;
  const kind = text.startsWith("Not taxable") ? "free" : text.startsWith("Taxable") ? "taxed" : "mixed";
  return <span className={`tag ${kind}`}>{text}</span>;
}

function LineLabel({ line }: { line: Line }) {
  return (
    <>
      <span className="line-label">{line.label}</span>
      <Tag text={line.tag} />
      {line.basis === "input"
        ? <span className="basis">your input</span>
        : <SourceLinks sources={line.sources} compact />}
    </>
  );
}

function Summary({ r }: { r: EstimateResult }) {
  const t = r.cost_table;
  return (
    <div className="stats">
      <div className="stat primary">
        <span className="stat-label">Employer cost, {r.input.months} months</span>
        <span className="stat-value">{money(t.total)}</span>
        <span className="stat-note">Cost table total, all tax years</span>
      </div>
      <div className="stat">
        <span className="stat-label">Multiple of home pay <Help term="multiple" label="the multiple of home pay" /></span>
        <span className="stat-value">{times(t.multiple)}</span>
        <span className="stat-note">{t.years.map((y, i) => `${y.label}: ${times(t.year_multiples[i])}`).join(" · ")}</span>
      </div>
      <div className="stat">
        <span className="stat-label">With immigration costs</span>
        <span className="stat-value">{money(r.all_in)}</span>
        <span className="stat-note">{money(r.per_month)} a month</span>
      </div>
    </div>
  );
}

function MethodUsed({ r }: { r: EstimateResult }) {
  const d = r.decisions;
  const changed = r.settings.filter((s) => !s.is_default);
  return (
    <section className="card">
      <h2>Method used</h2>
      {changed.length > 0 && (
        <p className="notice">
          {changed.length === 1 ? "One setting differs" : `${changed.length} settings differ`} from the tool's
          default method (marked below). "Other methods" further down shows the default result for comparison.
        </p>
      )}
      <div className="decisions">
        <div className="decision">
          <h3>Social security <Help term="coverage" label="a certificate of coverage" /></h3>
          <p className="decision-result">{d.social_security.system_name}</p>
          <p>{d.social_security.reason}</p>
          <ul className="checklist">
            {d.social_security.checks.map((c) => (
              <li key={c.test} className={c.passed ? "pass" : "fail"}>
                <span aria-hidden="true">{c.passed ? "✓" : "✗"}</span> {c.test}{" "}
                <RuleIds ids={c.rule_ids} rules={r.rules} />
              </li>
            ))}
          </ul>
        </div>
        <div className="decision">
          <h3>Housing relief <Help term="relief" label="temporary-workplace relief" /></h3>
          <p className="decision-result">{d.relief.applies ? "Applies" : "Does not apply"}</p>
          <p>{d.relief.reason}.</p>
          <RuleIds ids={d.relief.rule_ids} rules={r.rules} />
        </div>
      </div>
      <h3 className="sub">Settings</h3>
      <ul className="settings">
        {r.settings.map((s) => (
          <li key={s.key} className={s.is_default ? "" : "changed"}>
            <div className="setting-head">
              <strong>{s.label}</strong>
              <span className={`pill ${s.value ? "on" : "off"}`}>{s.value ? "On" : "Off"}</span>
              <span className="pill muted">{s.is_default ? "default" : "changed from default"}</span>
            </div>
            <p>{s.explanation}</p>
            <RuleIds ids={s.rule_ids} rules={r.rules} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function CostTableView({ r }: { r: EstimateResult }) {
  const t = r.cost_table;
  const assumed = t.years.some((y) => y.rates_assumed);
  return (
    <section className="card">
      <h2>Cost table</h2>
      <p className="muted">
        In £, per UK tax year. Each line is rounded to the penny before it is added, so the table adds up.
        Numbers in brackets link to the official source of each line.
      </p>
      <div className="table-wrap">
        <table className="cost-table">
          <thead>
            <tr>
              <th scope="col">Item</th>
              {t.years.map((y) => (
                <th key={y.label} scope="col" className="num" title={`${y.period}. ${y.rates_note}`}>
                  {y.label}{y.rates_assumed && <sup>*</sup>}
                  <span className="period">{y.months} months</span>
                </th>
              ))}
              <th scope="col" className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {t.sections.map((s) => (
              <Fragment key={s.key}>
                <tr className="section-row">
                  <th colSpan={t.years.length + 2} scope="colgroup">
                    {s.title}
                    {s.key === "host_tax_and_charges" && <Help term="grossup" label="tax on tax" />}
                    {s.key === "deductions" && <Help term="hypothetical" label="hypothetical tax" />}
                  </th>
                </tr>
                {s.lines.map((l) => (
                  <tr key={l.key}>
                    <th scope="row" className="item"><LineLabel line={l} /></th>
                    {l.amounts.map((a, i) => <td key={i} className="num">{money(a)}</td>)}
                    <td className="num strong">{money(l.total)}</td>
                  </tr>
                ))}
                <tr className="subtotal">
                  <th scope="row">Subtotal</th>
                  {s.subtotals.map((a, i) => <td key={i} className="num">{money(a)}</td>)}
                  <td className="num">{money(s.total)}</td>
                </tr>
              </Fragment>
            ))}
          </tbody>
          <tfoot>
            <tr className="grand">
              <th scope="row">Total employer cost</th>
              {t.totals.map((a, i) => <td key={i} className="num">{money(a)}</td>)}
              <td className="num">{money(t.total)}</td>
            </tr>
            <tr>
              <th scope="row">Home pay (salary and bonus)</th>
              {t.home_pay.map((a, i) => <td key={i} className="num">{money(a)}</td>)}
              <td className="num">{money(t.home_pay_total)}</td>
            </tr>
            <tr>
              <th scope="row">Multiple of home pay</th>
              {t.year_multiples.map((a, i) => <td key={i} className="num">{times(a)}</td>)}
              <td className="num strong">{times(t.multiple)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="muted small">
        {t.years.map((y) => `${y.label}: ${y.period}`).join(" · ")}
        {assumed && <><br /><sup>*</sup> Uses the 2026/27 rates: the rules file has no later tax year yet.</>}
      </p>
    </section>
  );
}

function AlternativeCard({ a, r }: { a: Alternative; r: EstimateResult }) {
  const diff = Number(a.difference);
  return (
    <article className="alt">
      <header className="alt-head">
        <div>
          <h3>{a.title}</h3>
          <p>{a.summary}</p>
        </div>
        <div className="alt-figures">
          <span className="alt-total">{money(a.total)}</span>
          <span className={`alt-diff ${diff > 0 ? "up" : diff < 0 ? "down" : ""}`}>{signed(a.difference)} vs this result</span>
          <span className="muted small">{times(a.multiple)} home pay</span>
        </div>
      </header>
      <h4>What changes</h4>
      <ul className="changed">
        {a.changed.map((c) => (
          <li key={c.key}>
            <strong>{c.label}: {c.value ? "on" : "off"}.</strong> {c.explanation}{" "}
            <RuleIds ids={c.rule_ids} rules={r.rules} />
          </li>
        ))}
      </ul>
      <div className="table-wrap">
        <table className="diff-table">
          <thead>
            <tr>
              <th scope="col">Line</th>
              <th scope="col" className="num">This result</th>
              <th scope="col" className="num">{a.title}</th>
              <th scope="col" className="num">Difference</th>
            </tr>
          </thead>
          <tbody>
            {a.lines.map((l) => (
              <tr key={l.key}>
                <th scope="row">
                  {l.label}
                  {l.main_tag !== l.alternative_tag && (
                    <span className="tag-change"><Tag text={l.main_tag} /> → <Tag text={l.alternative_tag} /></span>
                  )}
                </th>
                <td className="num">{money(l.main)}</td>
                <td className="num">{money(l.alternative)}</td>
                <td className="num strong">{signed(l.difference)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              <td className="num">{money(r.cost_table.total)}</td>
              <td className="num">{money(a.total)}</td>
              <td className="num strong">{signed(a.difference)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="muted small">
        In this reading: {a.relief_reason.replace(/\.$/, "")}; {a.social_security_reason}.
        By tax year: {r.cost_table.years.map((y, i) => `${y.label} ${signed(a.year_differences[i])}`).join(", ")}.
      </p>
    </article>
  );
}

function OtherMethods({ r }: { r: EstimateResult }) {
  if (!r.alternatives.length) return null;
  return (
    <section className="card">
      <h2>Other methods</h2>
      <p className="muted">
        The same assignment calculated with other readings of the rules. Each shows what it takes into account,
        and which lines and UK tax tags move, so the difference can be traced line by line.
      </p>
      {r.alternatives.map((a) => <AlternativeCard key={a.key} a={a} r={r} />)}
    </section>
  );
}

function CheckFigure({ r }: { r: EstimateResult }) {
  const c = r.check_figure;
  return (
    <section className="card check">
      <h2>Check against an official source</h2>
      {c ? (
        <>
          <p>
            {c.title}: the tool's figure and the calculator's figure for the same taxable incomes.
          </p>
          <div className="table-wrap">
            <table className="diff-table">
              <thead>
                <tr><th scope="col">Tax</th><th scope="col" className="num">This tool</th>
                  <th scope="col" className="num">ESTV calculator</th><th scope="col" className="num">Difference</th></tr>
              </thead>
              <tbody>
                {c.parts.map((p) => (
                  <tr key={p.label}>
                    <th scope="row">{p.label}</th>
                    <td className="num">{chf(p.tool)}</td><td className="num">{chf(p.official)}</td>
                    <td className="num">{signed(p.difference, "CHF")}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr><th scope="row">Total</th><td className="num">{chf(c.tool_total)}</td>
                  <td className="num">{chf(c.official_total)}</td><td className="num strong">{signed(c.difference, "CHF")}</td></tr>
              </tfoot>
            </table>
          </div>
          <p className="muted small">{c.note}</p>
          <SourceLinks sources={c.sources} />
        </>
      ) : (
        <p className="muted">
          The comparison with the official ESTV calculator is shown for the test case (salary and bonus of
          CHF 170,000 with pillar 2), the incomes the calculator was run with. These inputs differ, so it is hidden.
        </p>
      )}
    </section>
  );
}

function Working({ r }: { r: EstimateResult }) {
  const h = r.working.hypothetical_tax;
  return (
    <section className="card">
      <details>
        <summary><h2>Show working</h2><span className="muted">Hypothetical tax and the tax-on-tax rounds</span></summary>
        <h3 className="sub">Hypothetical Swiss tax <Help term="hypothetical" label="hypothetical tax" /></h3>
        <div className="table-wrap">
          <table className="kv">
            <tbody>
              <tr><th scope="row">Salary and bonus</th><td className="num">{chf(h.gross)}</td></tr>
              <tr><th scope="row">Employee AHV/IV/EO and ALV</th><td className="num">{chf(h.social_security)}</td></tr>
              <tr><th scope="row">Net salary</th><td className="num">{chf(h.net_salary)}</td></tr>
              <tr><th scope="row">Taxable income, federal / Zurich</th>
                <td className="num">{chf(h.federal_taxable)} / {chf(h.zurich_taxable)}</td></tr>
              <tr><th scope="row">Federal income tax</th><td className="num">{chf(h.federal)}</td></tr>
              <tr><th scope="row">Zurich basic tax</th><td className="num">{chf(h.zurich_basic)}</td></tr>
              <tr><th scope="row">Cantonal tax (95%)</th><td className="num">{chf(h.cantonal)}</td></tr>
              <tr><th scope="row">City of Zurich tax (119%)</th><td className="num">{chf(h.communal)}</td></tr>
              <tr className="strong"><th scope="row">Hypothetical income tax a year</th><td className="num">{chf(h.total)}</td></tr>
            </tbody>
          </table>
        </div>
        <SourceLinks sources={h.sources} />

        {r.working.years.map((w) => (
          <div key={w.label} className="working-year">
            <h3 className="sub">Tax on tax, {w.label} ({w.months} months) <Help term="grossup" label="tax on tax" /></h3>
            <p><code>{w.formula}</code></p>
            <p>
              Taxable pay before tax I = {money(w.taxable_pay)}. Result {money(w.uk_tax)} after {w.rounds} rounds;
              the last round moved it by {money(w.last_change)}.
            </p>
            {Number(w.ahv_extra_base_gbp) !== 0 && (
              <p>
                The assignment adds {money(w.ahv_extra_base_gbp)} ({chf(w.ahv_extra_base_chf)}) to the Swiss AHV base,
                of which {money(w.grossed_up_social_security)} is the employee contribution the employer bears, grossed up.
              </p>
            )}
            <div className="trace">
              <table>
                <thead><tr><th scope="col">Round</th><th scope="col" className="num">Result</th></tr></thead>
                <tbody>
                  {w.trace.map((t) => (
                    <tr key={t.round}><td>{t.round}</td><td className="num">{money(t.value)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <RuleIds ids={w.rule_ids} rules={r.rules} />
          </div>
        ))}
      </details>
    </section>
  );
}

function AdviceView({ r }: { r: EstimateResult }) {
  const a = r.advice;
  return (
    <section className="card">
      <h2>Duration advice</h2>
      <p className="muted">
        The full estimate, including immigration costs, for every length from {a.range.from} to {a.range.to} months,
        divided by the months. The rules change at 24 months: the housing relief ends and, without an agreed
        exception, UK National Insurance replaces Swiss social security.
      </p>
      <div className="advice-facts">
        <div><span className="stat-label">Planned, {a.planned.months} months</span>
          <span className="stat-value small">{money(a.planned.per_month)}</span><span className="stat-note">a month</span></div>
        <div><span className="stat-label">Cheapest, {a.cheapest.months} months</span>
          <span className="stat-value small">{money(a.cheapest.per_month)}</span><span className="stat-note">a month</span></div>
        <div><span className="stat-label">Cheapest from {a.planned.months} months</span>
          <span className="stat-value small">{a.cheapest_from_planned.months} months</span>
          <span className="stat-note">{money(a.cheapest_from_planned.per_month)} a month</span></div>
        {a.next_month && a.next_month_extra && (
          <div><span className="stat-label">One more month ({a.next_month.months})</span>
            <span className="stat-value small">{signed(a.next_month_extra)}</span><span className="stat-note">all-in</span></div>
        )}
      </div>
      {a.thresholds_crossed.length > 0 && (
        <p className="notice">
          Going to {a.planned.months + 1} months crosses: {a.thresholds_crossed.join("; ")}.
        </p>
      )}
      <AdviceChart rows={a.rows} planned={a.planned.months} cheapest={a.cheapest.months} />
      <details className="plain">
        <summary>All lengths</summary>
        <div className="table-wrap">
          <table className="diff-table">
            <thead>
              <tr><th scope="col">Months</th><th scope="col">Rules</th><th scope="col" className="num">Employer cost</th>
                <th scope="col" className="num">Immigration</th><th scope="col" className="num">All-in</th>
                <th scope="col" className="num">Per month</th></tr>
            </thead>
            <tbody>
              {a.rows.map((row) => (
                <tr key={row.months} className={row.months === a.planned.months ? "highlight" : ""}>
                  <td>{row.months}</td>
                  <td>{REGIME_LABELS[row.social_security === "UK" ? "uk" : row.relief ? "relief" : "swiss"]}</td>
                  <td className="num">{money(row.employer_cost)}</td><td className="num">{money(row.immigration)}</td>
                  <td className="num">{money(row.all_in)}</td><td className="num strong">{money(row.per_month)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <RuleIds ids={a.rule_ids} rules={r.rules} />
    </section>
  );
}

function ImmigrationSummary({ r, onShow }: { r: EstimateResult; onShow: () => void }) {
  const i = r.immigration;
  return (
    <section className="card">
      <div className="form-head">
        <h2>Immigration costs</h2>
        <button type="button" className="btn ghost" onClick={onShow}>Open the immigration tab</button>
      </div>
      <p className="muted">Shown separately from the cost table and included in the duration advice.</p>
      <div className="table-wrap">
        <table className="diff-table">
          <thead><tr><th scope="col">Item</th><th scope="col">Paid by</th><th scope="col" className="num">£</th></tr></thead>
          <tbody>
            {i.items.map((c) => (
              <tr key={c.key}>
                <th scope="row">{c.label} <SourceLinks sources={c.sources} compact /></th>
                <td>{c.paid_by}</td><td className="num">{money(c.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><th scope="row">Total</th><td /><td className="num strong">{money(i.total)}</td></tr></tfoot>
        </table>
      </div>
      <p><strong>Visa eligibility:</strong> {i.eligibility.summary}</p>
    </section>
  );
}

export function Results({ r, onShowImmigration }: { r: EstimateResult; onShowImmigration: () => void }) {
  return (
    <div className="results" aria-live="polite">
      {r.warnings.length > 0 && (
        <div className="warnings" role="status">
          {r.warnings.map((w) => <p key={w}><strong>Note:</strong> {w}</p>)}
        </div>
      )}
      <Summary r={r} />
      <MethodUsed r={r} />
      <CostTableView r={r} />
      <OtherMethods r={r} />
      <CheckFigure r={r} />
      <Working r={r} />
      <AdviceView r={r} />
      <ImmigrationSummary r={r} onShow={onShowImmigration} />
      <section className="card">
        <h2>Assumptions</h2>
        <ol className="assumptions">{r.assumptions.map((a) => <li key={a}>{a}</li>)}</ol>
      </section>
      <SourcesCard rules={r.rules} />
    </div>
  );
}

export function SourcesCard({ rules }: { rules: Rules }) {
  return (
    <section className="card">
      <details>
        <summary><h2>Rules and sources</h2><span className="muted">{Object.keys(rules).length} rules cited, each with its official page</span></summary>
        <RuleList rules={rules} />
      </details>
    </section>
  );
}
