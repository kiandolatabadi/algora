# Anatomy → words, stats and maths

**Status: designed, not started. Read this before touching region mapping.**

This is the plan for the thing the project has been blocked on: turning painted
pixels into *"left lumbar region — burning, 6/10, 84 cm²"* and into numbers that
can be compared between visits.

It is written to be picked up cold in a later session. Nothing here has been
implemented yet.

---

## 1. Why the earlier attempt failed

One wrong premise: **the body is not segmented into named parts.**

Verified against the actual assets (not the docs):

| Model | Meshes | Names |
|---|---|---|
| `male_body.glb` | **1** | `Low_Poly_Male_body:Group2_lambert1_0` |
| `low_poly_female_body__teeth__tongue_lp.glb` | 5 (4 paintable) | `head`, `body`, `hands`, `legs`, `inside` |

There is nowhere to hang a region name. This is the same false premise that made
the originally-prescribed per-**mesh** brush fix a literal no-op on the male
model — see the v1.4 entry in `CLAUDE.md`.

### The obvious fix is a trap

Splitting the mesh into ~40 named parts in Blender fails three ways:

1. **Memory.** 40 meshes × 3 canvases × 512² × 4 B = **~126 MB** of 2D canvas.
   iOS Safari evicts canvases long before that. (For scale: the female model's
   4 paintable meshes already cost 12.6 MB.)
2. **Paint seams.** `paintAt` receives only the single mesh under the cursor, so
   a brush straddling a boundary paints one side and leaves a visible gap. Every
   new boundary is a new seam.
3. **It is per-model manual work, forever.** Redone from scratch for every asset
   change — and the current models are explicitly placeholders (§6).

---

## 2. The reframe: a region-ID layer, not a segmented mesh

Keep **one mesh and one atlas per model.** Add a **region map**: an image the
same size as the paint atlas where each pixel's value encodes a region ID. It is
**never rendered** — it is a lookup table.

```
dab at uv (0.42, 0.67)  →  regionMap[texel] = 23  →  "left lumbar paraspinal"
```

One `getImageData()` at load, then O(1) array indexing per dab. Store the
resulting `regionId` on the stroke log entry.

- **~20 KB per model** (flat colour regions compress extremely well as PNG-8)
- no new meshes, no new seams, no extra draw calls, no extra canvases
- this is how games do damage zones and how body-map instruments do region
  attribution

---

## 3. Producing the region map

### Route A — geodesic Voronoi from landmarks ← **recommended**

> Recommendation changed deliberately. Hand-painting (Route B) is more accurate
> per-model, but the models are placeholders (§6). Route A **regenerates
> automatically on a new mesh** from ~25 re-placed landmarks, where hand-painting
> would have to be redone from nothing. Automation wins while the asset is in
> flux; revisit once the final mesh is locked.

1. Place ~25 landmark vertices: crown, nape, sternum, navel, and per side
   acromion, elbow, wrist, fingertip, hip, knee, ankle, toe.
2. Run Dijkstra over the mesh **edge graph** from all seeds simultaneously; each
   vertex takes its nearest seed's label. ~150 lines, milliseconds on 41 k verts.
3. Rasterize triangles into UV space with per-vertex labels → the region map.

**It must be geodesic, not Euclidean, and not bounding-box.** Surface distance is
what correctly separates the inner thigh from the opposite thigh, and the axilla
from the flank. Euclidean distance and axis-aligned boxes both fail at exactly
those places — which is the likely reason earlier attempts felt subtly wrong no
matter how the thresholds were tuned.

Then subdivide every cell by two cheap signals:

- **laterality** — sign of `x` after centering on the mid-sagittal plane
- **anterior / posterior** — sign of the **vertex normal's** `z`

That second one is worth stealing regardless of route: chest and upper back sit
at the same height inside the same region cell, and the normal direction
separates them for free, with no segmentation at all.

### Route B — paint it in Algora itself

Algora already *is* a pixel-accurate 3D paint tool with UV-correct brushes and an
eraser. Add a hidden authoring mode (`?atlas=1`):

- the card list shows **regions** instead of pain types
- painting writes a flat region-ID value into a dedicated canvas
- a button exports that canvas as PNG, which ships as an asset

Cost: ~an afternoon of code, an afternoon of painting per model. Accuracy equals
the author's anatomical knowledge, which beats any algorithm. Also self-
correcting: a wrong boundary is a 10-second fix in the same tool.

**Best combination: Route A generates the draft, Route B corrects it.** Build
Route B's authoring mode regardless — it is the correction tool, and it is how a
human validates the output of Route A.

### Route C — rig-derived (defer)

Auto-rig both models (Mixamo is free and browser-based); skin weights give a
dominant bone per vertex and Mixamo's bone names are already anatomical
(`LeftForeArm`, `RightUpLeg`). **Bonus: a rigged body can be posed**, which
matters because pain is often posture-dependent.

Costs an FBX→GLB pipeline that preserves skinning, ~+330 KB on the male model,
and the bone segmentation maps poorly onto clinical regions (nothing
distinguishes thoracic from lumbar beyond `Spine`/`Spine1`/`Spine2`). Only worth
it if **posing** becomes a product goal.

---

## 4. The region vocabulary — don't invent one

Two-level hierarchy, mapped onto validated instruments so the output is
defensible rather than bespoke:

- **~40 leaf regions** — left anterior thigh, right lumbar paraspinal, left
  plantar foot, …
- **~10 parent zones** — head/neck, upper limb L/R, thorax, abdomen, back,
  pelvis, lower limb L/R
- a mapping to the **Widespread Pain Index** 19 regions (ACR fibromyalgia
  criteria) and to the **Margolis pain-drawing** regions

