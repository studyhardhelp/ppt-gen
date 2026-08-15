# Automation CLI

Use `scripts/ppt_gen.py` as the stable entry point. Run commands from the Skill directory or use absolute script paths.

## Project lifecycle

```bash
python3 scripts/ppt_gen.py init work/my-deck --title "Quarterly review" --route native-pptx
python3 scripts/ppt_gen.py ingest report.docx data.csv --output work/my-deck/work/ingested.json
python3 scripts/ppt_gen.py create work/my-deck report.docx data.csv --title "Quarterly review" --slides 10 --scenario executive --render
python3 scripts/ppt_gen.py build work/my-deck --render
python3 scripts/ppt_gen.py qa work/my-deck/output/deck.pptx --strict --check-fonts
python3 scripts/ppt_gen.py convert existing.pptx output/deck.html
python3 scripts/ppt_gen.py convert output/deck.html output/deck.pdf
```

`build` supports `native-pptx`, `template-pptx`, `html`, `image-first`, and `reconstruction`. Route-specific inputs are `--template` plus `--edits` and optional `--profile`, `--images` or `--manifest`, or `--source` and optional `--language`. Use `--skip-check` only for debugging incomplete PPTX output.

## Brief contract

`work/brief.json` controls title, objective, audience, desired action, duration, slide count, language, route, editability, aspect ratio, brand/template, theme, author, subject, required sections, and constraints.

## Storyboard contract

`work/storyboard.json` contains deck-level purpose and ordered slides. Every slide must have a role and action title. Add only the route-specific fields required by the selected layout; omit unused `image`, `metrics`, `chart`, `table`, and `columns` values.

Chart series use `{name, values}` and share the chart's `categories`. Table rows must match the header width. Resolve image paths relative to the project root.

Simple editable diagrams use `{nodes: [{id, label}], edges: [{from, to, label}]}`. Quote slides use `quote` and optional `attribution`. Set `transition` to `fade`, `slide`, or `zoom` for HTML output.

## Template edit contract

Profile a template before editing:

```bash
python3 scripts/ppt_gen.py profile-template template.pptx --output work/profile.json
python3 scripts/ppt_gen.py template-plan work/profile.json work/storyboard.json work/edits.json
```

An edit specification may contain:

- `selected_slides`: original 1-based slide numbers to keep and reorder;
- `global`: string replacements across slide text;
- `slides`: exact old-to-new text maps keyed by original slide number;
- `edits`: addressed replacements with `slide`, `slot_id` or `address`, optional `expected_text`, `new_text`, and optional `font_size_pt` for run-level font resizing;
- `images`: picture replacements addressed by slide and shape ID, with optional alternative text;
- `notes`: updates to existing speaker-notes bodies;
- `charts`: category and series updates that synchronize chart caches and embedded workbooks;
- `duplicate_slides`: source slide numbers to clone immediately after the original.

Run strict mode so stale addresses or unexpected source text fail instead of silently editing the wrong content.

## Dependency behavior

`doctor.py` finds Node/PptxGenJS, LibreOffice, Poppler, Chrome/Playwright, OCR, PDF text, and image tooling. OCR uses Tesseract when installed and macOS Vision otherwise. PDF text uses `pdftotext` when installed and macOS PDFKit otherwise.

The tested GitHub Actions definition is stored at `assets/ci/github-actions-test.yml`. Copy it to `.github/workflows/test.yml` only when the pushing credential has GitHub's `workflow` permission.
