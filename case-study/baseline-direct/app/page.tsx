"use client";

import { useState } from "react";

const windows = {
  "7": {
    tokens: "12,480",
    saved: "31.6%",
    parity: "100%",
    runtime: "4m 12s",
  },
  "30": {
    tokens: "51,920",
    saved: "29.8%",
    parity: "100%",
    runtime: "4m 19s",
  },
} as const;

const metrics = [
  { label: "Output tokens", key: "tokens" },
  { label: "Context saved", key: "saved" },
  { label: "Build parity", key: "parity" },
  { label: "Median runtime", key: "runtime" },
] as const;

const comparisonRows = [
  { label: "Specification", baseline: "Frozen v1", compact: "Frozen v1" },
  { label: "Functional checks", baseline: "12 / 12", compact: "12 / 12" },
  { label: "Visual parity", baseline: "100%", compact: "100%" },
  {
    label: "Context use",
    baseline: "18,240 tokens",
    compact: "12,480 tokens",
  },
] as const;

export default function Home() {
  const [activeWindow, setActiveWindow] = useState<keyof typeof windows>("7");
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const activeMetrics = windows[activeWindow];

  function viewComparison() {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document
      .getElementById("comparison")
      ?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }

  return (
    <>
      <header className="site-header" data-testid="site-header">
        <div className="header-inner">
          <a className="brand" href="#top" aria-label="Relay Bench home">
            <span className="brand-mark" aria-hidden="true">R/B</span>
            Relay Bench
          </a>
          <span className="case-badge">A/B CASE STUDY</span>
        </div>
      </header>

      <main id="top">
        <section className="hero" data-testid="hero">
          <div className="hero-copy">
            <p className="eyebrow">CONTROLLED AGENT BENCHMARK</p>
            <h1>Same interface. Different context pressure.</h1>
            <p className="hero-body">
              Two agents build one frozen specification. We compare output fidelity,
              completion time, and total context consumed.
            </p>
            <div className="hero-actions">
              <button className="button button-primary" type="button" onClick={viewComparison}>
                View comparison
              </button>
              <button
                className="button button-secondary"
                type="button"
                aria-expanded={methodologyOpen}
                aria-controls="methodology-content"
                onClick={() => setMethodologyOpen((open) => !open)}
              >
                {methodologyOpen ? "Hide methodology" : "Show methodology"}
              </button>
            </div>
          </div>
          <aside className="hero-note" aria-label="Study summary">
            <span className="note-index">01 / 01</span>
            <p>Frozen input</p>
            <p>Matched environment</p>
            <p>Measured context</p>
          </aside>
        </section>

        <section className="metrics-section" aria-labelledby="metrics-heading">
          <div className="section-heading metrics-heading-row">
            <div>
              <p className="eyebrow">OBSERVED RESULTS</p>
              <h2 id="metrics-heading">Benchmark window</h2>
            </div>
            <div className="window-selector" aria-label="Select benchmark window">
              {(["7", "30"] as const).map((window) => (
                <button
                  key={window}
                  type="button"
                  data-window={window}
                  aria-pressed={activeWindow === window}
                  onClick={() => setActiveWindow(window)}
                >
                  {window} runs
                </button>
              ))}
            </div>
          </div>

          <div className="metrics-grid" data-testid="metrics-grid" aria-live="polite">
            {metrics.map((metric, index) => (
              <article className="metric-card" key={metric.key}>
                <span className="metric-number">0{index + 1}</span>
                <p>{metric.label}</p>
                <strong data-metric={metric.key}>{activeMetrics[metric.key]}</strong>
              </article>
            ))}
          </div>
        </section>

        <section id="comparison" className="comparison-section" data-testid="comparison" aria-labelledby="comparison-heading">
          <div className="section-heading">
            <p className="eyebrow">SIDE-BY-SIDE</p>
            <h2 id="comparison-heading">Same outcome. Leaner context.</h2>
          </div>
          <div className="comparison-grid">
            <article className="comparison-column baseline-column">
              <div className="comparison-title">
                <div>
                  <p>STANDARD CONTEXT</p>
                  <h3>Baseline</h3>
                </div>
                <span aria-hidden="true">A</span>
              </div>
              <dl>
                {comparisonRows.map((row) => (
                  <div className="comparison-row" key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.baseline}</dd>
                  </div>
                ))}
              </dl>
            </article>

            <article className="comparison-column compact-column">
              <div className="comparison-title">
                <div>
                  <p>GUARDED COMPRESSION</p>
                  <h3>Codex Compact</h3>
                </div>
                <span aria-hidden="true">B</span>
              </div>
              <dl>
                {comparisonRows.map((row) => (
                  <div className="comparison-row" key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.compact}</dd>
                  </div>
                ))}
              </dl>
            </article>
          </div>
        </section>

        <section className="methodology" data-testid="methodology" aria-labelledby="methodology-heading">
          <div className="methodology-label">
            <span>METHOD</span>
            <h2 id="methodology-heading">Controlled by design.</h2>
          </div>
          <div id="methodology-content" hidden={!methodologyOpen}>
            <p>
              Both agents receive the same files, acceptance tests, model family,
              and reasoning level. Only the compact arm receives the Codex Compact
              skill. Token counts use the o200k_base tokenizer.
            </p>
          </div>
          {!methodologyOpen && (
            <p className="methodology-placeholder" aria-hidden="true">
              Expand the study controls from above.
            </p>
          )}
        </section>
      </main>

      <footer className="site-footer" data-testid="site-footer">
        <p>Relay Bench</p>
        <p>Context compression, measured.</p>
      </footer>
    </>
  );
}
