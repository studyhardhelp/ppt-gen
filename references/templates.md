# GitHub Template Sources

Use the bundled registry to discover permissively licensed template libraries and template-aware engines. The registry is metadata only; fetch third-party repositories on demand and pin the returned commit in the project source ledger.

## Commands

```bash
python3 scripts/templates.py list
python3 scripts/templates.py list --route html
python3 scripts/templates.py search "academic html"
python3 scripts/templates.py show beautiful-html-templates
python3 scripts/templates.py fetch beautiful-html-templates work/vendor/beautiful-html-templates
```

`fetch` clones the selected source but never executes its scripts. Inspect the upstream README, `AGENTS.md`, dependencies, assets, and license before running commands or copying files.

## Selection workflow

1. Decide whether the delivery route is native PPTX, HTML, or Marp.
2. Search by audience, subject, format, and editability rather than by color alone.
3. Shortlist at most three candidates and inspect their actual previews and object structure.
4. Confirm the repository license and any separate logo, trademark, font, image, or brand restrictions.
5. Fetch only the selected source into the project workspace, never into the final delivery directory.
6. Record repository URL and fetched commit in `work/sources.md`.
7. Adapt the design system and layout logic to the user's content; do not copy example claims, data, or imagery.
8. Verify the generated deck independently with this Skill's QA workflow.

## Curated sources

| ID | Route | Type | License | Best use |
| --- | --- | --- | --- | --- |
| `beautiful-html-templates` | HTML | Template library | MIT | 34 general-purpose editorial, business, and creative styles |
| `ai-slide-templates` | HTML | Template library | MIT | 54 business, research, training, education, and executive templates |
| `inspiration-deck-workshop` | HTML | Template library | MIT | 23 themes, 25 layouts, and complete deck starters |
| `marp-slides-studio` | Marp | Template library | MIT | 50 Markdown-first themes with gallery and contrast checks |
| `cuhk-slides-template-html` | HTML | Branded template | MIT | Authorized CUHK academic presentations |
| `fudan-html-ppt-template` | HTML | Branded template | MIT | Authorized Fudan academic presentations |
| `pptx-from-layouts` | Native PPTX | Template engine | MIT | Fill actual slide-master layouts; includes `inner-chapter.pptx` |
| `pptx-template-skills` | Native PPTX | Template engine | MIT | Parse any user template into a semantic contract and refill it |
| `competition-template-first` | Native PPTX | Template engine | MIT | Competition and defense decks with visual underlays plus editable evidence |
| `ppt-master-examples` | Native PPTX | Example gallery | MIT | Study editable composition patterns and custom-template workflows |

The machine-readable source of truth is [assets/template-sources.json](../assets/template-sources.json).

## License and brand policy

- Include only repositories with an explicit permissive repository license in the fetchable registry.
- Treat repository license metadata as applying to repository content, not automatically to third-party logos, fonts, photographs, or trademarks.
- Require authorization before using university or company identities or implying endorsement.
- Keep unknown-license projects out of automatic fetching. They may be researched separately but must not be copied into a deliverable until rights are clarified.
- Preserve upstream notices when redistributing permitted assets.

## Native PPTX guidance

Prefer template engines over treating a PPTX as a flat background. Profile masters and layouts, map semantic content to real placeholders, and preserve theme colors, fonts, geometry, charts, notes, and relationships. Render the result after every substantial change.

## HTML and Marp guidance

Use metadata to shortlist styles, then inspect real previews. Preserve the selected template's design tokens and signature compositions while replacing all example content. Freeze dependencies locally for final delivery and test the deck at the intended aspect ratio.

