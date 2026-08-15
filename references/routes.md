# Output Routes

Choose the route from the delivery contract, not from visual preference alone.

## Decision order

1. If another person must edit the deck in PowerPoint, use native or template-based PPTX.
2. If an existing `.pptx` or `.potx` governs the brand, preserve its masters and layouts.
3. If browser interaction, animation, or source control is the primary requirement, use HTML.
4. If the user explicitly accepts flattened slides for maximum visual freedom, use image-first.
5. If screenshots, PDF pages, or a flattened deck must become editable, use reconstruction.

## Capability matrix

| Route | Visual ceiling | PowerPoint editability | Motion | Template fidelity | Typical use |
| --- | --- | --- | --- | --- | --- |
| Native PPTX | High | High | Native transitions/animations | High | Business delivery, consulting, academic |
| Template PPTX | Medium-high | High | Preserve existing behavior | Highest | Enterprise and regulated brands |
| HTML | Highest | None unless separately converted | CSS, JS, SVG, WebGL | Low-medium | Product launches, technical demos |
| Hybrid HTML to PPTX | High | Medium; verify every converted object | HTML motion is usually lost | Medium | Browser editing plus Office handoff |
| Image-first PPTX | Highest static fidelity | Slide-level only | Image transitions | Visual only | Editorial and highly art-directed decks |
| Reconstruction | Depends on source | Medium-high after review | Usually rebuilt | Visual approximation | Legacy deck recovery |

## Route-specific risks

- Native PPTX: layout code can produce clipping, font substitution, or generic compositions. Render every iteration.
- Template PPTX: careless XML edits can break relationships, masters, charts, or embedded media. Make minimal changes.
- HTML: the recipient may be unable to edit or present offline. Freeze all dependencies into local files.
- Hybrid: DOM-to-PPTX conversion can flatten effects and alter typography. Treat exported PPTX as a separate artifact to verify.
- Image-first: text and diagrams are usually not editable and generated text may contain errors. Disclose this before generation.
- Reconstruction: OCR and geometry inference are approximate. Preserve complex regions as separate images when native reconstruction is unreliable.

## Capability patterns synthesized from the ecosystem

- Native editable objects, charts, tables, masters, notes, and package validation.
- HTML-native styling, motion, presenter mode, and single-file delivery.
- Browser editing followed by PPTX export.
- Image generation followed by slide assembly and optional editable reconstruction.
- Scenario overlays for academic, consulting, teaching, product, and enterprise-brand decks.

