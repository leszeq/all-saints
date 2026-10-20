export interface PersonTableOfContentsItem {
  id: string;
  label: string;
}

export function PersonTableOfContents({
  title,
  items,
}: {
  title: string;
  items: PersonTableOfContentsItem[];
}) {
  if (!items.length) return null;

  return (
    <nav
      aria-label={title}
      className="rounded-2xl border border-gold-500/20 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 className="font-serif text-xl font-bold text-burgundy-900">{title}</h2>
      <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        {items.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className="inline-flex min-h-9 items-center rounded-md px-2 py-1 font-medium text-burgundy-700 underline decoration-gold-500/60 underline-offset-4 outline-offset-2 transition-colors hover:text-burgundy-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600"
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
