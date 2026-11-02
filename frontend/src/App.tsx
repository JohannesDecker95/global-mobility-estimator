// Two tabs over one shared form: the cost estimate and the immigration requirements.
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getImmigration, postEstimate } from "./api";
import type { EstimateResult, FieldErrors, ImmigrationResult } from "./api";
import { CostForm } from "./CostForm";
import { emptyForm, immigrationParams, testCase, toPayload } from "./form";
import type { FormState } from "./form";
import { Help } from "./Help";
import { ImmigrationTab } from "./Immigration";
import { Results } from "./Results";

type Tab = "cost" | "immigration";

export default function App() {
  const [tab, setTab] = useState<Tab>("cost");
  const [form, setForm] = useState<FormState>(testCase);
  const [result, setResult] = useState<EstimateResult | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  const [imm, setImm] = useState<ImmigrationResult | null>(null);
  const [immErrors, setImmErrors] = useState<FieldErrors>({});
  const [immBusy, setImmBusy] = useState(false);
  const [immKey, setImmKey] = useState("");

  const calculate = useCallback(async () => {
    setBusy(true);
    setErrors({});
    try {
      const r = await postEstimate(toPayload(form));
      setResult(r);
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setResult(null);
      setErrors(e instanceof ApiError ? e.errors : { request: [String(e)] });
    } finally {
      setBusy(false);
    }
  }, [form]);

  const params = immigrationParams(form);
  const paramsKey = JSON.stringify(params);
  const loadImmigration = useCallback(async () => {
    setImmBusy(true);
    setImmErrors({});
    try {
      setImm(await getImmigration(JSON.parse(paramsKey)));
    } catch (e) {
      setImm(null);
      setImmErrors(e instanceof ApiError ? e.errors : { request: [String(e)] });
    } finally {
      setImmKey(paramsKey);   // also after an error, so a failed request is not repeated in a loop
      setImmBusy(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    if (tab === "immigration" && immKey !== paramsKey && !immBusy) void loadImmigration();
  }, [tab, immKey, paramsKey, immBusy, loadImmigration]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "cost", label: "Cost estimate" },
    { id: "immigration", label: "Immigration" },
  ];

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <div>
            <p className="eyebrow">Global Mobility Estimator</p>
            <h1>Zurich to London assignment</h1>
            <p className="lede">
              What the assignment costs the employer under tax equalisation
              <Help term="equalisation" label="tax equalisation" />, and what UK immigration requires.
              Every rate, fee and requirement links to the official page it comes from.
            </p>
          </div>
        </div>
        <nav className="tabs" role="tablist" aria-label="Sections">
          {tabs.map((t) => (
            <button key={t.id} role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id}
                    aria-controls={`panel-${t.id}`} className={tab === t.id ? "tab active" : "tab"}
                    onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <section role="tabpanel" id="panel-cost" aria-labelledby="tab-cost" hidden={tab !== "cost"}>
          <CostForm form={form} setForm={setForm} errors={errors} busy={busy}
                    onSubmit={calculate}
                    onLoadTestCase={() => { setForm(testCase()); setErrors({}); }}
                    onClear={() => { setForm(emptyForm()); setErrors({}); setResult(null); }} />
          <div ref={resultsRef}>
            {result && <Results r={result} onShowImmigration={() => setTab("immigration")} />}
          </div>
        </section>

        <section role="tabpanel" id="panel-immigration" aria-labelledby="tab-immigration"
                 hidden={tab !== "immigration"}>
          <ImmigrationTab data={imm} errors={immErrors} busy={immBusy} params={params}
                          onRefresh={loadImmigration} onEditInputs={() => setTab("cost")} />
        </section>
      </main>

      <footer className="footer">
        <p>
          Estimates for planning, based on 2026/27 rules. Not tax or legal advice: confirm the
          social security position with the Swiss compensation office and the visa route with a
          UK immigration adviser.
        </p>
      </footer>
    </div>
  );
}
