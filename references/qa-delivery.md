# Quality Assurance and Delivery

## Automated sequence

Run from the skill directory, adjusting paths as needed:

```bash
python3 scripts/doctor.py
python3 scripts/pptx_check.py output/deck.pptx
python3 scripts/render_deck.py output/deck.pptx --output-dir work/rendered --clean
```

Use `pptx_check.py --strict` for release gates after intentional out-of-canvas elements have been eliminated. Structural checks do not replace visual inspection.

The checker reports package corruption, missing and broken relationships, empty slides, excessive text, common Chinese/English sample copy, off-canvas geometry, likely text overflow, obvious text-box collisions, duplicate slide text, notes, external links, media, and referenced fonts. Overflow and collision checks are heuristics; inspect each warning against the render.

For regression work, compare rendered slide directories with `python3 scripts/compare_renders.py baseline-render candidate-render --diff-dir work/diffs`. Or pass `--baseline baseline-render` to `scripts/ppt_gen.py qa` after rendering the candidate.

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
