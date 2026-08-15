# Quality Assurance and Delivery

## Automated sequence

Run from the skill directory, adjusting paths as needed:

```bash
python3 scripts/doctor.py
python3 scripts/pptx_check.py output/deck.pptx
python3 scripts/render_deck.py output/deck.pptx --output-dir work/rendered --clean
```

Use `pptx_check.py --strict` for release gates after intentional out-of-canvas elements have been eliminated. Structural checks do not replace visual inspection.

## Contact-sheet review

Inspect the entire deck at once for:

- narrative rhythm and section transitions;
- repeated layouts or monotonous composition;
- sudden density, font, color, or margin changes;
- blank or duplicate slides;
- inconsistent citations, page numbers, and recurring elements.

## Full-size review

Inspect dense and unusual slides for:

- clipped text, accidental wrapping, overflow, and tiny labels;
- collisions, misalignment, distorted images, and broken crops;
- chart labels, units, periods, legends, and source notes;
- connector endpoints and diagram reading order;
- font substitution and missing glyphs;
- generated-image text defects;
- contrast and color-only meaning.

## File integrity

- Confirm the expected slide count, aspect ratio, notes, and output filename.
- Open or parse the final file after the last write.
- Verify that external links and media are intentional.
- Keep editable objects editable and disclose every flattened region.
- Remove placeholders, sample data, debugging objects, and broken links.

## Delivery contract

Deliver only requested final artifacts. Keep source code when it is needed for future edits, but keep temporary XML extraction, render profiles, and intermediate images out of the final directory.

Report the format, editability, slide count, notes or companion PDF, assumptions, missing assets, font substitutions, known limitations, and verification performed. Never claim rendering or visual inspection that did not occur.

