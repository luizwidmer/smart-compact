"use client";

import { useState } from "react";

type WindowKey = "7" | "30";

const metricWindows = {
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
} satisfies Record<WindowKey, Record<string, string>>;

const metrics = [
  { label: "Output tokens", key: "tokens" },
  { label: "Context saved", key: "saved" },
  { label: "Build parity", key: "parity" },
  { label: "Median runtime", key: "runtime" },
] as const;

const sharedRows = [
  ["Specification", "Frozen v1"],
  ["Functional checks", "12 / 12"],
  ["Visual parity", "100%"],
] as const;

export default function Home() {
  const [activeWindow, setActiveWindow] = useState<WindowKey>("7");
  const [methodologyVisible, setMethodologyVisible] = useState(false);

  const scrollToComparison = () => {
    document.getElementById("comparison")?.scrollIntoView({ behavior: "smooth" });
  };

  const toggleMethodology = () => {
    setMethodologyVisible((visible) => !visible);
  };

  return (
    <div className="site-shell">
      <header className="site-header" data-testid="site-header">
        <a className="brand" href="#top" aria-label="Relay Bench home">
          <span className="brand-mark" aria-hidden="true">RB</span>
          <span>Relay Bench</span>
        </a>
        <span className="case-badge">A/B CASE STUDY</span>
      </header>

      <main id="top">
        <section className="hero" data-testid="hero">
          <p className="eyebrow">CONTROLLED AGENT BENCHMARK</p>
          <h1>Same interface.<br />Different context pressure.</h1>
          <p className="hero-copy">
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
              aria-expanded={methodologyVisible}
              aria-controls="methodology-content"
              onClick={toggleMethodology}
            >
              {methodologyVisible ? "Hide methodology" : "Show methodology"}
            </button>
          </div>
        </section>

        <section className="results" aria-labelledby="results-heading">
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">MEASURED RESULTS</p>
              <h2 id="results-heading">Benchmark snapshot</h2>
            </div>
            <div className="window-selector" aria-label="Run window">
              {(["7", "30"] as WindowKey[]).map((window) => (
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
                <div className="metric-index" aria-hidden="true">0{index + 1}</div>
                <p>{metric.label}</p>
                <strong data-metric={metric.key}>{metricWindows[activeWindow][metric.key]}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className="comparison" id="comparison" data-testid="comparison" aria-labelledby="comparison-heading">
          <div className="section-heading-row comparison-heading">
            <div>
              <p className="section-kicker">SIDE BY SIDE</p>
              <h2 id="comparison-heading">Same brief. Measured difference.</h2>
            </div>
            <p className="comparison-note">7-run median</p>
          </div>

          <div className="comparison-grid">
            <article className="comparison-column">
              <div className="comparison-column-header">
                <p>STANDARD CONTEXT</p>
                <h3>Baseline</h3>
              </div>
              <dl>
                {sharedRows.map(([label, value]) => (
                  <div className="comparison-row" key={label}>
                    <dt>{label}</dt><dd>{value}</dd>
                  </div>
                ))}
                <div className="comparison-row context-row baseline-row">
                  <dt>Context use</dt><dd>18,240 tokens</dd>
                </div>
              </dl>
            </article>

            <article className="comparison-column compact-column">
              <div className="comparison-column-header">
                <p>GUARDED COMPRESSION</p>
                <h3>Codex Compact</h3>
              </div>
              <dl>
                {sharedRows.map(([label, value]) => (
                  <div className="comparison-row" key={label}>
                    <dt>{label}</dt><dd>{value}</dd>
                  </div>
                ))}
                <div className="comparison-row context-row compact-row">
                  <dt>Context use</dt><dd>12,480 tokens</dd>
                </div>
              </dl>
            </article>
          </div>
        </section>

        <section className={`methodology ${methodologyVisible ? "is-visible" : ""}`} data-testid="methodology" aria-labelledby="methodology-heading">
          <div className="methodology-label">
            <span aria-hidden="true">M</span>
            <p>METHOD NOTE</p>
          </div>
          <div>
            <h2 id="methodology-heading">Methodology</h2>
            <div id="methodology-content" hidden={!methodologyVisible}>
              <p>
                Both agents receive the same files, acceptance tests, model family,
                and reasoning level. Only the compact arm receives the Codex Compact
                skill. Token counts use the o200k_base tokenizer.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer" data-testid="site-footer">
        <p>Relay Bench</p>
        <p>Controlled context compression study · 2026</p>
      </footer>
    </div>
  );
}
