// Types for the two API endpoints (estimator/api/present.py) and the calls to them.
// Money arrives as strings with two decimals; format.ts turns them into £ and CHF.

export type Money = string;
export type FieldErrors = Record<string, string[]>;

export interface Source { title: string; url: string }
export interface Citation {
  rule_id: string;
  description: string;
  sources: { title: string; publisher: string; url: string }[];
}
export type Rules = Record<string, Citation>;

export interface Line {
  key: string;
  label: string;
  tag: string;
  amounts: Money[];
  total: Money;
  basis: "rules" | "input";
  rule_ids: string[];
  sources: Source[];
}
export interface Section { key: string; title: string; lines: Line[]; subtotals: Money[]; total: Money }
export interface Year { label: string; months: number; period: string; rates_assumed: boolean; rates_note: string }
export interface CostTable {
  currency: "GBP";
  years: Year[];
  sections: Section[];
  totals: Money[];
  total: Money;
  home_pay: Money[];
  home_pay_total: Money;
  multiple: string;
  year_multiples: string[];
}

export interface Setting {
  key: string;
  label: string;
  value: boolean;
  default: boolean;
  is_default: boolean;
  explanation: string;
  rule_ids: string[];
}

export interface Decisions {
  relief: { applies: boolean; reason: string; rule_ids: string[] };
  social_security: {
    system: "CH" | "UK";
    system_name: string;
    reason: string;
    checks: { test: string; passed: boolean; rule_ids: string[] }[];
    rule_ids: string[];
  };
}

export interface AlternativeLine {
  key: string; label: string; main: Money; alternative: Money; difference: Money;
  main_tag: string; alternative_tag: string;
}
export interface Alternative {
  key: string;
  title: string;
  summary: string;
  changed: { key: string; label: string; value: boolean; explanation: string; rule_ids: string[] }[];
  totals: Money[];
  total: Money;
  multiple: string;
  difference: Money;
  year_differences: Money[];
  lines: AlternativeLine[];
  relief_reason: string;
  social_security_reason: string;
}

export interface HypotheticalTax {
  currency: "CHF";
  gross: Money; social_security: Money; net_salary: Money;
  federal_taxable: Money; zurich_taxable: Money;
  federal: Money; zurich_basic: Money; cantonal: Money; communal: Money; total: Money;
  rule_ids: string[]; sources: Source[];
}
export interface WorkingYear {
  label: string; months: number; formula: string;
  taxable_pay: Money; uk_tax: Money; rounds: number;
  trace: { round: number; value: Money }[];
  last_change: Money;
  ahv_extra_base_gbp: Money; ahv_extra_base_chf: Money; grossed_up_social_security: Money;
  rule_ids: string[];
}
export interface CheckFigure {
  title: string; currency: "CHF";
  parts: { label: string; tool: Money; official: Money; difference: Money }[];
  tool_total: Money; official_total: Money; difference: Money; note: string; how_to_check: string[];
  rule_ids: string[]; sources: Source[];
}

export interface CostItem {
  key: string; label: string; amount: Money; paid_by: "sponsor" | "employee";
  rule_ids: string[]; sources: Source[];
}
export interface EligibilityCheck { test: string; status: Status; detail: string; rule_ids: string[] }
export type Status = "met" | "not met" | "to check" | "not checked";
export interface Eligibility { status: Status; summary: string; checks: EligibilityCheck[] }

export interface AdviceRow {
  months: number; social_security: "CH" | "UK"; relief: boolean;
  employer_cost: Money; immigration: Money; all_in: Money; per_month: Money;
}
export interface Advice {
  range: { from: number; to: number };
  planned: AdviceRow;
  cheapest: AdviceRow;
  cheapest_from_planned: AdviceRow;
  next_month: AdviceRow | null;
  next_month_extra: Money | null;
  thresholds_crossed: string[];
  rows: AdviceRow[];
  rule_ids: string[];
}

export interface EstimateResult {
  input: Record<string, unknown> & { months: number };
  warnings: string[];
  decisions: Decisions;
  settings: Setting[];
  cost_table: CostTable;
  working: { hypothetical_tax: HypotheticalTax; years: WorkingYear[] };
  check_figure: CheckFigure | null;
  alternatives: Alternative[];
  immigration: { items: CostItem[]; total: Money; sponsor_total: Money; employee_total: Money; eligibility: Eligibility };
  all_in: Money;
  per_month: Money;
  advice: Advice;
  assumptions: string[];
  rules: Rules;
}

export interface Requirement {
  id: string; text: string; time: string | null;
  cost: { label: string; amount: Money; paid_by: string } | null;
  rule_ids: string[]; sources: Source[];
}
export interface TimelineStep {
  id: string; step: string; party: "employer" | "employee";
  duration: string; unit: string; start_week: string; end_week: string; skipped: boolean;
  rule_ids: string[]; sources: Source[];
}
export interface ImmigrationResult {
  input: Record<string, unknown>;
  route: { title: string; summary: string; rule_ids: string[]; sources: Source[] };
  eligibility: Eligibility;
  areas: { key: string; title: string; items: Requirement[] }[];
  timeline: { total_weeks: string; steps: TimelineStep[] };
  costs: {
    items: CostItem[];
    total: Money;
    optional_extras: { label: string; amount: Money; currency: "GBP" | "CHF"; rule_ids: string[] }[];
  };
  rules: Rules;
}

/** The API answered with field errors (HTTP 400/415/422). */
export class ApiError extends Error {
  constructor(public status: number, public errors: FieldErrors) {
    super(Object.values(errors).flat().join(" "));
  }
}

async function handle<T>(response: Response): Promise<T> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(response.status, { request: [`The server answered with HTTP ${response.status} and no JSON.`] });
  }
  if (!response.ok) {
    const errors = (body as { errors?: FieldErrors })?.errors ?? { request: [`HTTP ${response.status}`] };
    throw new ApiError(response.status, errors);
  }
  return body as T;
}

function networkError(): ApiError {
  return new ApiError(0, { request: ["The API cannot be reached. Is `python manage.py runserver` running?"] });
}

export async function postEstimate(payload: unknown): Promise<EstimateResult> {
  let response: Response;
  try {
    response = await fetch("/api/estimate/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw networkError();
  }
  return handle<EstimateResult>(response);
}

export async function getImmigration(params: Record<string, string>): Promise<ImmigrationResult> {
  let response: Response;
  try {
    response = await fetch(`/api/immigration/?${new URLSearchParams(params)}`, { headers: { Accept: "application/json" } });
  } catch {
    throw networkError();
  }
  return handle<ImmigrationResult>(response);
}
