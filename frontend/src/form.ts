// The cost form's state, the candidate pack's test case, and the request it becomes.
// Amounts stay as typed text: the API checks them and answers with a message per field,
// so "15O000" shows the server's readable error instead of being silently fixed here.

export type Category =
  | "housing" | "temporary_housing" | "moving_costs"
  | "relocation_allowance" | "other_cash_allowance" | "other_benefit_in_kind";

export interface BenefitRow {
  id: number;
  label: string;
  category: Category;
  amount: string;
  currency: "GBP" | "CHF";
  timing: "monthly" | "one_off";
}

export interface FormState {
  home: string;                 // "CH|zurich"
  host: string;                 // "GB|london"
  start_date: string;           // ISO date
  end_date: string;
  nationality: string;
  marital_status: string;
  children: string;
  months_with_employer: string;
  salary_chf: string;
  bonus_chf: string;
  fx_chf_per_gbp: string;
  sponsor_size: "medium_or_large" | "small";
  sponsor_licence_held: boolean;
  continuing_employment: boolean;
  housing_reasonable: boolean;
  swiss_home_kept: boolean;
  art17_exception: boolean;
  advice_from: string;
  advice_to: string;
  benefits: BenefitRow[];
  options: { twr_rule: boolean; ahv_full_base: boolean; pillar2: boolean };
}

export const CATEGORIES: { value: Category; label: string; hint: string }[] = [
  { value: "housing", label: "Housing", hint: "Rent the employer pays for the home in the host city" },
  { value: "temporary_housing", label: "Temporary housing", hint: "Serviced flat or hotel while moving in" },
  { value: "moving_costs", label: "Moving costs", hint: "Flights, shipping and removal paid to suppliers" },
  { value: "relocation_allowance", label: "Relocation cash allowance", hint: "Cash paid to the employee for the move" },
  { value: "other_cash_allowance", label: "Other cash allowance", hint: "Any other allowance paid in cash" },
  { value: "other_benefit_in_kind", label: "Other benefit in kind", hint: "Any other benefit the employer provides" },
];

export const TIMINGS = [
  { value: "monthly", label: "Monthly for the whole stay" },
  { value: "one_off", label: "One-off at the start" },
] as const;

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];

