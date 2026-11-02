// The cost form (spec section 4). Amounts are text fields on purpose: the API checks them
// and its message is shown beside the field (check 12).
import type { Dispatch, FormEvent, ReactNode, SetStateAction } from "react";
import type { FieldErrors } from "./api";
import { benefit, CATEGORIES, endOptions, monthsBetween, START_OPTIONS, TIMINGS } from "./form";
import type { BenefitRow, FormState } from "./form";
import { Help } from "./Help";

interface Props {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
  errors: FieldErrors;
  busy: boolean;
  onSubmit: () => void;
  onLoadTestCase: () => void;
  onClear: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  home_country: "Home country", home_city: "Home city", host_country: "Host country", host_city: "Host city",
  start_date: "Start date", end_date: "End date", nationality: "Nationality", marital_status: "Marital status",
  children: "Children", months_with_employer: "Months with the employer", salary_chf: "Base salary",
  bonus_chf: "Bonus", fx_chf_per_gbp: "Exchange rate", sponsor_size: "Sponsor size",
  advice_from: "Advice from", advice_to: "Advice to", benefits: "Benefits", input: "Input", request: "Request",
};

function labelFor(key: string): string {
  const m = /^benefits\.(\d+)\.(\w+)$/.exec(key);
  if (m) return `Benefit ${Number(m[1]) + 1}, ${m[2]}`;
  if (key.startsWith("options.")) return "Method setting";
  return FIELD_LABELS[key] ?? key;
}

function Field({ label, name, errors, help, hint, children, wide }: {
  label: ReactNode; name: string | string[]; errors: FieldErrors; help?: ReactNode; hint?: string;
  children: ReactNode; wide?: boolean;
}) {
  const names = Array.isArray(name) ? name : [name];
  const messages = names.flatMap((n) => errors[n] ?? []);
  return (
    <div className={`field${messages.length ? " has-error" : ""}${wide ? " wide" : ""}`}>
      <label htmlFor={names[0]}>{label}{help}</label>
      {children}
      {hint && !messages.length && <p className="hint">{hint}</p>}
      {messages.map((m) => <p key={m} className="error" role="alert">{m}</p>)}
    </div>
  );
}

function YesNo({ id, label, checked, onChange, hint }: {
  id: string; label: ReactNode; checked: boolean; onChange: (v: boolean) => void; hint?: string;
}) {
  return (
    <div className="yesno">
      <input type="checkbox" id={id} checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <label htmlFor={id}>
        <span>{label}</span>
        {hint && <span className="hint">{hint}</span>}
      </label>
    </div>
  );
}

