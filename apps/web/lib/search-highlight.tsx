import type { ReactNode } from "react";

type TextRange = { start: number; end: number };
type NormalizedEntry = { start: number; end: number };

function normalizeForSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("pl-PL");
}

function normalizedIndex(value: string): {
  text: string;
  entries: NormalizedEntry[];
} {
  let text = "";
  const entries: NormalizedEntry[] = [];

  for (let index = 0; index < value.length; ) {
    const codePoint = value.codePointAt(index);
    if (codePoint === undefined) break;
    const character = String.fromCodePoint(codePoint);
    const end = index + character.length;
    const normalized = normalizeForSearch(character);
    text += normalized;
    for (let offset = 0; offset < normalized.length; offset += 1) {
      entries.push({ start: index, end });
    }
    index = end;
  }

  return { text, entries };
}

function mergeRanges(ranges: TextRange[]): TextRange[] {
  return ranges
    .sort((left, right) => left.start - right.start || left.end - right.end)
    .reduce<TextRange[]>((merged, range) => {
      const previous = merged.at(-1);
      if (!previous || range.start > previous.end) {
        merged.push(range);
      } else {
        previous.end = Math.max(previous.end, range.end);
      }
      return merged;
    }, []);
}

function findRanges(value: string, query: string): TextRange[] {
  const terms = query
    .trim()
    .split(/\s+/)
    .map(normalizeForSearch)
    .filter((term) => term.length >= 2);
  if (!terms.length) return [];

  const indexed = normalizedIndex(value);
  const ranges: TextRange[] = [];
  for (const term of terms) {
    let searchStart = 0;
    while (searchStart < indexed.text.length) {
      const matchStart = indexed.text.indexOf(term, searchStart);
      if (matchStart < 0) break;
      const matchEnd = matchStart + term.length;
      const first = indexed.entries[matchStart];
      const last = indexed.entries[matchEnd - 1];
      if (first && last) ranges.push({ start: first.start, end: last.end });
      searchStart = matchEnd;
    }
  }
  return mergeRanges(ranges);
}

/** Render search matches as escaped React children, preserving the source text. */
export function highlightSearchText(value: string, query: string): ReactNode {
  const ranges = findRanges(value, query);
  if (!ranges.length) return value;

  const children: ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((range) => {
    if (range.start > cursor) children.push(value.slice(cursor, range.start));
    children.push(
      <mark
        key={`${range.start}-${range.end}`}
        className="rounded-sm bg-gold-200 px-0.5 text-inherit"
      >
        {value.slice(range.start, range.end)}
      </mark>,
    );
    cursor = range.end;
  });
  if (cursor < value.length) children.push(value.slice(cursor));
  return children;
}
