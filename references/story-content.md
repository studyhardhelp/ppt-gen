# Story and Content

## Build the brief

Capture audience, objective, expected decision or action, duration, slide count, language, editability, brand assets, required sections, and factual constraints. Ask only questions that materially change the result. Use reasonable defaults for the rest.

## Extract evidence

- Read all supplied sources before outlining.
- Separate facts, interpretations, claims, quotations, and open questions.
- Record each external source in `work/sources.md` with a stable ID.
- Preserve units, reporting periods, methodology, and uncertainty around numbers.
- Never fabricate citations, customers, performance metrics, or quotations.

## Write the storyboard

Use `work/storyboard.json`. Give each slide:

- `role`: cover, section, context, argument, evidence, comparison, process, result, decision, or close;
- `action_title`: the conclusion the audience should retain;
- `supporting_points`: no more than the slide can support visibly;
- `visual`: chart, diagram, image, table, quotation, code, or deliberate typography;
- `source_ids`: evidence used on the slide;
- `speaker_note`: what the presenter says beyond the visible content.

Review the storyboard as a complete argument before implementing layouts. Remove redundant slides and split overloaded ones.

## Common narrative structures

- Executive update: situation, change, implication, options, recommendation, decision.
- Consulting: answer first, supporting arguments, evidence, risks, implementation.
- Pitch: problem, insight, solution, proof, market, model, traction, ask.
- Product launch: audience tension, product promise, workflow, differentiation, proof, next step.
- Academic: question, prior work, method, results, limitations, conclusion, references.
- Teaching: learning objective, prior model, explanation, worked example, practice, recap.
- Technical: constraint, architecture, key decisions, sequence, tradeoffs, operations.

## Writing rules

- State conclusions in titles; use neutral labels only for covers and section dividers.
- Keep one primary message per slide.
- Prefer concrete nouns and verbs over slogans.
- Keep body text presentation-length, not document-length.
- Put detail in notes, appendices, or handouts when it cannot be removed.
- Explain the meaning of a chart directly instead of expecting the audience to infer it.
- Write notes to expand the visible slide, not repeat it.