function iso(year: number, month0: number, day: number): string {
  return `${year}-${String(month0 + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** The 6th of a month, `offset` months after April 2026. */
function startOf(offset: number): { iso: string; label: string } {
  const n = 3 + offset;
  const year = 2026 + Math.floor(n / 12);
  const m = n % 12;
  return { iso: iso(year, m, 6), label: `6 ${MONTHS[m]} ${year}` };
}

/** Allowed starts: the 6th of each month from April 2026 to March 2027 (UK tax year 2026/27). */
export const START_OPTIONS = Array.from({ length: 12 }, (_, k) => startOf(k));

export function monthsBetween(start: string, end: string): number | null {
  const s = /^(\d{4})-(\d{2})-(\d{2})$/.exec(start);
  const e = /^(\d{4})-(\d{2})-(\d{2})$/.exec(end);
  if (!s || !e) return null;
  return (Number(e[1]) - Number(s[1])) * 12 + (Number(e[2]) - Number(s[2]));
}

/** End dates for a start: the 5th of a month, 12 to 60 months later. */
export function endOptions(start: string): { iso: string; label: string; months: number }[] {
  const s = /^(\d{4})-(\d{2})-06$/.exec(start);
  if (!s) return [];
  const out = [];
  for (let months = 12; months <= 60; months++) {
    const n = Number(s[2]) - 1 + months;
    const year = Number(s[1]) + Math.floor(n / 12);
    const m = n % 12;
    out.push({ iso: iso(year, m, 5), label: `5 ${MONTHS[m]} ${year}`, months });
  }
  return out;
}

let nextId = 1;
export function benefit(label = "", category: Category = "other_cash_allowance", amount = "",
                        currency: "GBP" | "CHF" = "GBP", timing: "monthly" | "one_off" = "one_off"): BenefitRow {
  return { id: nextId++, label, category, amount, currency, timing };
}

/** The candidate pack's test case. */
export function testCase(): FormState {
  return {
    home: "CH|zurich", host: "GB|london",
    start_date: "2026-04-06", end_date: "2028-04-05",
    nationality: "CH", marital_status: "single", children: "0",
    months_with_employer: "36",
    salary_chf: "150000", bonus_chf: "20000", fx_chf_per_gbp: "1.10",
    sponsor_size: "medium_or_large", sponsor_licence_held: false,
    continuing_employment: true, housing_reasonable: true, swiss_home_kept: false, art17_exception: false,
    advice_from: "12", advice_to: "60",
    benefits: [
      benefit("Housing in London", "housing", "3000", "GBP", "monthly"),
      benefit("Relocation allowance", "relocation_allowance", "5000", "CHF", "one_off"),
      benefit("Moving costs (flights, shipping)", "moving_costs", "6000", "GBP", "one_off"),
      benefit("Temporary housing, first 4 weeks", "temporary_housing", "4000", "GBP", "one_off"),
    ],
    options: { twr_rule: true, ahv_full_base: true, pillar2: true },
  };
}

/** An empty form with the supported choices preselected. */
export function emptyForm(): FormState {
  return {
    ...testCase(),
    months_with_employer: "", salary_chf: "", bonus_chf: "", fx_chf_per_gbp: "",
    benefits: [],
  };
}

const blankToNull = (s: string) => (s.trim() === "" ? null : s.trim());

/** The JSON body of POST /api/estimate/. */
export function toPayload(f: FormState) {
  const [home_country, home_city] = f.home.split("|");
  const [host_country, host_city] = f.host.split("|");
  return {
    home_country, home_city, host_country, host_city,
    start_date: f.start_date, end_date: f.end_date,
    nationality: f.nationality, marital_status: f.marital_status,
    children: blankToNull(f.children) ?? 0,
    months_with_employer: blankToNull(f.months_with_employer),
    salary_chf: blankToNull(f.salary_chf),
    bonus_chf: blankToNull(f.bonus_chf) ?? "0",
    fx_chf_per_gbp: blankToNull(f.fx_chf_per_gbp),
    sponsor_size: f.sponsor_size,
    sponsor_licence_held: f.sponsor_licence_held,
    continuing_employment: f.continuing_employment,
    housing_reasonable: f.housing_reasonable,
    swiss_home_kept: f.swiss_home_kept,
    art17_exception: f.art17_exception,
    advice_from: blankToNull(f.advice_from) ?? 12,
    advice_to: blankToNull(f.advice_to) ?? 60,
    benefits: f.benefits.map(({ label, category, amount, currency, timing }) =>
      ({ label, category, amount: blankToNull(amount), currency, timing })),
    options: f.options,
  };
}

/** Query of GET /api/immigration/, taken from the same form so both tabs agree. */
export function immigrationParams(f: FormState): Record<string, string> {
  const params: Record<string, string> = {
    nationality: f.nationality,
    host: f.host.split("|")[0],
    sponsor_size: f.sponsor_size,
    sponsor_licence_held: String(f.sponsor_licence_held),
  };
  const months = monthsBetween(f.start_date, f.end_date);
  if (months !== null && months >= 12 && months <= 60) params.months = String(months);
  const salary = Number(f.salary_chf);
  const fx = Number(f.fx_chf_per_gbp);
  if (f.salary_chf.trim() && Number.isFinite(salary) && salary >= 0 && Number.isFinite(fx) && fx > 0) {
    params.salary_gbp = (salary / fx).toFixed(2);
  }
  if (/^\d+$/.test(f.months_with_employer.trim())) params.months_with_employer = f.months_with_employer.trim();
  return params;
}
