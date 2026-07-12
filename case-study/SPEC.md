# Relay Bench website contract

Build the same single-page responsive website in the assigned workspace. Implement only the files needed by the existing Sites starter. Do not add dependencies, external images, generated images, SVG, persistence, authentication, or additional routes.

## Product

- Browser title: `Relay Bench — Context Compression Study`
- Description: `A controlled A/B benchmark for agent context compression.`
- Brand: `Relay Bench`
- Header badge: `A/B CASE STUDY`
- Hero eyebrow: `CONTROLLED AGENT BENCHMARK`
- Hero heading: `Same interface. Different context pressure.`
- Hero body: `Two agents build one frozen specification. We compare output fidelity, completion time, and total context consumed.`
- Primary button: `View comparison`
- Secondary button: `Show methodology`

## Visual contract

- Background: `#F4F1EA`
- Primary text: `#171A1F`
- Muted text: `#64615A`
- Orange accent: `#FF5C35`
- Teal accent: `#0B7A75`
- Border: `#D8D2C4`
- Display type: `Iowan Old Style`, `Palatino Linotype`, `Palatino`, serif
- Utility type: `SFMono-Regular`, `Consolas`, `Liberation Mono`, monospace
- Maximum content width: `1180px`
- Corners: no radius larger than `8px`
- No gradients, shadows, decorative blobs, nested cards, or dark mode.

## Required structure

Use this order and these test hooks:

1. `<header data-testid="site-header">`
2. `<main>` containing:
   - hero section with `data-testid="hero"`
   - window selector with buttons `data-window="7"` and `data-window="30"`
   - metrics grid with `data-testid="metrics-grid"`
   - comparison section with `id="comparison"` and `data-testid="comparison"`
   - methodology panel with `data-testid="methodology"`
3. `<footer data-testid="site-footer">`

## Metrics

The 7-run window is active initially.

| Metric | 7 runs | 30 runs |
|---|---:|---:|
| Output tokens | `12,480` | `51,920` |
| Context saved | `31.6%` | `29.8%` |
| Build parity | `100%` | `100%` |
| Median runtime | `4m 12s` | `4m 19s` |

Each metric card must have a stable label and a value element carrying `data-metric` with one of: `tokens`, `saved`, `parity`, `runtime`.

## Comparison section

Render two equal columns:

- `Baseline` with label `STANDARD CONTEXT`
- `Codex Compact` with label `GUARDED COMPRESSION`

Each column contains rows for `Specification`, `Functional checks`, `Visual parity`, and `Context use`. Use the values:

- Specification: `Frozen v1`
- Functional checks: `12 / 12`
- Visual parity: `100%`
- Baseline context use: `18,240 tokens`
- Codex Compact context use: `12,480 tokens`

## Methodology

The methodology content starts hidden. Selecting `Show methodology` must reveal it, update `aria-expanded` to `true`, and change the button label to `Hide methodology`. Selecting it again reverses the state.

Visible methodology copy:

`Both agents receive the same files, acceptance tests, model family, and reasoning level. Only the compact arm receives the Codex Compact skill. Token counts use the o200k_base tokenizer.`

## Interaction and accessibility

- `View comparison` scrolls to `#comparison`.
- Window buttons update all four metrics and expose `aria-pressed`.
- Buttons must be keyboard accessible with visible focus states.
- Use semantic landmarks and one `<h1>`.
- Respect `prefers-reduced-motion`.
- At widths below `760px`, comparison columns and metric cards become one column.
- No horizontal overflow at `390px`.

## Acceptance

- Preserve the existing Sites package manager, build scripts, and hosting configuration.
- `npm run build` must pass.
- No console errors during interaction checks.
- All required text and hooks must exist.
- Do not describe implementation details in the page.
- Final response must state changed files, build result, and any residual risk.
