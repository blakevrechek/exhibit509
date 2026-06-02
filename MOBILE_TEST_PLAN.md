# Mobile — Real-Device Test Plan

The sandbox has no browser and no egress, so every mobile change below must be
confirmed by a human on the **live deploy** (`https://exhibit509.com`) after the
new service worker installs (hard-reload once, then refresh).

## Devices / orientations to cover
- iPhone (Safari) — the iOS focus-zoom + `pointer:coarse` checks matter most here.
- Android phone (Chrome).
- Small tablet (iPad portrait ~768px and landscape).
- Each phone in **portrait and landscape**.

## Breakpoints in play
- **≤640px** — phone layout: bottom tab bar, hamburger hidden, bottom-sheet school panel, sticky table columns.
- **≤760px** — tablet card/grid reflow (`.dp-grid`, `.tr-grid`, `.sg-cols` → single column).
- **`pointer:coarse`** — touch devices of any width: form controls forced to ≥16px.
- **landscape + max-height:500px + pointer:coarse** — slim tab bar + taller sheet.

## Checklist

### 1. iOS focus-zoom (≥16px inputs)
- [ ] Tap the **Match** LSAT and GPA selects — page must **not** zoom in.
- [ ] Tap the **map search** box — no zoom.
- [ ] Net-price calc: tap LSAT/uGPA number inputs and the **in-state** `<select>` — no zoom.
- [ ] Desktop unchanged: those controls keep their compact size with a mouse.

### 2. Bottom-sheet school panel (the `.open`/`.hidden` fix)
- [ ] Tap a map pin on a phone → the sheet **slides up** from the bottom (previously it stayed off-screen).
- [ ] Tap **✕** → the sheet **slides back down** and the map is fully visible.
- [ ] Open a school, then another → second school's sheet opens at the default height.
- [ ] Desktop regression: the right-side panel still shows the empty "No school selected" state on load, slides in on pin click, and the **School Info »/«** collapse button still hides/shows it.

### 3. Drag-to-resize grip
- [ ] With the sheet open, **drag the header down** a little and release → snaps back.
- [ ] **Drag down hard** (past ~110px) → sheet dismisses (same as ✕).
- [ ] **Drag up** → sheet expands to near-full height (`.sp-expanded`); a hard drag-down from expanded returns to default height before dismissing.
- [ ] Tapping the **Overview** tab or **✕** inside the header still works (taps pass through, not hijacked by drag).
- [ ] After resizing, the map re-measures (no gray strip).

### 4. Sticky first column on wide tables
- [ ] **Compare** page on a phone: scroll the table sideways → the first column (metric label) stays pinned with a drop-shadow edge.
- [ ] **Net-price calc** table: scroll sideways → the school-name column stays pinned.
- [ ] Light theme: pinned column background is light (not a dark block).

### 5. Landscape phones
- [ ] Rotate to landscape: the bottom tab bar is slimmer and the sheet uses the reclaimed height.
- [ ] No content is trapped under the tab bar; the map still fills.

### 6. General
- [ ] Bottom tab bar (Map / Schools / Match / Compare / More) navigates correctly; active tab highlighted; Compare badge shows the pinned count.
- [ ] Map basemap loads and stays (cartocdn tiles 200, not intercepted) after a hard-reload + a few refreshes.
- [ ] No console errors on load or on opening/closing the sheet.
</content>
</invoke>
