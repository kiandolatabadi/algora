# Backlog — agreed, deferred

Items the owner has **approved in principle** but deliberately postponed. These
are decided in direction, not yet scheduled. See `ANATOMY.md` for the region /
stats work, which is tracked separately because it is larger than everything
here combined.

---

## A. UI and visual design — approved, deferred

### A1. Typography hierarchy
Almost every string in the app is 0.58–0.78 rem, uppercase, letterspaced, in
`--dim`. `header h1` — the app's own name — is **0.9 rem**, barely above a field
label. With no size contrast nothing leads the eye.

Fix: establish three real sizes and let colour carry state (`--dim` for labels,
`--text` for values). Give the body map visual weight; shrink the chrome.

### A2. Button hierarchy
Depth modes, gender toggle, Clear and undo are all outlined pills in `--border` —
a destructive action looks identical to a mode switch. Fix: one filled accent for
the active mode, ghost for secondary, Clear text-only until hover.

### A3. Card previews: animate on hover only
15 simultaneously moving thumbnails is visually loud and the eye cannot settle.
Animate only the hovered/focused card and hold a representative static frame for
the rest. **The machinery already exists** — `SETTLE_TICKS` in the preview loop,
built for `prefers-reduced-motion`. Make it the default and animate on hover.
Cuts CPU again as a side effect.

### A4. Depth icons → skin cross-section  ← highest value, also solves §B1
The `.dico` glyphs (dot, gradient blob, hatch square, blurred circle, dashed
ring) are decorative and do not say "deeper". Replace with a **4-step skin
cross-section**: epidermis / fat / muscle / viscera, with the active layer lit.
Prettier *and* clearer than "Sub-Q" even for clinicians. The `.dico` span already
exists in the markup, so this is purely a CSS/SVG change.

### A5. three.js upgrades, ranked by value per effort
1. **Contact shadow** — soft blurred ellipse on a transparent ground plane, or
   `ShadowMaterial` + one casting light. ~15 lines, biggest perceived-quality
   jump available. The figure currently hovers in void.
2. **Baked AO map** — bake once in Blender, ship ~50 KB, `material.aoMap` +
   `uv2`. Axilla, groin and under-chin currently read as featureless. Biggest
   *anatomical readability* gain, which matters more here than prettiness.
   **Blocked on the final mesh** (`ANATOMY.md` §6) — do not bake for a
   placeholder.
3. **Drop `computeVertexNormals()`** (in `setupModel`). Both GLBs ship authored
   `NORMAL` attributes and the code throws them away and re-smooths — across UV
   seams, where split vertices do not average, which can produce visible seam
   shading on a low-poly body. Possibly a free quality win *and* faster loading.
   Needs an A/B look.
4. **`MeshStandardMaterial` + `RoomEnvironment`/PMREM** — ships with three, needs
   no external asset, reads form far better than Phong. Gate on
   `!COARSE_POINTER` if it costs too much on phones.
5. **Fresnel rim light** via `onBeforeCompile` — separates silhouette from
   background, especially in dark theme. ~20 lines.
6. **`antialias:true` on desktop only** — nearly free with MSAA; low-poly
   silhouettes currently stair-step.
7. **three-mesh-bvh** — 20,764 brute-force triangle tests per `pointermove`
   becomes ~log n. Also makes a cheaper hover possible.

### A6. Compare mode on a phone
Splitting a 390 px viewport into two 195 px bodies is unusable. Make it a
swipe/crossfade between A and B rather than a side-by-side split.

### A7. Landscape on phones
Every phone rule is behind `@media (max-width:600px)`, which never fires in
landscape (844×390). So the safe-area insets never apply and on a notched iPhone
the Patients button sits under the notch. Needs an orientation-aware breakpoint.

**Already done** (shipped in v1.5.0, listed so they are not re-opened): WCAG AA
label contrast, the canvas/panel colour seam, global `:focus-visible`.

---

## B. Language-free interface — approved, scope agreed

**Agreed principle: split by audience, not by element.** The patient-facing
surface goes wordless; the clinician-facing surface (Patients, Settings, Save,
Compare) keeps its words. An icon-only language picker is self-defeating — it has
to name the languages.

The patient surface is only six things:

