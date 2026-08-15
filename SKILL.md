---
name: ppt-gen
description: Create, revise, and validate polished presentation decks in Codex. Use when a user asks to generate or edit PPT/PPTX files, slides, pitch decks, business reports, training decks, academic presentations, conference talks, or speaker notes; transform text, Markdown, Word, PDF, URLs, data, or an existing deck into slides; apply a PowerPoint template or brand system; rebuild screenshots or slide images; or export an HTML or image-first presentation. Default to a native, editable PPTX and always render and inspect the finished deck before delivery.
---

# PPT Generator

Create presentation artifacts that are coherent, visually intentional, editable when required, and verified by rendering.

## Select the output route

Choose the route before implementation. State the choice briefly when it affects editability or delivery.

| Route | Use when | Deliverable |
| --- | --- | --- |
| Native PPTX | Default; stakeholders must edit in PowerPoint | Editable `.pptx` with native text, shapes, charts, tables, and notes |
| Template-based PPTX | A `.pptx` or `.potx` template is supplied | Editable `.pptx` preserving masters, layouts, theme, and brand assets |
| HTML deck | Rich motion, browser delivery, or source control matters more than PowerPoint editing | Self-contained `.html`, plus PDF/PPTX only when requested |
| Image-first PPTX | The user explicitly prioritizes visual fidelity over element editability | `.pptx` assembled from slide images; disclose that slide contents are flattened |
| Editable reconstruction | Images, PDF pages, or a flattened deck must become editable | Rebuilt `.pptx`; preserve complex visuals as separate images when native reconstruction is unreliable |

Do not silently substitute an HTML deck, PDF, or image-based PPTX when the user asked for an editable PowerPoint file.

## Establish the brief

Inspect all supplied source files before drafting. Infer what is safe from context and ask at most three high-impact questions only when the answers would materially change the deck:

- audience and decision or action expected;
- presentation duration or target slide count;
- brand/template requirements and required editability.

When answers are unavailable, use these defaults: 16:9, concise business presentation, native editable PPTX, restrained professional visual system, and one clear message per slide. Record important assumptions in the handoff, not on the slides.

## Build the narrative

1. Extract claims, evidence, numbers, quotations, and reusable media from the sources.
2. Define the deck's objective in one sentence.
3. Create a slide-by-slide storyboard before writing layout code. Give every content slide an action title that states its conclusion.
4. Arrange the story as context, tension or question, evidence, resolution, and next action. Adapt this structure for teaching or academic work rather than forcing a sales narrative.
5. Assign each slide a purpose, supporting evidence, and visual form. Remove slides that do not advance the argument.

Do not fabricate facts, citations, metrics, customer names, or quotations. When current research is required, use reliable sources and keep a source ledger with the URL, publisher, title, date, and the slide that uses it.

## Define the visual system

Set a compact design system before generating slides:

- canvas size and safe margins;
- one display typeface and one body typeface, with reliable fallbacks;
- neutral base colors plus one primary and one semantic accent;
- title, subtitle, body, caption, and data-label scales;
- recurring grid, spacing, chart, image, and citation treatments.

Match the visual direction to the subject and audience. Use real product imagery, diagrams, data, screenshots, or generated raster artwork when those assets communicate the content. Avoid decorative assets that do not carry meaning.

Keep layouts varied but related. Prefer a dominant visual, chart, quotation, or diagram over collections of generic cards. Do not place cards inside cards. Keep text within its container at all target sizes and never allow elements to overlap incoherently.

## Generate the deck

Use the presentation toolchain available in the current environment. If a dedicated presentation or PPTX skill is installed, read and follow it for file-format operations and rendering requirements.

For a new native deck, prefer a programmable PPTX library such as PptxGenJS. Use editable PowerPoint objects for text, simple geometry, charts, tables, connectors, and diagrams. Use SVG or raster images only where native objects would substantially reduce fidelity or reliability.

For a supplied template:

- inspect masters, layouts, placeholders, theme colors, fonts, and existing examples;
- reuse the correct layout rather than drawing a visual imitation over a blank slide;
- preserve package relationships, notes, comments, embedded media, and theme assets;
- make the smallest reliable edit when refreshing an existing deck.

For charts and tables, preserve the underlying values and units. Label the takeaway directly. Do not use a chart when a single number or short comparison communicates the point better.

For academic decks, include citations on borrowed figures and claims, keep equations legible, use one primary exhibit per results slide, and include a references slide. For consulting or executive decks, prioritize action titles, evidence density, decision implications, and a clear next step.

Add speaker notes when requested or when the deck is intended for a timed live presentation. Notes should expand the slide rather than repeat its visible text.

## Enforce slide-level quality

Check every slide against these rules:

- one primary message;
- title communicates a conclusion or useful section label;
- body copy is concise enough to present aloud;
- visual hierarchy is obvious from a thumbnail;
- important data includes units, period, and source;
- text, charts, and images remain inside the canvas and safe margins;
- no clipped text, overflow, accidental wrapping, collisions, or tiny labels;
- repeated elements align consistently across slides;
- color contrast is sufficient and meaning does not depend on color alone;
- editable deliverables remain editable.

Never leave placeholder text, broken image links, sample data, generation notes, or debugging elements in the final deck.

## Render and verify

Treat rendering as part of generation, not an optional check.

1. Validate the presentation package and its relationships when tooling is available.
2. Render the completed deck to PDF or per-slide PNG files using PowerPoint, LibreOffice, or the environment's presentation renderer.
3. Create a contact sheet or thumbnail grid and inspect the whole narrative for rhythm, density, consistency, and blank slides.
4. Inspect dense or unusual slides individually at full size.
5. Fix every visible defect and render again. Repeat until the deck is clean.
6. Open or parse the final artifact once more to confirm the expected slide count, notes, fonts, and file integrity.

If rendering is unavailable, report that limitation explicitly and perform all available structural checks. Do not claim visual verification that did not happen.

## Deliver

Return the final deck and any specifically requested companion artifacts. Keep temporary renders, extraction folders, and intermediate files out of the final delivery location.

In the handoff, state:

- the output format and whether elements are editable;
- slide count and any included notes or companion PDF;
- important assumptions, missing assets, font substitutions, or unresolved limitations;
- the verification performed.