Rolling up means one painting supports *"left leg"*, *"left anterior thigh"* and
a **WPI score** simultaneously, with no extra work asked of the patient.

Region names go in the existing `window.I18N` dictionary keyed by region ID, so
bilingual output is free.

---

## 5. The maths

Region IDs alone give words. Numbers need one more baked asset.

### 5a. Per-texel area map

Each atlas texel covers a different real amount of skin (same UV-density
variation that the brush calibration deals with — see `triDensity`). Rasterize
every triangle into UV space and store `worldArea / uvArea` per texel as a
`Float32Array`. 512² = 1 MB; ~50 ms at load, or precompute and ship it.

World→cm is already known: both models are normalised to **16 world units tall**
in `setupModel`, so one world unit is `BODY_CM/16` centimetres. `BODY_CM` is
currently **170** (see the brush calibration block) — a human should confirm that
reference, and decide whether it should become per-patient.

### 5b. Compute from a stroke replay, not from the colour texture

```
replay strokes → typeBuffer[texel]       (pain type index, or a bitmask)
               → intensityBuffer[texel]  (max intensity)
then integrate → area[region][type] += texelArea[texel]
```

Why replay rather than reading back the rendered texture:

- no colour-matching against the palette (which JPEG q=0.65 makes unreliable
  anyway — see §7)
- erasures and overlapping strokes are handled correctly for free
- **a per-type bitmask lets two pain types coexist in the data** even though the
  render can only show one. This quietly fixes the "overlapping pain types are
  unrepresentable" limitation as a side effect.

One pass, ~10 ms.

### 5c. What this unlocks, all from the same pass

1. **Words** — "Left lumbar region — burning, 6/10, 84 cm²", bilingual.
2. **Burden score** — Σ(area × intensity). One number that trends over time.
3. **WPI count** — how many of the 19 regions have any pain.
4. **Delta vs a previous session** — per-region signed change in area and
   intensity, rendered as a green/red tint plus a sorted table ("left lumbar
   −32 cm², right shoulder +18 cm²"). **This is what Compare mode should be**
   instead of two pictures side by side for a human to eyeball.
5. **Printable one-page report** — front/back render, region table, trend
   sparkline. The artifact a clinician actually puts in a chart.
6. **Export** — CSV for research now, FHIR `Observation` later.

---

## 6. Hard prerequisite: the body mesh is a placeholder

**Both current models are placeholders and are stylistically mismatched** (male
and female come from different artists with different conventions). The final
representation has not been chosen. This has consequences for sequencing:

- The **region map is the only mesh-dependent asset.** Everything else —
  strokes-as-truth, the area-map baker, the stats engine, the vocabulary, the
  report, the delta compare — is mesh-independent and can be built now.
- So: **build the machinery first, author the atlas last.** Do not spend a day
  hand-painting regions onto an asset that is going to be replaced.
- This is also why Route A beats Route B for now: ~25 landmark clicks to
  regenerate, versus repainting from scratch.

Measured problems with the current assets, as a spec for choosing the next one:

| | male | female |
|---|---|---|
| paintable meshes | 1 | 4 |
| triangles | 20,764 | 15,680 |
| paint resolution | **2.5 texels/cm** (1 texel = 4.0 mm) | 4.9–9.7 texels/cm (1.0–2.0 mm) |
| torso triangles | — | **1,424** (fewer than the hands' 5,826) |
| UV atlas used | 58 % of the square | ~59 % |

Requirements for the replacement:
- **one** body, two morphs (or at minimum one consistent style), so male and
  female are the same instrument
- ≥4 texels/cm **everywhere** after unwrapping (needs either a bigger atlas or a
  tighter pack — the current 42 % waste is a lot)
- triangle budget spent on the **torso and back**, not the hands
- non-mirrored UVs (both current models pass this — verified, 500/500 sampled
  mirror-pairs have distinct UVs, so laterality is safe)
- ideally owned/commissioned, to drop the permanent CC-BY attribution obligation
- `tools/check-model.py` already exists for vetting candidates; extend it with
  the texels/cm and UV-waste checks above

---

## 7. Build order

The stats cannot be retrofitted onto existing sessions while the saved artifact
is a JPEG, so the refactor has to come before the engine.

1. **Vocabulary + i18n region names** — no code dependencies, needs a human
   decision (§4)
2. **Per-texel area-map baker** — mesh-independent, pure function
3. **Geodesic Voronoi generator + `?atlas=1` correction mode** (§3) — build the
   machinery; run it for real once the final mesh lands
4. **Strokes become authoritative** — `regionId` on each stroke; replay to
   rebuild textures on load; the stored image demoted to an optional thumbnail.
   Needs a versioned session schema and a migration from v1 sessions (which can
   only keep their JPEG, since their stroke logs predate `regionId`)
5. **Stats engine** — §5b, one pass
6. **Report + delta compare** — §5c items 4–6

Steps 1–3 are independently useful and block nothing. Step 4 is the gate for
5 and 6.

---

## 8. Regulatory note — read before building §5c

`TERMS.md` positions Algora as "not a medical device", and that position is
currently sound **precisely because the app outputs no measurement**. Everything
in §5c is a measurement.

The moment the app emits scores, trends and deltas that inform treatment, the EU
MDR "not a medical device" argument gets materially harder. This is not a reason
to skip §5 — it is a reason to decide *before* building it whether Algora is:

- a **communication aid** that deliberately stays out of scope (stats stay
  descriptive, no trend lines, no scores framed as clinical indicators), or
- an **instrument** that goes through conformity assessment.

A human has to make that call. It changes what §5c is allowed to display.
