# Algora — Next Steps (approved roadmap)

> **For any AI assistant / future Claude working in this repo:** the four features
> below are **approved and committed to be built** — they are not open questions or
> suggestions to re-litigate. When asked to "work on the next step", "continue", or
> "build the next feature", pick the highest-priority unstarted item here, confirm
> the specifics with the user if anything is genuinely ambiguous, and implement it.
> Update each item's **Status** as you go, and tick the acceptance checklist.

## Hard constraints (apply to every item)

- **No backend, no external API, no network at runtime.** Algora is a single-file,
  offline-first PWA (`algora.html`) served statically. Everything must run client-side.
  (An LLM-powered enhancement may be added *later, optionally*, but nothing here may
  depend on it.)
- **Privacy:** all patient data stays local (IndexedDB / localStorage). Never add
  telemetry, uploads, or third-party calls.
- **Non-diagnostic positioning:** this is a *communication* aid between patient and
  clinician (see `INTENDED_USE.md` / `README.md`). Wording in any new UI must not
  claim to diagnose or interpret.
- **Self-contained:** inline any new CSS/JS into `algora.html`; vendor any library
  under `vendor/` (no CDNs). Keep it working offline.
- **Ship discipline:** bump the in-app version (`#app-version`) **and** `CACHE_NAME`
  in `sw.js` together, then git-tag the release (see [CLAUDE.md](CLAUDE.md)).
- **Verify:** these touch canvas/WebGL/DOM that can't be exercised headlessly here —
  after building, ask the user to test in the browser before tagging a release.

---

## 1. Local plain-language pain summary (copy-paste)  — PRIORITY 1

**Status:** not started

**Goal.** Generate a deterministic, human-readable text description of the current
(or a saved) session that the user can copy-paste into a clinical note — *without*
any LLM or backend. This is the offline realisation of the "describe the pain in
words" idea.

**Why.** The clinician-facing value of the body map is the story it tells; a
copy-pasteable text version makes that portable into any EHR/notes field.

**Where.** `algora.html`:
- `summarizePaint()` already aggregates per pain type: `label`, intensity `min`/`max`,
  `depths`, `count` (sorted by frequency). This is the data source for v1.
- Per-stroke data (`packStrokes()` / `paintLog`) carries `partName` + `uvx/uvy` +
  `painId` + `depth` + `intensity` — the raw material for *location* in v2.

**Approach.**
- **v1 (no location):** a pure formatter over `summarizePaint()`. Template per type:
  `"{Type}, {intensityWord} ({min}–{max}/10), {depthWord}."` Join into a short
  paragraph or bullet list. Reuse existing `depthLabel()` and the intensity wording;
  fully localised via `window.I18N`.
- **v2 (with body region):** ⚠️ **the `partName → human region` map described here is not
  achievable with the current models.** `male_body.glb` is a **single mesh**, so every male
  stroke carries the same `partName`; the female model has four (head / body / hands /
  legs). There is no `arm_L`. Three options, in preference order:
  1. **Swap in a properly segmented anatomical model** — makes regions fall out for free
     and unlocks per-part logic generally. Preferred, and worth doing deliberately.
  2. Record the raycast's 3D hit point per stroke (`paintAt` already has `hit.point` and
     discards it), then classify by height / left-right / front-back against the model's
     bounding box. Model-agnostic, but a stroke-schema change, needs threshold calibration
     against the actual pose, and gives no regions for already-saved sessions.
  3. Reverse UV → 3D lookup for existing sessions. Most work, lowest value.
- Surface via a **"Copy summary"** button (near export / session UI) using
  `navigator.clipboard.writeText()`; show a brief "copied" confirmation.

**Acceptance.**
- [ ] v1 button copies a correct, localised text summary of the live session.
- [ ] Works from a restored/saved session too (uses stored summary or rebuilds from strokes).
- [ ] No network calls; works offline.
- [ ] v2 adds body-region phrasing via the part→region map.

---

## 2. Printable one-page clinician report  — PRIORITY 2

**Status:** not started

**Goal.** A clean, one-page printable/PDF report: body-map snapshot(s) + the #1 text
summary + the pain-type legend + patient label + date.

**Why.** The concrete "hand it to the doctor" artifact; natural companion to #1.

**Where.** `algora.html`. Body snapshot: the WebGL canvas can be captured with
`renderer.domElement.toDataURL()` (render the wanted view first). Legend + summary
already exist in the DOM (`showSessionLegend`, `summarizePaint`).

**Approach.**
- Prefer **`@media print`** + `window.print()` — no library needed. Build a hidden
  print-only container populated on demand (snapshot image, summary text, legend,
  label/date), and a print stylesheet that hides everything else.
