"use client";

import { useState } from "react";

const metrics = {
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

type WindowSize = keyof typeof metrics;

const metricCards = [
  { label: "Output tokens", key: "tokens" },
  { label: "Context saved", key: "saved" },
  { label: "Build parity", key: "parity" },
  { label: "Median runtime", key: "runtime" },
] as const;

const comparisonRows = [
  ["Specification", "Frozen v1"],
  ["Functional checks", "12 / 12"],
  ["Visual parity", "100%"],
] as const;

export default function Home() {
  const [windowSize, setWindowSize] = useState<WindowSize>("7");
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  const scrollToComparison = () => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById("comparison")?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
    });
  };

  return (
    <div className="site-shell">
      <header data-testid="site-header" className="site-header">
        <a className="brand" href="#top" aria-label="Relay Bench home">
          <span className="brand-mark" aria-hidden="true">RB</span>
          Relay Bench
        </a>
        <span className="header-badge">A/B CASE STUDY</span>
      </header>

      <main id="top">
        <section data-testid="hero" className="hero" aria-labelledby="hero-title">
          <p className="eyebrow">CONTROLLED AGENT BENCHMARK</p>
          <h1 id="hero-title">Same interface.<br />Different context pressure.</h1>
          <p className="hero-body">
            Two agents build one frozen specification. We compare output fidelity,
            completion time, and total context consumed.
          </p>
          <div className="hero-actions">
            <button className="button button-primary" type="button" onClick={scrollToComparison}>
              View comparison <span aria-hidden="true">↓</span>
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
        </section>

        <section className="results" aria-labelledby="results-title">
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">MEASURED RESULTS</p>
              <h2 id="results-title">Benchmark snapshot</h2>
            </div>
            <div className="window-selector" aria-label="Benchmark run window">
              <span>WINDOW</span>
              {(["7", "30"] as const).map((size) => (
                <button
                  key={size}
                  type="button"
                  data-window={size}
                  aria-pressed={windowSize === size}
                  onClick={() => setWindowSize(size)}
                >
                  {size} RUNS
                </button>
              ))}
            </div>
          </div>

          <div data-testid="metrics-grid" className="metrics-grid">
            {metricCards.map((metric, index) => (
              <article className="metric-card" key={metric.key}>
                <span className="metric-index">0{index + 1}</span>
                <p>{metric.label}</p>
                <strong data-metric={metric.key}>{metrics[windowSize][metric.key]}</strong>
              </article>
            ))}
          </div>
        </section>

        <section id="comparison" data-testid="comparison" className="comparison" aria-labelledby="comparison-title">
          <div className="comparison-heading">
            <p className="section-kicker">SIDE BY SIDE</p>
            <h2 id="comparison-title">One brief. Two context strategies.</h2>
          </div>
          <div className="comparison-grid">
            <ComparisonColumn
              title="Baseline"
              label="STANDARD CONTEXT"
              context="18,240 tokens"
              variant="baseline"
            />
            <ComparisonColumn
              title="Codex Compact"
              label="GUARDED COMPRESSION"
              context="12,480 tokens"
              variant="compact"
            />
          </div>
        </section>

        <section data-testid="methodology" className="methodology" aria-labelledby="methodology-title">
          <div className="methodology-label">
            <span>PROTOCOL</span>
            <h2 id="methodology-title">Methodology</h2>
          </div>
          <div id="methodology-content" hidden={!methodologyOpen}>
            <p>
              Both agents receive the same files, acceptance tests, model family, and reasoning level.
              Only the compact arm receives the Codex Compact skill. Token counts use the o200k_base tokenizer.
            </p>
          </div>
          {!methodologyOpen && <p className="methodology-closed">Use the control above to inspect the study protocol.</p>}
        </section>
      </main>

      <footer data-testid="site-footer" className="site-footer">
        <p>Relay Bench</p>
        <p>CONTEXT COMPRESSION STUDY / 2026</p>
      </footer>
    </div>
  );
}

function ComparisonColumn({
  title,
  label,
  context,
  variant,
}: {
  title: string;
  label: string;
  context: string;
  variant: "baseline" | "compact";
}) {
  return (
    <article className={`comparison-column comparison-column-${variant}`}>
      <div className="comparison-column-header">
        <span className="comparison-label">{label}</span>
        <h3>{title}</h3>
      </div>
      <dl>
        {comparisonRows.map(([term, value]) => (
          <div className="comparison-row" key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
        <div className="comparison-row context-row">
          <dt>Context use</dt>
          <dd>{context}</dd>
        </div>
      </dl>
    </article>
  );
}
