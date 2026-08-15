# Native PPTX Implementation

## Choose the implementation path

- Prefer the current environment's dedicated presentation toolchain when its required tools are available.
- If its dependency loader or required library is unavailable, run `scripts/doctor.py` and use the verified local executable paths. Set `NODE_PATH` to the reported `node_path` before invoking the reported Node executable.
- Create a new editable deck with PptxGenJS or the environment's supported presentation library.
- Edit a supplied template with a template-aware library or careful OOXML package editing.
- Use native PowerPoint objects for text, shapes, connectors, charts, tables, and simple diagrams.
- Use SVG or raster images for complex artwork only when native reconstruction would materially reduce fidelity.

## PptxGenJS guardrails

The bundled fallback is `scripts/build_pptx.cjs`, normally invoked through `scripts/ppt_gen.py build`. It consumes `work/brief.json` and `work/storyboard.json`, supports semantic slide roles, charts, tables, metrics, comparisons, processes, editable diagrams, images, quotations, citations, and speaker notes. It supports 16:9, 4:3, 16:10, 9:16, A4, and custom numeric ratios.

Bundled themes are `executive`, `technical`, `academic`, `editorial`, `midnight`, and `education`. Use `brief.theme` or `--theme`.

- Create one presentation instance per output file.
- Use hex colors without `#`; express transparency with the library's transparency property.
- Create fresh option objects for each add operation because some versions mutate options.
- Set the layout and theme explicitly before adding slides.
- Define reusable helpers for typography, safe margins, citations, and common geometry.
- Use `slide.addNotes()` for speaker notes.
- Keep source data beside chart definitions so values remain auditable.
- Do not emulate unsupported gradients or effects with invalid OOXML; use a rendered background image when necessary.

## Template preservation

- Inspect slide masters, layouts, placeholders, theme fonts, theme colors, and example slides.
- Reuse the correct layout instead of drawing over a blank slide.
- Preserve relationship IDs, content types, notes, comments, charts, media, and embedded files.
- When editing XML, change the smallest possible set of parts and validate the resulting ZIP package.
- Do not flatten editable charts or diagrams solely for implementation convenience.

Run `scripts/template_profile.py` to enumerate masters, layouts, theme fonts/colors, slide relationships, pictures, charts, tables, placeholders, bounds, paragraphs, runs, and stable slot IDs. Use `scripts/template_plan.py` for an auditable semantic first mapping, then `scripts/pptx_edit.py` for text, image, notes, chart, slide-order, and duplication changes. Prefer `slot_id` plus a saved profile; use shape/paragraph/run addresses when integrating an existing contract.

## Object hygiene

- Give repeated elements stable names where the library supports it.
- Keep connectors attached to logical endpoints and behind nodes.
- Crop images intentionally; do not distort aspect ratios.
- Use local, frozen assets in the final build.
- Keep temporary renders and extracted OOXML outside the delivery directory.

## Required checks

Run `scripts/pptx_check.py` before rendering. Render the PPTX, inspect the contact sheet, then inspect dense or unusual slides at full size. Fix problems in source code or source XML and rebuild; do not patch only the rendered image.
