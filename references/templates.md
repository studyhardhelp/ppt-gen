# GitHub Template Sources

Use the bundled registry to discover permissively licensed template libraries and template-aware engines. The registry is metadata only; fetch third-party repositories on demand and pin the returned commit in the project source ledger.

## Commands

```bash
python3 scripts/templates.py stats
python3 scripts/templates.py stats --json
python3 scripts/templates.py list
python3 scripts/templates.py list --route html
python3 scripts/templates.py search "academic html"
python3 scripts/templates.py show beautiful-html-templates
python3 scripts/templates.py fetch beautiful-html-templates work/vendor/beautiful-html-templates
python3 scripts/templates.py fetch beautiful-html-templates work/vendor/beautiful-html-templates --commit <sha>
python3 scripts/templates.py verify beautiful-html-templates work/vendor/beautiful-html-templates
python3 scripts/templates.py stats --include-local
python3 scripts/templates.py local --gallery work/template-gallery.html
```

As of 2026-08-15, the registry contains 20 permissively licensed GitHub sources: 237 concrete templates or themes, 52 reusable layouts, and 21 example decks. Template engines without a fixed bundled template are counted as sources but not as template assets. Run `stats` for the current machine-readable totals and route breakdown.

`fetch` clones the selected source but never executes its scripts. It writes `.ppt-gen-source.json` with the repository, commit, Git tree, registered license, discovered license files, and timestamp. Use `--commit` for exact reproducibility and `verify` before rebuilding. Inspect the upstream README, `AGENTS.md`, dependencies, assets, and license before running commands or copying files.

## Local template cache

Inspect `local-templates/` before fetching a remote source. This directory is intentionally ignored by Git so locally licensed, user-supplied, or personal-use template assets cannot be pushed accidentally.

When present, the local Gorden PPT cache is stored at `local-templates/GordenPPTSkill`; it is not part of a fresh Git clone. Read its `templates/INDEX.md`, shortlist by scene and style, show the corresponding `preview.png` files when the choice is ambiguous, then follow its `SKILL.md` and `references/workflow.md`. Each of its 21 template directories contains `template.pptx`, `detail.json`, `intro.md`, and `preview.png`; use its `scripts/build_pptx.py` workflow or this Skill's profile/fill workflow to replace addressed text while preserving the original layout.

## Selection workflow

1. Decide whether the delivery route is native PPTX, HTML, Marp, or Slidev.
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
| `deckmason` | HTML | Template library | MIT | 31 selectable HTML themes |
| `slidev-templates` | Slidev | Template library | MIT | One Neko-style Markdown and Vue template |
| `neobeam` | Marp | Template library | MIT | One focused modern Marp theme |
| `marpx` | Marp | Template library | MIT | 15 named Marp themes with shared foundations |
| `codebytes-marp-slides-template` | Marp | Template library | MIT | Four CSS themes for technical presentations |
| `marp-theme-wave` | Marp | Template library | MIT | One wave-inspired Marp theme |
| `academic-ppt-template` | Native PPTX | Template library | MIT | Editable academic PowerPoint template |
| `bit-ppt-template` | Native PPTX | Branded template | MIT | Authorized BIT academic presentations |
| `ppt-report-skills` | HTML | Template engine | MIT | 19 reusable report slide layouts |
| `seaslides` | HTML | Template library | MIT | 18 web presentation templates with theme metadata |

The machine-readable source of truth is [assets/template-sources.json](../assets/template-sources.json).

## License and brand policy

- Include only repositories with an explicit permissive repository license in the fetchable registry.
- Treat repository license metadata as applying to repository content, not automatically to third-party logos, fonts, photographs, or trademarks.
- Require authorization before using university or company identities or implying endorsement.
- Keep unknown-license projects out of automatic fetching. They may be researched separately but must not be copied into a deliverable until rights are clarified.
- Preserve upstream notices when redistributing permitted assets.

## Native PPTX guidance

Prefer template engines over treating a PPTX as a flat background. Profile masters and layouts, map semantic content to real placeholders, and preserve theme colors, fonts, geometry, charts, notes, and relationships. Render the result after every substantial change.

## HTML, Marp, and Slidev guidance

Use metadata to shortlist styles, then inspect real previews. Preserve the selected template's design tokens and signature compositions while replacing all example content. Freeze dependencies locally for final delivery and test the deck at the intended aspect ratio.
