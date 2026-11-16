---
name: DeepCrop
description: Light greenhouse-dashboard world for a tomato crop-health platform built around its own 3D field unit.
colors:
  canvas: "#E8EBE5"
  shell: "#DFE3DC"
  card: "#FAFBF8"
  tile: "#F1F3EE"
  ink: "#141814"
  muted: "#596158"
  faint: "#7C847B"
  line: "#D3D8CF"
  leaf: "#22C55E"
  leaf-deep: "#13662F"
  leaf-mint: "#DCF5E3"
  leaf-wash: "#EEF9F1"
  warn: "#B26B00"
  warn-field: "#FBEFD9"
  alert: "#C2322B"
  alert-field: "#FBE3E1"
  risk-moderate: "#E5B44A"
  risk-high: "#E0833F"
typography:
  numeral-hero:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "56px"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "-0.03em"
  numeral:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "36px"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "-0.03em"
  page-title:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.03em"
  card-title:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Hanken Grotesk Variable, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.3
rounded:
  tile: "12px"
  card: "16px"
  pill: "9999px"
spacing:
  gap: "16px"
  card-pad: "20px"
  tile-pad: "12px 14px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    rounded: "{rounded.tile}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "#2A302A"
  button-quiet:
    backgroundColor: "{colors.tile}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tile}"
    padding: "8px 14px"
  button-quiet-hover:
    backgroundColor: "{colors.shell}"
  chip:
    backgroundColor: "{colors.tile}"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
    typography: "{typography.label}"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "20px"
  tab-active:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  tab-track:
    backgroundColor: "{colors.shell}"
    rounded: "{rounded.pill}"
    padding: "4px"
---

# Design System: DeepCrop

## Overview

The dashboard is a pale grey-green greenhouse. Near-white cards float on it with one soft shadow, numbers are set large and light, and leaf green does the marking.

The signature is the project's own field unit rendered in 3D at the centre of the overview, with live readings pinned to the physical sensors: **the readings live where the sensors are**. Everything else is a calm, standard product shell around it: top pill tabs, cards, tables, charts.

The audience is examiners watching a projected demo, so the system favours large numerals, high-contrast labels, and state that reads at a distance. Every number carries its provenance: whether it is simulated or live, and whether its model is demo or trained.

## Colors

### Primary
- **Leaf** `leaf` #22C55E is for marks and fills only: gauge arcs, dots, in-range history and status dots. It is never used for body text.
- **Leaf deep** `leaf-deep` #13662F is green text on light grounds (7.2:1), and the chart line colour.

### Neutral
- **Canvas** `canvas` #E8EBE5 is the page ground. **Shell** `shell` #DFE3DC is the inset wells and the pill track.
- **Card** `card` #FAFBF8 is the card surface. **Tile** `tile` #F1F3EE is a tile inside a card.
- **Ink** `ink` #141814 is for headings, numerals and the primary button. **Muted** `muted` #596158 is secondary text (5.6:1).
- **Faint** `faint` #7C847B is for decorative icons and separators only, never text. **Line** `line` #D3D8CF is hairlines and empty dots.

### State
- **Positive field:** `leaf-mint` #DCF5E3 (the in-range banner, the "Trained model" and "Live ESP32" chips, the optimal-range chart band).
- **Warning:** `warn` #B26B00 on `warn-field` #FBEFD9, for out-of-range readings, the "Simulated" and "Demo model" chips, and low confidence.
- **Critical:** `alert` #C2322B on `alert-field` #FBE3E1, for the API offline state and inference errors.
- **Risk zones:** `leaf` (low, 0–25), `risk-moderate` (25–50), `risk-high` (50–75), `alert` (critical, 75–100). These are the backend's `score_to_risk_level` cut-offs.

### Named Rules
- **The Provenance Rule.** Every reading shows its data source and every prediction shows its model status. Simulated and demo are amber, never hidden.
- **Green Marks, Ink Speaks.** Text is ink or muted. Green text appears only as `leaf-deep` for a positive state.

## Typography

**Font:** Hanken Grotesk Variable, self-hosted through `@fontsource-variable/hanken-grotesk`, so the demo works offline. Tabular numerals (`.num`) are used wherever digits are data.

