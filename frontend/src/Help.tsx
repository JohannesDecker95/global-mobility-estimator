// Short explanations of the terms the tool uses, behind a small "?" button.
import { useEffect, useId, useRef, useState } from "react";

export const GLOSSARY = {
  equalisation:
    "Tax equalisation: the employee pays what they would have paid at home (the hypothetical tax), and the employer pays the actual host-country tax.",
  hypothetical:
    "Hypothetical tax: the Swiss income tax and social security the employee would have paid on salary and bonus had they stayed in Zurich. It is deducted from their pay.",
  grossup:
    "Tax on tax (gross-up): UK tax the employer pays for the employee is itself taxable pay, so the tax is solved as T = UKTax(I + T), round by round until it stops changing.",
  ahv:
    "AHV/IV/EO: Swiss old-age, disability and income-compensation insurance, 5.3% each for employee and employer. ALV is unemployment insurance.",
  bik: "Benefit in kind: something the employer provides instead of cash, such as a flat. It is taxable in the UK unless an exemption applies.",
  relief:
    "Temporary-workplace relief: when a posting is planned for 24 months or less, housing near the temporary workplace is treated as a travel cost and is not taxable.",
  coverage:
    "Certificate of coverage: proves the employee stays in Swiss social security during the posting, so no UK National Insurance is due.",
  multiple: "Multiple of home pay: total employer cost divided by salary and bonus for the same period.",
  ni: "National Insurance: UK social security contributions. Employer, employee and Class 1A (on benefits in kind) contributions apply only if the employee is in the UK system.",
} as const;

export function Help({ term, label }: { term: keyof typeof GLOSSARY; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  return (
    <span className="help" ref={ref}>
      <button type="button" className="help-btn" aria-expanded={open} aria-controls={id}
              aria-label={`What is ${label ?? term}?`} onClick={() => setOpen(!open)}>?</button>
      {open && <span role="tooltip" id={id} className="help-pop">{GLOSSARY[term]}</span>}
    </span>
  );
}
