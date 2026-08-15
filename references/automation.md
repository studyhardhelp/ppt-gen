# Automation CLI

Use `scripts/ppt_gen.py` as the stable entry point. Run commands from the Skill directory or use absolute script paths.

## Project lifecycle

```bash
python3 scripts/ppt_gen.py init work/my-deck --title "Quarterly review" --route native-pptx
python3 scripts/ppt_gen.py ingest report.docx data.csv --output work/my-deck/work/ingested.json
python3 scripts/ppt_gen.py build work/my-deck --render
python3 scripts/ppt_gen.py qa work/my-deck/output/deck.pptx --strict
```

`build` supports `native-pptx`, `template-pptx`, `html`, `image-first`, and `reconstruction`. Route-specific inputs are `--template` plus `--edits` and optional `--profile`, `--images`, or `--source` and optional `--language`. Use `--skip-check` only for debugging incomplete PPTX output.

## Brief contract

`work/brief.json` controls title, objective, audience, desired action, duration, slide count, language, route, editability, aspect ratio, brand/template, theme, author, subject, required sections, and constraints.

## Storyboard contract

`work/storyboard.json` contains deck-level purpose and ordered slides. Every slide must have a role and action title. Add only the route-specific fields required by the selected layout; omit unused `image`, `metrics`, `chart`, `table`, and `columns` values.

Chart series use `{name, values}` and share the chart's `categories`. Table rows must match the header width. Resolve image paths relative to the project root.

## Template edit contract

Profile a template before editing:

```bash
python3 scripts/ppt_gen.py profile-template template.pptx --output work/profile.json
```

An edit specification may contain:

- `selected_slides`: original 1-based slide numbers to keep and reorder;
- `global`: string replacements across slide text;
- `slides`: exact old-to-new text maps keyed by original slide number;
- `edits`: addressed replacements with `slide`, `slot_id` or `address`, optional `expected_text`, and `new_text`.

Run strict mode so stale addresses or unexpected source text fail instead of silently editing the wrong content.

## Dependency behavior

`doctor.py` finds a usable Node/PptxGenJS runtime and rendering tools. The repository pins PptxGenJS in `package.json` for standalone installation and CI; prefer an environment-provided runtime when one is available. Reconstruction additionally requires Tesseract and Pillow. PDF text ingestion requires `pdftotext`.

The tested GitHub Actions definition is stored at `assets/ci/github-actions-test.yml`. Copy it to `.github/workflows/test.yml` only when the pushing credential has GitHub's `workflow` permission.