### Hierarchy
- **Hero numeral:** 56/1, weight 300, -0.03em. Used for the risk score.
- **Numeral:** 36–38/1, weight 300, -0.03em. Used for the condition tiles and chart headers (30px).
- **Page title:** 32px, weight 600, -0.03em.
- **Card title:** 19px, weight 600, -0.03em.
- **Body:** 15px/1.55, with a 72ch maximum measure for advice text.
- **Label:** 12–13px, weight 500–600, in muted. Data labels are never below 12px.

## Layout

- **Width:** a centred frame up to 1520px with a 16 / 24 / 32px side gutter.
- **Overview (xl):** three columns, `320px | 1fr | 340px`, with the 3D hero in the flexible centre and a full-width state banner closing the viewport.
- **Spacing:** a single 16px gap rhythm between cards; cards are padded 20px and tiles 12px × 14px.
- **Narrower screens:** columns stack at lg and below; the hero keeps at least 480px height (560px on phones).
- **Page headers:** a title with a one-line description, and actions aligned right.

## Elevation & Depth

Elevation is declared once, as a shadow with no border:
- `shadow-card`: `0 1px 2px rgba(20,24,20,.04), 0 8px 24px -12px rgba(20,24,20,.12)` for cards and the active tab.
- `shadow-lift`: `0 2px 4px rgba(20,24,20,.06), 0 16px 32px -16px rgba(20,24,20,.22)` for 3D callouts floating over the model.

## Shapes

Cards use a 16px radius and tiles, buttons and inputs a 12px radius. Pills (9999px) are only for tabs, chips and callouts. Dots are circles of 4–10px.

## Components

### Buttons
- **Primary:** an ink fill with card-coloured text, at most one per card.
- **Quiet:** a tile fill with ink text, for secondary actions.
- Both use a 12px radius, and disabled buttons drop to 50% opacity.

### Chips
Small pills with a 6px status dot. They are used for data source (Live ESP32, Simulated, Manual entry), model status (Trained model, Demo model, Model missing, Inference error), urgency and versions.

### Cards / Containers
Cards hold one job each, with a 19px semibold title and an optional status chip on the right. Cards are never nested; tiles inside cards use `tile` with no shadow.

### Navigation
The top bar holds the wordmark (three drawn leaflets plus "DeepCrop"), a centred pill-tab track (Overview, Sensors, Leaf scan, Advisor, Crops), and the plant chip and API status on the right. On phones, the tabs take a full-width row.

### Field unit hero (signature)
- **Model:** a WebGL render of the CAD meshes (`frontend/public/field-unit/models.json`, produced by `cad/pack_viewer.py --frontend`) on a soft radial ground, with a contact shadow.
- **Interaction:** drag to orbit, with a slow auto-rotate when reduced motion is not requested. Zoom and pan are off.
- **Callouts:** pinned to the DHT22, the moisture probe and the pH probe. They turn amber when a value is out of range, and hovering one lights its sensor.
- **Metadata strip:** a gradient band along the bottom (Crop, Plant, Device, Last reading).

### Dot history
In each condition tile, the last 12 readings are shown as columns of 4 dots, green when inside tomato's optimal band and amber outside it. Readings from `/sensors/history`; bands from `/crops/tomato` thresholds.

### Gauges and scales
- **Confidence dial:** a 240° arc, green, turning amber below 65%.
- **Risk scale:** a vertical zone bar with labels every 25, a marker at the score, and the current zone at full strength.

## Do's and Don'ts

### Do:
- Show provenance on every reading and prediction.
- Use light-weight numerals for values and `.num` for every column of digits.
- Keep the field unit at the centre of the overview; readings belong on their sensors.
- Break chart lines across gaps longer than 5 minutes, and draw tomato's optimal range as a mint band.

### Don't:
- Don't use `faint` for text, or set data labels below 12px.
- Don't use green as a text colour except `leaf-deep`.
- Don't use emoji or Unicode glyphs as icons; use lucide-react or authored SVG.
- Don't add kickers or eyebrow labels above headings.
- Don't show a device, model or reading the backend didn't return; show "—" or "None reporting".
