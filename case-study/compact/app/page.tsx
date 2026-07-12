"use client";

import { useState } from "react";

const metrics = {
  "7": [
    { label: "Output tokens", metric: "tokens", value: "12,480" },
    { label: "Context saved", metric: "saved", value: "31.6%" },
    { label: "Build parity", metric: "parity", value: "100%" },
    { label: "Median runtime", metric: "runtime", value: "4m 12s" },
  ],
  "30": [
    { label: "Output tokens", metric: "tokens", value: "51,920" },
    { label: "Context saved", metric: "saved", value: "29.8%" },
    { label: "Build parity", metric: "parity", value: "100%" },
    { label: "Median runtime", metric: "runtime", value: "4m 19s" },
  ],
} as const;

const sharedRows = [
  ["Specification", "Frozen v1"],
  ["Functional checks", "12 / 12"],
  ["Visual parity", "100%"],
] as const;

type WindowSize = keyof typeof metrics;

export default function Home() {
  const [windowSize, setWindowSize] = useState<WindowSize>("7");
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  function viewComparison() {
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    document.getElementById("comparison")?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }

  return (
    <div className="site-shell">
      <header className="site-header" data-testid="site-header">
        <div className="content header-inner">
          <a className="brand" href="#top" aria-label="Relay Bench home">
            Relay Bench
          </a>
          <span className="case-badge">A/B CASE STUDY</span>
        </div>
      </header>

      <main id="top">
        <section className="hero content" data-testid="hero">
          <div className="hero-copy">
            <p className="eyebrow">CONTROLLED AGENT BENCHMARK</p>
            <h1>Same interface. Different context pressure.</h1>
            <p className="hero-body">
              Two agents build one frozen specification. We compare output
              fidelity, completion time, and total context consumed.
            </p>
            <div className="hero-actions">
              <button className="button button-primary" onClick={viewComparison}>
                View comparison
              </button>
              <button
                className="button button-secondary"
                aria-expanded={methodologyOpen}
                aria-controls="methodology-content"
                onClick={() => setMethodologyOpen((open) => !open)}
              >
                {methodologyOpen ? "Hide methodology" : "Show methodology"}
              </button>
            </div>
          </div>
          <div className="hero-index" aria-label="Study identifier">
            <span>STUDY</span>
            <strong>RB–01</strong>
            <span>JUL / 2026</span>
          </div>
        </section>

        <section className="metrics-section content" aria-labelledby="metrics-title">
          <div className="section-heading metrics-heading">
            <div>
              <p className="section-number">01 / RESULTS</p>
              <h2 id="metrics-title">Measured across matched runs</h2>
            </div>
            <div className="window-selector" aria-label="Run window">
              {(["7", "30"] as const).map((window) => (
                <button
                  key={window}
                  data-window={window}
                  aria-pressed={windowSize === window}
                  onClick={() => setWindowSize(window)}
                >
                  {window} runs
                </button>
              ))}
            </div>
          </div>

          <div className="metrics-grid" data-testid="metrics-grid">
            {metrics[windowSize].map((item, index) => (
              <article className="metric-card" key={item.metric}>
                <span className="metric-index">0{index + 1}</span>
                <p>{item.label}</p>
                <strong data-metric={item.metric}>{item.value}</strong>
              </article>
            ))}
          </div>
        </section>

        <section
          className="comparison-section content"
          id="comparison"
          data-testid="comparison"
          aria-labelledby="comparison-title"
        >
          <div className="section-heading">
            <div>
              <p className="section-number">02 / COMPARISON</p>
              <h2 id="comparison-title">One specification, two context strategies</h2>
            </div>
          </div>

          <div className="comparison-grid">
            <article className="comparison-column baseline">
              <div className="comparison-header">
                <p>STANDARD CONTEXT</p>
                <h3>Baseline</h3>
              </div>
              <dl>
                {sharedRows.map(([label, value]) => (
                  <div className="comparison-row" key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
                <div className="comparison-row context-row">
                  <dt>Context use</dt>
                  <dd>18,240 tokens</dd>
                </div>
              </dl>
            </article>

            <article className="comparison-column compact">
              <div className="comparison-header">
                <p>GUARDED COMPRESSION</p>
                <h3>Codex Compact</h3>
              </div>
              <dl>
                {sharedRows.map(([label, value]) => (
                  <div className="comparison-row" key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
                <div className="comparison-row context-row">
                  <dt>Context use</dt>
                  <dd>12,480 tokens</dd>
                </div>
              </dl>
            </article>
          </div>
        </section>

        <section className="methodology content" data-testid="methodology">
          <div className="methodology-label">
            <p className="section-number">03 / METHODOLOGY</p>
            <h2>Controlled inputs</h2>
          </div>
          <div
            id="methodology-content"
            className="methodology-content"
            hidden={!methodologyOpen}
          >
            <p>
              Both agents receive the same files, acceptance tests, model family,
              and reasoning level. Only the compact arm receives the Codex Compact
              skill. Token counts use the o200k_base tokenizer.
            </p>
          </div>
        </section>
      </main>

      <footer className="site-footer" data-testid="site-footer">
        <div className="content footer-inner">
          <p>Relay Bench</p>
          <p>Controlled context compression study · RB–01</p>
        </div>
      </footer>
    </div>
  );
}
