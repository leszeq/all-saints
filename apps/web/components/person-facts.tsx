import type { ReactNode } from "react";

export function PersonFacts({
  title,
  labels,
  birthYear,
  deathYear,
  gender,
  genderLabel,
  stateOfLife,
}: {
  title: string;
  labels: {
    birth: string;
    death: string;
    gender: string;
    state: string;
  };
  birthYear?: string | null;
  deathYear?: string | null;
  gender?: string | null;
  genderLabel?: string | null;
  stateOfLife?: string | null;
}) {
  const facts: Array<{ key: keyof typeof labels; value: string | null | undefined }> = [
    { key: "birth", value: birthYear },
    { key: "death", value: deathYear },
    { key: "gender", value: gender ? genderLabel || gender : null },
    { key: "state", value: stateOfLife },
  ];
  const visibleFacts = facts.filter(({ value }) => Boolean(value));

  if (!visibleFacts.length) return null;

  return (
    <section
      id="fakty"
      aria-labelledby="person-facts-heading"
      className="scroll-mt-24 rounded-xl border border-white/15 bg-black/10 shadow-sm"
    >
      <h2 id="person-facts-heading" className="sr-only">
        {title}
      </h2>
      <dl className="grid grid-cols-2 overflow-hidden sm:grid-cols-4">
        {visibleFacts.map(({ key, value }) => (
          <div key={key} className="border-b border-r border-white/10 bg-burgundy-900/55 px-4 py-3 last:border-r-0 sm:border-b-0">
            <dt className="text-[10px] font-bold uppercase tracking-wider text-gold-300">{labels[key]}</dt>
            <dd className="mt-1 text-sm font-semibold text-white">{value as ReactNode}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