| Element | Wordless form | Status |
|---|---|---|
| **Depth** | 4-step skin cross-section glyph — see A4. **Worst current offender: "Sub-Q" is jargon in both languages.** | to do |
| Brush | already a slider; now reads in **mm** (universal). Add three dots of increasing size as the track label. | mm done in v1.5.0 |
| Intensity | already a number + colour gauge; numbers need no translation. Optionally add a **Wong-Baker FACES** row — a *validated* low-literacy pain scale, not decoration. | mostly fine |
| Undo / redo | already arrows | done |
| Clear | trash glyph | to do |
| Category headers | a small **waveform** each: pulse train (Rhythmic), flat line (Continuous), isolated spikes (Intermittent), shimmer (Sensory). Intuitive, and they mirror what the animations do. | to do |

**Keep the pain-type names as words.** The animation *is* the language-free
representation; the name exists for the clinician reading over the patient's
shoulder. Stripping it costs them and gains the patient nothing.

Not planned: a wordless Settings panel. Agreed it would add confusion rather
than remove a barrier.

---

## C. Licence — direction agreed, needs owner sign-off

**Intent:** free to use forever and to modify, never to sell.

That is a **non-commercial source-available licence**. The off-the-shelf,
lawyer-drafted licence matching it exactly is **PolyForm Noncommercial 1.0.0**.

The current `LICENSE` says the *opposite* of the intent — no copying, no
modification, evaluation only — so it needs **replacing, not amending**.

Three decisions a human has to make first:

1. **It is not open source** by the OSI definition (non-commercial clauses fail
   it). Fine — but never call it open source.
2. **"Commercial" is genuinely fuzzy.** PolyForm NC counts personal use,
   research, education, and non-commercial charitable/government work as
   noncommercial. **A clinic using this in fee-charging practice is arguably
   commercial** — and that is probably the main intended user. An explicit
   carve-out is likely needed: *"use in clinical care is permitted; resale or
   incorporation into a paid product is not."*
3. **The repo is public** with a currently-restrictive licence, which makes it
   source-available in practice regardless of wording. Either accept that or go
   private.

**Already done** (v1.5.0): removed the stray "AGPL-3.0" line in
`THIRD_PARTY_LICENSES.md` that contradicted `LICENSE`; added the in-app credits
disclosure, because CC-BY-4.0 requires attribution on the *distributed work* and
a markdown file in the repo is unreachable from the deployed app; added a
provenance canary (`_origin` in both i18n dictionaries — never rendered, do not
"clean it up").

The models' CC-BY-4.0 permits commercial use, so there is no conflict with being
stricter on Algora's own code. Commissioning an owned mesh (`ANATOMY.md` §6)
would remove the attribution obligation entirely.

---

## D. Deferred engineering, not yet discussed in depth

- **Session storage schema.** Everything lives under a single IndexedDB key, so
  every read deserialises every session's base64 texture and every write
  rewrites the whole blob. v1.5.0 added an in-memory cache as a stopgap; the real
  fix is one record per session plus a light index — and it mostly dissolves once
  strokes are authoritative (`ANATOMY.md` §7 step 4).
- **JPEG q=0.65 session textures.** Deliberately deprioritised by the owner
  (small data matters more than precision for an approximate, subjective input).
  Worth noting the one real risk: *Load → paint → re-save* recompresses, so there
  is **generational loss across visits**. Disappears once strokes are
  authoritative and the image is a thumbnail.
- **Encryption + lock screen.** Patient names sit unencrypted in IndexedDB with
  no auth and a plain-JSON export. Needed before any real patient data —
  WebCrypto keyed off a passphrase, plus enforced pseudonymisation.
- **Service-worker update prompt.** `skipWaiting()` + `clients.claim()` can swap
  versions mid-consult with no warning.
- **Backup-import validation.** Currently accepts any JSON array and replaces
  everything.
- **Tests.** There are none, and no CI. The paint pipeline, UV density, brush
  calibration and stroke pack/unpack round-trip would all pay for themselves.
- **Taxonomy ontology.** "Angor / Angina" is a *diagnosis* sitting beside
  "Throbbing", a *descriptor* — it leaks the clinician's hypothesis into the
  patient's vocabulary, which is the bias the tool exists to avoid. Aligning the
  set to SF-MPQ-2 descriptors would fix the ontology and buy construct validity.
  **Clinical judgement call, not an engineering one.**
- **Not recorded at all:** radiation direction (Shooting has no vector), temporal
  pattern per stroke, triggers, pain at rest vs movement, function/sleep impact.
- **Validation.** The core premise — that patients pick animations matching their
  pain more accurately than they pick words — is testable and untested. A ~20
  patient concordance study against SF-MPQ-2 would be worth more than any feature
  on this list, and it is what turns the project from a good app into a thing
  with evidence.
