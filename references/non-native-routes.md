# HTML, Image-First, and Reconstruction Routes

## HTML deck

- Produce a fixed-format 16:9 stage with responsive fit, not a fluid webpage layout.
- Freeze fonts, images, scripts, and styles locally; prefer a single self-contained file when practical.
- Support keyboard navigation, slide numbers, fullscreen, and presenter notes when needed.
- Keep motion deterministic and restrained. Ensure a paused or printed frame still communicates the slide.
- Test desktop and projected aspect ratios. Export a PDF fallback when requested.
- If exporting to PPTX, verify the converted file independently and disclose lost motion or flattened effects.

Build with `python3 scripts/ppt_gen.py build <project> --route html`. The self-contained runtime includes 36 selectable themes, keyboard navigation, progress, fullscreen (`F`), overview (`O`), editable text mode (`E`), save (`Cmd/Ctrl+S`), print/PDF styling, per-slide transitions, and a separate presenter window (`S`) with notes, next-slide title, and timer.

Convert PPTX to a fidelity-first HTML deck with `ppt_gen.py convert source.pptx output.html`. Convert HTML to PDF or image-first PPTX with the same command. Preserve and disclose flattening boundaries.

## Image-first PPTX

- Use only after the user accepts non-editable slide contents.
- Confirm the outline, visual direction, and one or two sample slides before generating the full deck.
- Generate each slide at the final aspect ratio and resolution.
- Check all generated text character by character; regenerate pages with text defects.
- Keep visual style, recurring characters, lighting, and composition consistent across slides.
- Assemble images without recompression where possible and add notes separately.
- Offer editable reconstruction only as a separate, higher-cost step.

Build a directory of ordered PNG/JPG slides with `python3 scripts/ppt_gen.py build <project> --route image-first --images <directory>`. Use `--manifest` for per-slide paths, notes, sources, alternative text, background, and aspect ratio. The result is a PPTX with one contained image per page; disclose that objects inside the image are not editable.

## Editable reconstruction

- Normalize every input page to a stable image and collect OCR results.
- Rebuild readable text as native text boxes and simple geometry as native shapes.
- Preserve complex illustrations, textures, and photographs as separately cropped image assets.
- Recreate tables and charts from source data when available; do not infer exact numbers from pixels.
- Compare each rebuilt slide against the source image at full size and as an overlay when possible.
- Expect multiple correction passes and disclose areas that remain flattened.

Run `python3 scripts/ppt_gen.py build <project> --route reconstruction --source <pdf-or-images>`. This route uses Tesseract or macOS Vision, preserves each source page as an image, covers recognized text regions with sampled local colors, and places editable OCR text over them. Treat the result as a first reconstruction pass and compare every page at full size; complex artwork remains flattened.
