"use client";

import { useState } from "react";
import { recordProductEvent } from "@/lib/analytics";

export function PersonFeedback({
  title,
  description,
  helpfulLabel,
  notHelpfulLabel,
  thanksLabel,
}: {
  title: string;
  description: string;
  helpfulLabel: string;
  notHelpfulLabel: string;
  thanksLabel: string;
}) {
  const [submitted, setSubmitted] = useState(false);

  const submit = (feedback: "helpful" | "not_helpful") => {
    if (submitted) return;
    setSubmitted(true);
    recordProductEvent("feedback_submitted", { properties: { feedback } });
  };

  return (
    <section className="rounded-2xl border border-gold-500/20 bg-gold-50/50 p-6 shadow-sm sm:p-8" aria-labelledby="person-feedback-heading">
      <h2 id="person-feedback-heading" className="font-serif text-xl font-bold text-burgundy-900">
        {title}
      </h2>
      <p className="mt-2 text-sm leading-6 text-stone-600">{submitted ? thanksLabel : description}</p>
      {!submitted && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => submit("helpful")}
            className="rounded-xl border border-burgundy-900/20 bg-white px-4 py-2 text-sm font-semibold text-burgundy-800 transition-colors hover:border-burgundy-900/50 hover:bg-burgundy-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600 focus-visible:outline-offset-2"
          >
            {helpfulLabel}
          </button>
          <button
            type="button"
            onClick={() => submit("not_helpful")}
            className="rounded-xl border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition-colors hover:border-stone-500 hover:bg-stone-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600 focus-visible:outline-offset-2"
          >
            {notHelpfulLabel}
          </button>
        </div>
      )}
    </section>
  );
}
