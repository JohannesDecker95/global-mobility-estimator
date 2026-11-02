// Links to the official pages behind a figure or a requirement.
import type { MouseEvent } from "react";
import type { Rules, Source } from "./api";

export function SourceLinks({ sources, compact = false }: { sources: Source[]; compact?: boolean }) {
  if (!sources.length) return null;
  return (
    <span className={compact ? "sources compact" : "sources"}>
      {!compact && <span className="sources-label">Source{sources.length > 1 ? "s" : ""}: </span>}
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && (compact ? " " : " · ")}
          <a href={s.url} target="_blank" rel="noopener noreferrer" title={s.title}>
            {compact ? `[${i + 1}]` : s.title}
          </a>
        </span>
      ))}
    </span>
  );
}

/** Open the rule list of the current tab and jump to one rule. */
function jumpToRule(e: MouseEvent<HTMLAnchorElement>, id: string) {
  const scope = e.currentTarget.closest("[role=tabpanel]") ?? document;
  const target = scope.querySelector<HTMLElement>(`[data-rule="${id}"]`);
  if (!target) return;
  e.preventDefault();
  const details = target.closest("details");
  if (details) details.open = true;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.add("flash");
  window.setTimeout(() => target.classList.remove("flash"), 1600);
}

/** Rule IDs as small chips; hovering shows what each rule says, clicking jumps to its sources. */
export function RuleIds({ ids, rules }: { ids: string[]; rules?: Rules }) {
  if (!ids.length) return null;
  return (
    <span className="rule-ids">
      {ids.map((id) => (
        <a key={id} className="rule-id" href={`#rule-${id}`} title={rules?.[id]?.description ?? id}
           onClick={(e) => jumpToRule(e, id)}>{id}</a>
      ))}
    </span>
  );
}

/** Every rule a response cites, with its official pages: the list the rule chips link to. */
export function RuleList({ rules }: { rules: Rules }) {
  const ids = Object.keys(rules).sort();
  return (
    <ul className="rule-list">
      {ids.map((id) => (
        <li key={id} data-rule={id}>
          <span className="rule-id static">{id}</span> {rules[id].description}.{" "}
          {rules[id].sources.map((s, i) => (
            <span key={s.url}>
              {i > 0 && " · "}
              <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
              <span className="publisher"> ({s.publisher})</span>
            </span>
          ))}
        </li>
      ))}
    </ul>
  );
}
