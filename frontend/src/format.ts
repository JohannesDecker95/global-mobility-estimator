// Number formatting for £ and CHF (en-GB style, thousands separators, two decimals).

const gbp = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });
const gbp0 = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 });
const plain = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const money = (s: string | number) => gbp.format(Number(s));
export const money0 = (s: string | number) => gbp0.format(Number(s));
export const chf = (s: string | number) => `CHF ${plain.format(Number(s))}`;
export const amount = (s: string | number, currency: string) => (currency === "CHF" ? chf(s) : money(s));

/** A difference with an explicit sign: +£1,234.56 or −£1,234.56. */
export function signed(s: string | number, currency = "GBP"): string {
  const n = Number(s);
  if (n === 0) return currency === "CHF" ? chf(0) : money(0);
  const body = currency === "CHF" ? chf(Math.abs(n)) : money(Math.abs(n));
  return `${n > 0 ? "+" : "−"}${body}`;
}

export const times = (s: string) => `${s}×`;
