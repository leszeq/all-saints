export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background" aria-live="polite">
      <div className="h-9 w-9 animate-spin rounded-full border-2 border-border border-t-primary" />
      <span className="sr-only">Trwa wczytywanie aplikacji.</span>
    </div>
  );
}
