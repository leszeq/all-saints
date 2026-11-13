import type { ReactNode } from "react";

interface MarkdownContentProps {
  value: string;
  className?: string;
}

type MarkdownBlock =
  | { type: "paragraph"; lines: string[] }
  | { type: "heading"; level: number; text: string }
  | { type: "unordered-list"; items: string[] }
  | { type: "ordered-list"; items: string[] }
  | { type: "quote"; lines: string[] }
  | { type: "code"; language: string; value: string }
  | { type: "rule" };

const BLOCK_START = /^(?: {0,3}(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+|>\s?|```)| {0,3}(?:---+|\*\s*\*\s*\*|___+))$/;
const INLINE_TOKEN = /\[([^\]]+)\]\(([^\s)]+)(?:\s+"[^"]*")?\)|`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|~~([^~]+)~~|\*([^*]+)\*|_([^_]+)_/g;

function safeHref(value: string): string | null {
  const href = value.trim();
  if (
    /^https?:\/\//i.test(href) ||
    (href.startsWith("/") && !href.startsWith("//")) ||
    href.startsWith("#")
  ) {
    return href;
  }
  return null;
}

function renderInline(value: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokenPattern = new RegExp(INLINE_TOKEN.source, "g");
  let cursor = 0;
  let match: RegExpExecArray | null;
  let tokenIndex = 0;

  while ((match = tokenPattern.exec(value)) !== null) {
    if (match.index > cursor) nodes.push(value.slice(cursor, match.index));

    const key = `${keyPrefix}-${tokenIndex}`;
    const label = match[1];
    const href = match[2];
    if (label && href) {
      const safeUrl = safeHref(href);
      nodes.push(
        safeUrl ? (
          <a
            key={key}
            href={safeUrl}
            className="font-semibold text-burgundy-700 underline decoration-gold-500/60 underline-offset-2 hover:text-burgundy-900"
            {...(/^https?:\/\//i.test(safeUrl)
              ? { target: "_blank", rel: "noreferrer" }
              : {})}
          >
            {renderInline(label, key)}
          </a>
        ) : (
          renderInline(label, key)
        ),
      );
    } else if (match[3]) {
      nodes.push(
        <code key={key} className="rounded bg-burgundy-50 px-1.5 py-0.5 font-mono text-[0.9em] text-burgundy-900">
          {match[3]}
        </code>,
      );
    } else if (match[4] || match[5]) {
      nodes.push(<strong key={key}>{renderInline(match[4] ?? match[5] ?? "", key)}</strong>);
    } else if (match[6]) {
      nodes.push(<del key={key}>{renderInline(match[6], key)}</del>);
    } else if (match[7] || match[8]) {
      nodes.push(<em key={key}>{renderInline(match[7] ?? match[8] ?? "", key)}</em>);
    }

    cursor = match.index + match[0].length;
    tokenIndex += 1;
  }

  if (cursor < value.length) nodes.push(value.slice(cursor));
  return nodes;
}

function isBlank(line: string): boolean {
  return line.trim().length === 0;
}

function parseBlocks(value: string): MarkdownBlock[] {
  const lines = value.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    if (isBlank(lines[index])) {
      index += 1;
      continue;
    }

    const fence = lines[index].match(/^ {0,3}```\s*([\w-]+)?\s*$/);
    if (fence) {
      const language = fence[1] ?? "";
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !/^ {0,3}```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ type: "code", language, value: codeLines.join("\n") });
      continue;
    }

    const heading = lines[index].match(/^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }

    if (/^ {0,3}(?:---+|\*\s*\*\s*\*|___+)\s*$/.test(lines[index])) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }

    const unordered = lines[index].match(/^ {0,3}[-+*]\s+(.+)$/);
    if (unordered) {
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^ {0,3}[-+*]\s+(.+)$/);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push({ type: "unordered-list", items });
      continue;
    }

    const ordered = lines[index].match(/^ {0,3}\d+[.)]\s+(.+)$/);
    if (ordered) {
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^ {0,3}\d+[.)]\s+(.+)$/);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push({ type: "ordered-list", items });
      continue;
    }

    const quote = lines[index].match(/^ {0,3}>\s?(.*)$/);
    if (quote) {
      const quoteLines: string[] = [];
      while (index < lines.length) {
        const line = lines[index].match(/^ {0,3}>\s?(.*)$/);
        if (!line) break;
        quoteLines.push(line[1]);
        index += 1;
      }
      blocks.push({ type: "quote", lines: quoteLines });
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length && !isBlank(lines[index])) {
      if (paragraph.length > 0 && BLOCK_START.test(lines[index])) break;
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push({ type: "paragraph", lines: paragraph });
  }

  return blocks;
}

function renderBlock(block: MarkdownBlock, index: number): ReactNode {
  const key = `markdown-block-${index}`;
  if (block.type === "heading") {
    const Heading = block.level <= 2 ? "h3" : "h4";
    return (
      <Heading key={key} className="mt-6 font-serif text-xl font-bold text-burgundy-900 first:mt-0">
        {renderInline(block.text, key)}
      </Heading>
    );
  }
  if (block.type === "paragraph") {
    return (
      <p key={key} className="whitespace-pre-wrap leading-relaxed">
        {renderInline(block.lines.join("\n"), key)}
      </p>
    );
  }
  if (block.type === "unordered-list" || block.type === "ordered-list") {
    const List = block.type === "unordered-list" ? "ul" : "ol";
    return (
      <List key={key} className="space-y-2 pl-6 leading-relaxed marker:text-gold-700">
        {block.items.map((item, itemIndex) => (
          <li key={`${key}-${itemIndex}`}>{renderInline(item, `${key}-${itemIndex}`)}</li>
        ))}
      </List>
    );
  }
  if (block.type === "quote") {
    return (
      <blockquote key={key} className="border-l-4 border-gold-400 pl-4 italic text-stone-600">
        {renderInline(block.lines.join("\n"), key)}
      </blockquote>
    );
  }
  if (block.type === "code") {
    return (
      <pre key={key} className="overflow-x-auto rounded-xl bg-burgundy-950 p-4 text-sm text-burgundy-50">
        <code data-language={block.language || undefined}>{block.value}</code>
      </pre>
    );
  }
  return <hr key={key} className="border-gold-500/30" />;
}

export function MarkdownContent({ value, className }: MarkdownContentProps) {
  return <div className={className}>{parseBlocks(value).map(renderBlock)}</div>;
}

/** Use Markdown text safely in metadata and compact catalogue excerpts. */
export function stripMarkdown(value: string): string {
  return value
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}(?:#{1,6}|[-+*]|>+|\d+[.)])\s*/gm, "")
    .replace(/[*_~`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
