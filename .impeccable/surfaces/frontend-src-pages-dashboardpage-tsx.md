---
version: 1
slug: "frontend-src-pages-dashboardpage-tsx"
primary_target: "frontend/src/pages/DashboardPage.tsx"
related_targets: ["frontend/src/components/Layout.tsx"]
---

# Dashboard (Overview) surface brief

Scope: frontend/src/pages/DashboardPage.tsx and the app shell (frontend/src/components/Layout.tsx); the other pages inherit the shell and tokens.
Mode: Operate. Audience: examiners and supervisor watching a live laptop/projector demo; the student drives. Job: see the whole pipeline (sensors → leaf-photo AI → disease risk → advice) working on one plant, with honest status labels, in one viewport.

## Direction contract

THESIS: The readings live where the sensors are. The overview is built around the project's own field unit in 3D, with live values pinned to the DHT22 shield and the two soil probes, instead of the category default of a sidebar plus a grid of identical metric tiles.

OWN-WORLD: Pinned by the user's two references. Pale grey-green canvas, near-white rounded cards (16px radius) with one soft offset shadow, a near-black ink, large light-weight numerals, pill tab navigation, a black primary button, and leaf green used as fill and marks (never as body text), with mint for positive state fields. Hanken Grotesk is self-hosted, with tabular numerals in data. Amber and red appear only where state needs them.

STORY: An examiner sees the field unit and its current conditions at once. They read the latest leaf diagnosis with its model version and confidence, and the disease-risk score on a vertical scale, labelled demo while it is one. Then they understand what to do next: simulate or receive a reading, scan a leaf, or ask the advisor.

FIRST VIEWPORT (1440x900): a top bar with the wordmark at left, pill tabs at centre (Overview, Sensors, Leaf scan, Advisor, Crops) and the plant chip and API status at right. Below it, three columns:
- Left, 320px: a Current conditions card with a 2x2 grid of large numerals and their threshold states, the data-source chip, and the black Simulate reading button with a scenario select. An Alerts card sits underneath.
- Centre, flexible: the 3D field-unit hero card, drag to orbit, with live callouts on the sensors and a metadata strip along its bottom edge (device, crop, plant, last reading).
- Right, 340px: a Leaf diagnosis card with a confidence ring gauge, the model chip and a Scan leaf action, then a Disease risk card with a vertical 0–100 scale and marker.
A full-width state banner closes the viewport.

FORM: Pinned whole by the user: two reference images (a greenhouse monitoring dashboard with a central 3D greenhouse hero, and a mint eco-score dashboard with a big score on a vertical scale) plus the answer "Our 3D field unit" for the hero. seed: none (pinned) — "use these are baseplates or inspiration for how the UI should look"; hero: "Our 3D field unit (Recommended)".

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Memorable moment
Callouts that follow the sensors as the unit rotates; a value outside its threshold turns its callout amber.

## Unresolved
- Product name in the UI: DeepCrop (repo/CAD) vs AgriHealth AI (old frontend). This build uses DeepCrop; confirm with the user.