- For a captured 3D image, render at a good fixed viewpoint (e.g. front) into an
  offscreen/known camera pose before `toDataURL()`; consider front+back.
- If true PDF is later wanted, vendor a small lib under `vendor/` — but `window.print()`
  → "Save as PDF" covers it with zero deps first.

**Acceptance.**
- [ ] "Print / Export report" produces a one-page layout with map + summary + legend + label/date.
- [ ] Prints cleanly (no app chrome) and "Save as PDF" works from the print dialog.
- [ ] Offline, no external resources.

---

## 3. Multi-session timeline / trends  — PRIORITY 3

**Status:** not started

**Goal.** A longitudinal view over a patient's saved, dated sessions: how intensity
and affected regions evolve over time.

**Why.** Sessions are already saved with dates; 2-way compare exists. A trend view
adds real clinical value across many sessions.

**Where.** `algora.html` + `DB` (IndexedDB patient store). Sessions carry `date`,
`label`, `summary`, `strokes`, `gender`.

**Approach.**
- Add a timeline/trend panel: e.g. intensity-over-time per pain type (from each
  session's `summary`), and a "most recurring regions" readout (needs the part→region
  map from #1 v2 — build that first or share it).
- Client-side charting only. If a chart library helps, vendor it under `vendor/`;
  otherwise hand-draw on a `<canvas>`/SVG. Follow the `dataviz` skill for palette/
  legibility, and keep it theme-aware (light/dark) like the rest of the app.

**Acceptance.**
- [ ] A panel lists a patient's sessions chronologically with an intensity trend.
- [ ] Recurring painful regions/types are summarised across sessions.
- [ ] Reads only local data; works offline; light + dark themes.

---

## 4. Undo / redo for painting  — PRIORITY 4 (quick win, slot in anytime)

**Status:** ✅ **done in v1.4.** Implemented as lazy per-mesh snapshots of the committed
base canvas, taken the first time a stroke touches a part (`snapshotForUndo`), committed
as one step on `pointerup`/`pointerleave` (`endUndoStroke`), capped at `UNDO_LIMIT = 15`.
`paintLog` is per-dab, so each step also stores the log length at stroke start and undo
splices back to it (the removed tail is kept on the redo entry). Eraser drags are covered
for free, since the eraser writes straight into the base canvas and the snapshot precedes
it. Stacks reset via `resetUndo()` on Clear, `switchGender`, and `restoreSession` (which
also covers entering view and compare mode). Buttons `#undo-btn`/`#redo-btn` plus
`Cmd/Ctrl+Z`, `Cmd/Ctrl+Shift+Z`, `Ctrl+Y`, ignored while focus is in a text field.

**Goal.** Undo/redo for paint strokes on the body map.

**Why.** Genuinely missing today; high-frequency quality-of-life win. Purely local.

**Where.** `algora.html` painting pipeline: strokes are committed by `bakeStroke()`
into each mesh's base canvas (`cv`/`ctx`), with `paintLog` tracking stroke tuples,
and `rebuildDisplay()` compositing the live stroke.

**Approach.**
- Maintain an undo stack of committed states. Cheapest correct approach: snapshot the
  per-part base canvas (or the compact `paintLog` up to that point) at each
  `bakeStroke()` boundary; undo restores the previous snapshot + trims `paintLog`;
  redo re-applies. Cap stack depth to bound memory (textures are 512²).
- Wire to buttons + keyboard (`Ctrl/Cmd+Z`, `Ctrl/Cmd+Shift+Z`). Call `invalidate()`
  after each so the 3D view redraws (on-demand render loop).
- Reset the stacks on clear / gender switch / session load.

**Acceptance.**
- [ ] Undo reverts the last stroke; redo re-applies it; both update the 3D body.
- [ ] Keyboard shortcuts work; stacks reset correctly on clear/switch/load.
- [ ] Bounded memory (capped history depth).

---

## Known bugs (fix when convenient)

### 🔴 Male model: paint stops at polygon edges (ASSET bug — not fixable in code)

**Status:** open, **blocked on replacing `male_body.glb`**. User-reported v1.4, with a
screenshot showing paint filling whole quads with hard edges plus stray painted polygons
away from the stroke.

**Cause — the male model's UV unwrap is shattered.** Measured directly from the GLB:

| model | tris | UV islands | tris/island | verdict |
|---|---|---|---|---|
| `male_body.glb` | 20,764 | **10,387** | **2.00** | every quad is its own island |
| female `head` | 4,462 | 5 | 892 | fine |
| female `body` | 1,424 | 2 | 712 | fine |
| female `hands` | 5,826 | 6 | 971 | fine |
| female `legs` | 3,968 | 7 | 567 | fine |

The male body is one continuous surface in 3D but **10,387 disconnected islands in UV
space** — a per-quad atlas. Quads that touch on the body are unrelated in the texture, so:
(a) paint cannot flow across a polygon edge → hard barriers, and (b) a dab spills into
whatever unrelated quads sit next to it *in the atlas* → stray painted polygons elsewhere.

It is also far below usable resolution: the median island is **7.1 texels across** at
`TEX_SIZE = 512` (p10 1.8, p90 34.9). Even a 1-texel-radius brush is comparable to a whole
island, which is why each polygon fills flat. **No brush size or blending change can fix
this** — the information simply isn't in the UV layout.

**Fix — replace the asset.** Either re-unwrap `male_body.glb` in Blender (one contiguous
unwrap with few seams) and re-export, or swap the model entirely. This converges with the
segmented-model plan in item #1: source one model that is **both** properly unwrapped
**and** segmented into named parts, and this bug plus the region-map blocker both disappear.
Raising `TEX_SIZE` would not help. Verify a candidate before adopting it: tris/island should
be in the hundreds, not ~2.

**Only in-code alternative** (not recommended): paint in 3D space instead of UV space —
per dab, find all triangles within radius R of `hit.point` and rasterise each one's UV
footprint with distance falloff. Correct and model-agnostic, but a rewrite of the painting
pipeline and it still can't beat the ~7-texel island resolution.

**Meanwhile:** the female model is correctly unwrapped and does **not** show this artifact —
worth defaulting to it, or at least using it for any demo or screen recording.

### Brush paints different real-world sizes on different body parts

**Status:** ✅ **fixed in v1.4** — see the corrected analysis below.

**Symptom.** With the same brush setting, the painted blob covers a larger/smaller area
of the body depending on where you paint.

**Cause.** The brush radius `br` is in **texture pixels** (constant), but the body is
UV-unwrapped at a **varying texel-to-world density**, so a fixed texel radius maps to
different physical sizes.

> **Correction — the fix originally written here was wrong.** It prescribed a *per-mesh*
> `uvDensity` factor. That cannot work: `male_body.glb` is a **single mesh**
> (`Low_Poly_Male_body:Group2_lambert1_0`) and `activeGender` defaults to `'male'`, so a
> per-mesh factor is one uniform scale over the whole body and changes nothing. All of the
> reported variation is *within* a mesh — which the per-mesh approach explicitly does not
> address. The female model has only four paintable meshes (head / body / hands / legs),
> so it fares little better.

**Actual fix (v1.4).** Measure density **per hit**, not per mesh:
- `triDensity(pos, uv, a, b, c)` returns `sqrt(uvArea / posArea)` for one triangle —
  UV units per object-space unit. Object space is fine because `model.scale` is a single
  uniform scalar and cancels in the ratio below.
- `setupModel` walks every triangle of every paintable mesh (`collectDensities`) and stores
  the **model-wide median** as `refDensity` on each `userData`, so the brush is calibrated
  across parts rather than per part.
- `brushRadiusAt(mesh, hit)` recomputes the density of the triangle under `hit.face` and
  returns `brushSize * BR_SCALE * clamp(d / refDensity, 0.3, 3)`. Using the median as the
  reference preserves the existing slider feel at typical density.
- `strokeBr` is locked on the stroke's **first** dab (`strokeBrSet`), since `br` now varies
  per dab but the depth hatch is applied once over the whole stroke.
- Consequence: the brush's *object-space* radius is now constant (the `d` cancels), which
  let `updateRing` become a true projected world radius — so the cursor ring finally tracks
  zoom, which it never did before.

**Residual.** Extreme UV stretch inside a single triangle is still not corrected, and the
`[0.3, 3]` clamp means pathological triangles are approximated rather than matched.

## Also-noted (not in the committed four, but worth doing)

- **Compress the body GLBs** (Draco/meshopt) — biggest remaining startup/memory win.
  `male_body.glb` is ~1.5 MB uncompressed. Requires re-export + vendoring the decoder.
- **Lazy-load the second body model** — deferred: `switchGender`, `restoreSession`,
  and `buildCompareScene` all assume both models are loaded; needs an async refactor
  (await the model before switching/restoring/cloning) + a loading state. Test live.

_See [CLAUDE.md](CLAUDE.md) for repo conventions and the performance work already shipped (v1.1 / v1.1.1)._
