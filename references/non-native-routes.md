# HTML, Image-First, and Reconstruction Routes

## HTML deck

- Produce a fixed-format 16:9 stage with responsive fit, not a fluid webpage layout.
- Freeze fonts, images, scripts, and styles locally; prefer a single self-contained file when practical.
- Support keyboard navigation, slide numbers, fullscreen, and presenter notes when needed.
- Keep motion deterministic and restrained. Ensure a paused or printed frame still communicates the slide.
- Test desktop and projected aspect ratios. Export a PDF fallback when requested.
- If exporting to PPTX, verify the converted file independently and disclose lost motion or flattened effects.

## Image-first PPTX

- Use only after the user accepts non-editable slide contents.
- Confirm the outline, visual direction, and one or two sample slides before generating the full deck.
- Generate each slide at the final aspect ratio and resolution.
- Check all generated text character by character; regenerate pages with text defects.
- Keep visual style, recurring characters, lighting, and composition consistent across slides.
- Assemble images without recompression where possible and add notes separately.
- Offer editable reconstruction only as a separate, higher-cost step.

## Editable reconstruction

- Normalize every input page to a stable image and collect OCR results.
- Rebuild readable text as native text boxes and simple geometry as native shapes.
- Preserve complex illustrations, textures, and photographs as separately cropped image assets.
- Recreate tables and charts from source data when available; do not infer exact numbers from pixels.
- Compare each rebuilt slide against the source image at full size and as an overlay when possible.
- Expect multiple correction passes and disclose areas that remain flattened.

