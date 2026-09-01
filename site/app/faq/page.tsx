import type { Metadata } from "next";
import { jsonLdScript } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "FAQ",
  description: "How mcphound's score is computed, what counts as a finding, and how to dispute one.",
  alternates: { canonical: "/faq" },
};

const faqs: { question: string; answer: string }[] = [
  {
    question: "How is the score computed?",
    answer:
      "Every server starts at 100. Each finding scales down the remaining score by an amount set by its severity (critical, high, medium, low) and confidence (high, medium, low) — a multiplicative decay, not a flat subtraction, so one critical finding can't zero out a server on its own, but a pile of smaller findings still compounds. A server with no findings scores 100; adding findings only ever moves the score down.",
  },
  {
    question: "Does mcphound ever run the servers it scores?",
    answer:
      "No. Every score on this site comes from static analysis of a server's published config and source — mcphound never installs, executes, or connects to a server to produce a finding.",
  },
  {
    question: "What counts as a finding?",
    answer:
      "Static analysis rules covering things like hardcoded secrets, download-and-execute launch commands, over-broad permissions, pinned-version drift, and typosquatted package names. Every rule maps to a code in the OWASP Top 10 for LLM or Agentic applications — see the full rule catalog on GitHub for exact detection logic and severity.",
  },
  {
    question: "I think a finding is wrong — how do I dispute it?",
    answer:
      'Run "mcphound feedback <rule-id> --note \\"why you think this is wrong\\"" — it prints a pre-filled GitHub issue URL with the rule and version, no network call or auth required. False-positive fixes are treated as release-blockers.',
  },
  {
    question: "What's a typosquat cluster?",
    answer:
      "A known, established MCP package paired with any published registry entries whose name is one or two characters away from it — the kind of edit a person skims past and a copy-paste doesn't catch. Each cluster page shows the exact characters that differ.",
  },
  {
    question: "How often is the registry rescanned?",
    answer:
      "The public MCP registry is polled and every tracked server rescanned once a day. Score and finding pages reflect the most recent nightly run, timestamped on each server's page.",
  },
  {
    question: "Where's the source?",
    answer:
      "mcphound is open source. The scanner is also published on PyPI and runs locally against your own MCP configs — see the GitHub repository linked in the footer for the CLI, rule definitions, and this site's code.",
  },
];

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map((faq) => ({
    "@type": "Question",
    name: faq.question,
    acceptedAnswer: { "@type": "Answer", text: faq.answer },
  })),
};

export default function FaqPage() {
  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLdScript(faqJsonLd) }}
      />
      <p className="eyebrow mb-3">frequently asked</p>
      <h1 className="mb-8 text-2xl font-semibold">How scoring and findings work</h1>

      <dl className="divide-y divide-ink-800 border-y border-ink-700">
        {faqs.map((faq) => (
          <div key={faq.question} className="py-6 first:pt-0">
            <dt className="mb-2 font-semibold text-paper">{faq.question}</dt>
            <dd className="max-w-2xl text-sm text-paper-dim">{faq.answer}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
