---
name: ppt-gen
description: Create, revise, convert, reconstruct, and validate polished presentation decks in Codex. Use when a user asks for PPT/PPTX files, slides, pitch decks, business or consulting reports, product launches, training decks, academic presentations, conference talks, speaker notes, or branded presentations; wants to transform text, Markdown, Word, PDF, URLs, research, or data into slides; needs to apply or update a PowerPoint template; wants an HTML or image-first deck; needs to convert an existing PPTX to web; or wants screenshots, PDFs, or flattened slides rebuilt as editable PowerPoint. Route deliberately between native PPTX, template PPTX, HTML, image-first, and editable reconstruction, then render and inspect the final artifact before delivery.
---

# PPT Generator

Build presentation artifacts through a source-first, storyboard-first, render-verified workflow. Default to a native editable 16:9 PPTX unless the delivery contract requires another route.

## Start every task

1. Inspect every supplied source, template, deck, image, and data file before drafting.
2. Determine the audience, objective, expected decision or action, duration or slide count, language, brand constraints, and editability requirement. Ask at most three questions only when the answers materially change the deck.
3. Run `python3 scripts/doctor.py` when the environment or toolchain is unknown. If the environment's dependency-loader tool is unavailable, treat `doctor.py` as the supported fallback and use the reported executable and `node_path` values.
4. Select an output route and disclose any editability tradeoff before implementation.
5. Create a clean workspace with `python3 scripts/init_deck.py <project-dir> --title "..." --route <route>` when the task does not already have an organized project directory.

Use these defaults when information is unavailable: native editable PPTX, 16:9, concise professional tone, one primary message per slide, and a restrained visual system appropriate to the subject.

## Select the output route

Read [references/routes.md](references/routes.md) whenever route selection or conversion is involved.

| Route | Choose when | Required reference |
| --- | --- | --- |
| Native PPTX | Default; stakeholders must edit in PowerPoint | [references/pptx-implementation.md](references/pptx-implementation.md) |
| Template PPTX | A `.pptx` or `.potx` controls brand and layouts | [references/pptx-implementation.md](references/pptx-implementation.md) |
| HTML deck | Browser delivery, interaction, motion, or source control dominates | [references/non-native-routes.md](references/non-native-routes.md) |
| Image-first PPTX | The user explicitly accepts flattened contents for visual freedom | [references/non-native-routes.md](references/non-native-routes.md) |
| Editable reconstruction | Images, PDF pages, or flattened slides must become editable | [references/non-native-routes.md](references/non-native-routes.md) |

Do not silently substitute HTML, PDF, or slide images when the user asked for editable PowerPoint.

## Build the narrative

Read [references/story-content.md](references/story-content.md) for evidence extraction, source tracking, storyboard fields, and scenario structures.

1. Extract claims, evidence, quotations, numbers, and reusable media.
2. Record external evidence in `work/sources.md`. Preserve units, dates, methodology, and uncertainty.
3. Define the deck objective and core message in one sentence each.
4. Complete `work/storyboard.json` before writing layout code. Give content slides action titles that state their conclusions.
5. Review the full story for gaps, redundancy, and overload. Remove or split weak slides.

Never fabricate facts, citations, customer names, performance metrics, or quotations. When current facts are required, research them with reliable sources before building the deck.

## Define the visual system

Read [references/visual-design.md](references/visual-design.md) before designing a new deck or substantially restyling one.

Define the canvas, safe margins, grid, spacing, typography, palette, image treatment, chart treatment, and citation style. Match the visual language to the audience and subject. Prefer real product imagery, meaningful diagrams, data, or deliberate typography over decorative filler. Keep layouts varied but related and make the primary message obvious at thumbnail size.

When the user requests a template, brand style, or visual options, read [references/templates.md](references/templates.md). Run `python3 scripts/templates.py stats` to inspect catalog coverage, then use `python3 scripts/templates.py search "<terms>"` to shortlist native PPTX, HTML, Marp, or Slidev sources. Fetch only the selected permissively licensed source, inspect it before execution, record its commit, and verify the adapted deck independently. Do not copy example content or assume that a repository license grants trademark rights.

## Generate

Use the presentation toolchain available in the current environment. If a dedicated PPTX or presentation artifact skill is installed, read and follow it for file operations and its render requirements when its required tools are available. If those tools are not exposed or fail to initialize, record the limitation and fall back to a verified local route reported by `doctor.py`; for bundled Node modules, set `NODE_PATH` to the reported `node_path` value.

For native PPTX:

- prefer editable text, shapes, connectors, charts, tables, and diagrams;
- preserve masters, layouts, themes, notes, comments, relationships, charts, and media when using a template;
- keep underlying chart values and units auditable;
- add speaker notes when requested or useful for a timed live presentation;
- keep frozen local copies of every final asset.

For HTML, image-first, and reconstruction work, follow the selected route's confirmation, asset, editability, and verification rules in [references/non-native-routes.md](references/non-native-routes.md).

## Verify

Read [references/qa-delivery.md](references/qa-delivery.md) for the complete release checklist.

For PPTX output, run:

```bash
python3 scripts/pptx_check.py path/to/deck.pptx
python3 scripts/render_deck.py path/to/deck.pptx --output-dir path/to/rendered --clean
```

Then inspect the contact sheet for deck-wide rhythm and inspect dense or unusual slides at full size. Fix every visible defect in the source and rerender. Repeat until there are no unexplained structural errors, clipped text, overflow, collisions, tiny labels, broken crops, font failures, placeholder content, or incoherent overlaps.

Treat structural checks and visual checks as complementary. If rendering is unavailable, report that limitation and do not claim visual verification.

## Non-negotiable quality gates

- Keep one primary message per slide.
- Make titles useful conclusions or clear section labels.
- Keep content concise enough to present aloud.
- Keep all content inside the canvas and safe margins.
- Include units, period, and source for important data.
- Cite borrowed academic figures and claims on the slide and include references when appropriate.
- Preserve editability promised to the user.
- Remove placeholders, sample data, broken links, generation notes, and debug artifacts.
- Never deliver a deck that has not been opened or parsed after the final write.

## Deliver

Return only the requested final artifacts and useful source files. Keep temporary renders, extracted OOXML, browser profiles, and intermediate assets out of the final delivery directory.

State the output format, editability, slide count, notes or companion files, assumptions, missing assets, font substitutions, known limitations, and the verification performed.