export function CostForm({ form, setForm, errors, busy, onSubmit, onLoadTestCase, onClear }: Props) {
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));
  const setBenefit = (id: number, patch: Partial<BenefitRow>) =>
    setForm((f) => ({ ...f, benefits: f.benefits.map((b) => (b.id === id ? { ...b, ...patch } : b)) }));
  const setOption = (key: keyof FormState["options"], value: boolean) =>
    setForm((f) => ({ ...f, options: { ...f.options, [key]: value } }));

  const ends = endOptions(form.start_date);
  const months = monthsBetween(form.start_date, form.end_date);
  const errorKeys = Object.keys(errors);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  const changeStart = (start: string) => {
    // keep the length when the start moves
    const keep = months && months >= 12 && months <= 60 ? months : 24;
    const end = endOptions(start).find((o) => o.months === keep)?.iso ?? "";
    setForm((f) => ({ ...f, start_date: start, end_date: end }));
  };

  return (
    <form className="card form" onSubmit={submit} noValidate>
      <div className="form-head">
        <h2>Assignment details</h2>
        <div className="form-actions-top">
          <button type="button" className="btn ghost" onClick={onLoadTestCase}>Load test case</button>
          <button type="button" className="btn ghost" onClick={onClear}>Clear</button>
        </div>
      </div>

      {errorKeys.length > 0 && (
        <div className="error-summary" role="alert" aria-live="assertive">
          <strong>Please check {errorKeys.length === 1 ? "this field" : `these ${errorKeys.length} fields`}:</strong>
          <ul>
            {errorKeys.map((k) => errors[k].map((m) => <li key={k + m}><b>{labelFor(k)}:</b> {m}</li>))}
          </ul>
        </div>
      )}

      <fieldset>
        <legend>Where and when</legend>
        <div className="grid">
          <Field label="Home country and city" name={["home_country", "home_city"]} errors={errors}>
            <select id="home_country" value={form.home} onChange={(e) => set("home", e.target.value)}>
              <option value="CH|zurich">Switzerland, Zurich (city)</option>
            </select>
          </Field>
          <Field label="Host country and city" name={["host_country", "host_city"]} errors={errors}
                 hint="England and Northern Ireland rates">
            <select id="host_country" value={form.host} onChange={(e) => set("host", e.target.value)}>
              <option value="GB|london">United Kingdom, London</option>
            </select>
          </Field>
          <Field label="Start date" name="start_date" errors={errors}
                 hint="The 6th of a month in UK tax year 2026/27">
            <select id="start_date" value={form.start_date} onChange={(e) => changeStart(e.target.value)}>
              {START_OPTIONS.map((o) => <option key={o.iso} value={o.iso}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="End date" name="end_date" errors={errors}
                 hint={months ? `${months} months; UK tax years run 6 April to 5 April` : undefined}>
            <select id="end_date" value={form.end_date} onChange={(e) => set("end_date", e.target.value)}>
              {!ends.some((o) => o.iso === form.end_date) && <option value={form.end_date}>{form.end_date || "Choose"}</option>}
              {ends.map((o) => <option key={o.iso} value={o.iso}>{o.label} ({o.months} months)</option>)}
            </select>
          </Field>
        </div>
      </fieldset>

      <fieldset>
        <legend>Employee</legend>
        <div className="grid">
          <Field label="Nationality" name="nationality" errors={errors}>
            <select id="nationality" value={form.nationality} onChange={(e) => set("nationality", e.target.value)}>
              <option value="CH">Swiss</option>
            </select>
          </Field>
          <Field label="Marital status and children" name={["marital_status", "children"]} errors={errors}
                 hint="This version supports a single person without children">
            <div className="inline">
              <select id="marital_status" value={form.marital_status}
                      onChange={(e) => set("marital_status", e.target.value)}>
                <option value="single">Single</option>
                <option value="married">Married</option>
              </select>
              <input aria-label="Children" inputMode="numeric" value={form.children}
                     onChange={(e) => set("children", e.target.value)} />
            </div>
          </Field>
          <Field label="Months with the employer before the move" name="months_with_employer" errors={errors}
                 hint="For the visa and the Swiss posting rules">
            <input id="months_with_employer" inputMode="numeric" value={form.months_with_employer}
                   onChange={(e) => set("months_with_employer", e.target.value)} />
          </Field>
          <Field label="Base salary, CHF a year" name="salary_chf" errors={errors}>
            <input id="salary_chf" inputMode="decimal" value={form.salary_chf} placeholder="150000"
                   onChange={(e) => set("salary_chf", e.target.value)} />
          </Field>
          <Field label="Bonus, CHF a year" name="bonus_chf" errors={errors}>
            <input id="bonus_chf" inputMode="decimal" value={form.bonus_chf} placeholder="20000"
                   onChange={(e) => set("bonus_chf", e.target.value)} />
          </Field>
          <Field label="Exchange rate, CHF per £1" name="fx_chf_per_gbp" errors={errors}
                 hint="One rate for every year">
            <input id="fx_chf_per_gbp" inputMode="decimal" value={form.fx_chf_per_gbp} placeholder="1.10"
                   onChange={(e) => set("fx_chf_per_gbp", e.target.value)} />
          </Field>
        </div>
      </fieldset>

      <fieldset>
        <legend>Employer and posting</legend>
        <div className="grid">
          <Field label="UK sponsor size" name="sponsor_size" errors={errors} hint="Sets the licence fee and skills charge">
            <select id="sponsor_size" value={form.sponsor_size}
                    onChange={(e) => set("sponsor_size", e.target.value as FormState["sponsor_size"])}>
              <option value="medium_or_large">Medium or large</option>
              <option value="small">Small</option>
            </select>
          </Field>
        </div>
        <div className="checks">
          <YesNo id="sponsor_licence_held" label="UK entity already holds a sponsor licence"
                 checked={form.sponsor_licence_held} onChange={(v) => set("sponsor_licence_held", v)} />
          <YesNo id="continuing_employment" label="Swiss employment contract continues during the assignment"
                 hint="Needed for the housing relief and the Swiss posting rule"
                 checked={form.continuing_employment} onChange={(v) => set("continuing_employment", v)} />
          <YesNo id="housing_reasonable" label="Housing is reasonable for one person"
                 hint="In line with a suitable hotel; otherwise no housing relief"
                 checked={form.housing_reasonable} onChange={(v) => set("housing_reasonable", v)} />
          <YesNo id="swiss_home_kept" label="Employee keeps a home in Switzerland"
                 hint="Leaves up to 12 months of housing out of Swiss AHV"
                 checked={form.swiss_home_kept} onChange={(v) => set("swiss_home_kept", v)} />
          <YesNo id="art17_exception" label="Article 17 exception agreed by both authorities"
                 hint="Only matters above 24 months: keeps Swiss social security up to 72 months"
                 checked={form.art17_exception} onChange={(v) => set("art17_exception", v)} />
        </div>
      </fieldset>

      <fieldset>
        <legend>Benefits</legend>
        {errors.benefits && errors.benefits.map((m) => <p key={m} className="error">{m}</p>)}
        <div className="benefits">
          {form.benefits.length > 0 && (
            <div className="benefit-head" aria-hidden="true">
              <span>Benefit</span><span>Category</span><span>Amount</span><span>Currency</span><span>Timing</span><span />
            </div>
          )}
          {form.benefits.map((b, i) => {
            const err = (f: string) => errors[`benefits.${i}.${f}`] ?? [];
            const all = ["label", "category", "amount", "currency", "timing"].flatMap(err);
            return (
              <div key={b.id} className={`benefit-row${all.length ? " has-error" : ""}`}>
                <input aria-label={`Benefit ${i + 1} name`} value={b.label} placeholder="Name"
                       onChange={(e) => setBenefit(b.id, { label: e.target.value })} />
                <select aria-label={`Benefit ${i + 1} category`} value={b.category}
                        title={CATEGORIES.find((c) => c.value === b.category)?.hint}
                        onChange={(e) => setBenefit(b.id, { category: e.target.value as BenefitRow["category"] })}>
                  {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <input aria-label={`Benefit ${i + 1} amount`} inputMode="decimal" value={b.amount} placeholder="0"
                       onChange={(e) => setBenefit(b.id, { amount: e.target.value })} />
                <select aria-label={`Benefit ${i + 1} currency`} value={b.currency}
                        onChange={(e) => setBenefit(b.id, { currency: e.target.value as BenefitRow["currency"] })}>
                  <option value="GBP">GBP</option>
                  <option value="CHF">CHF</option>
                </select>
                <select aria-label={`Benefit ${i + 1} timing`} value={b.timing}
                        onChange={(e) => setBenefit(b.id, { timing: e.target.value as BenefitRow["timing"] })}>
                  {TIMINGS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <button type="button" className="btn icon" aria-label={`Remove benefit ${i + 1}`}
                        onClick={() => setForm((f) => ({ ...f, benefits: f.benefits.filter((x) => x.id !== b.id) }))}>
                  ×
                </button>
                {all.map((m) => <p key={m} className="error row-error">{m}</p>)}
              </div>
            );
          })}
          <button type="button" className="btn ghost small"
                  onClick={() => setForm((f) => ({ ...f, benefits: [...f.benefits, benefit()] }))}>
            + Add benefit
          </button>
          <p className="hint">
            The tool decides the UK tax and Swiss AHV treatment from the category and shows it as a tag in the
            results. Monthly amounts are paid every month of the stay; one-off amounts fall in the first tax year.
          </p>
        </div>
      </fieldset>

      <fieldset>
        <legend>Method settings</legend>
        <p className="hint block">
          The defaults are the tool's method. Switching one off shows a different reading; the results then list
          the default method under "Other methods" so the two can be compared.
        </p>
        <div className="checks">
          <YesNo id="opt_twr" label={<>Temporary-workplace relief for housing <Help term="relief" /></>}
                 hint="Housing is not taxable in the UK while the stay is planned for 24 months or less"
                 checked={form.options.twr_rule} onChange={(v) => setOption("twr_rule", v)} />
          <YesNo id="opt_ahv" label={<>Swiss AHV on the full assignment pay <Help term="ahv" label="AHV" /></>}
                 hint="Off: AHV on salary and bonus only, as the brief reads literally"
                 checked={form.options.ahv_full_base} onChange={(v) => setOption("ahv_full_base", v)} />
          <YesNo id="opt_pillar2" label="Employee pays into pillar 2"
                 hint="Sets the insurance allowance in the hypothetical Swiss tax"
                 checked={form.options.pillar2} onChange={(v) => setOption("pillar2", v)} />
        </div>
        <div className="grid narrow">
          <Field label="Duration advice from (months)" name="advice_from" errors={errors}>
            <input id="advice_from" inputMode="numeric" value={form.advice_from}
                   onChange={(e) => set("advice_from", e.target.value)} />
          </Field>
          <Field label="to (months)" name="advice_to" errors={errors}>
            <input id="advice_to" inputMode="numeric" value={form.advice_to}
                   onChange={(e) => set("advice_to", e.target.value)} />
          </Field>
        </div>
      </fieldset>

      <div className="form-actions">
        <button type="submit" className="btn primary" disabled={busy}>
          {busy ? "Calculating…" : "Calculate employer cost"}
        </button>
      </div>
    </form>
  );
}
