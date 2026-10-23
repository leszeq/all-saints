"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface MobileFilterDrawerProps {
  children: ReactNode;
  title: string;
  closeLabel: string;
}

export function MobileFilterDrawer({
  children,
  title,
  closeLabel,
}: MobileFilterDrawerProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) triggerRef.current?.focus();
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="inline-flex w-full items-center justify-between rounded-xl border border-gold-500/30 bg-gold-50/70 px-4 py-3 text-sm font-semibold text-burgundy-900 outline-offset-2 transition-colors hover:bg-gold-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600 sm:hidden"
        aria-expanded={open}
        aria-controls="saints-filter-panel"
        onClick={() => setOpen(true)}
      >
        <span>{title}</span>
        <span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <button
          type="button"
          aria-label={closeLabel}
          className="fixed inset-0 z-40 bg-burgundy-950/30 sm:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <div
        id="saints-filter-panel"
        role={open ? "dialog" : undefined}
        aria-label={open ? title : undefined}
        aria-modal={open ? true : undefined}
        className={open
          ? "fixed inset-y-0 right-0 z-50 w-[min(90vw,28rem)] overflow-y-auto bg-[#fffdf8] p-5 shadow-2xl sm:static sm:z-auto sm:block sm:w-auto sm:overflow-visible sm:bg-transparent sm:p-0 sm:shadow-none"
          : "hidden sm:block"}
      >
        <div className="mb-5 flex items-center justify-between border-b border-[#ded8cd] pb-4 sm:hidden">
          <h2 className="font-serif text-2xl font-semibold text-charcoal">{title}</h2>
          <button
            ref={closeRef}
            type="button"
            className="rounded-lg border border-[#ded8cd] px-3 py-2 text-sm font-semibold text-burgundy-700 outline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600"
            onClick={() => setOpen(false)}
          >
            {closeLabel}
          </button>
        </div>
        {children}
      </div>
    </>
  );
}
