# Typography for documents and HTML

Read the shared principles and the section for the current output. Read theme
options only when selecting a design. Existing templates and explicit user
instructions take precedence. This reference governs presentation; the relevant
Docs or artifact skill still governs tool use, permissions, and verification.

## Shared principles

- Set body text first. Judge size, line spacing, and line length together at
  the intended reading or screen-sharing zoom. Do not shrink text to fit a demo.
- Aim for roughly 45–90 characters per prose line. Keep wide tables, diagrams,
  and code readable independently of the prose measure.
- Give fonts consistent roles. Usually one family, or one for headings and one
  for prose, is enough; monospace serves code and alignment-dependent diagrams.
- Distinguish headings primarily with space and restrained changes of size or
  weight. For new documents, two or three levels usually suffice. Preserve an
  existing document's hierarchy when the task is only restyling.
- Left-align prose. Use emphasis selectively; avoid stacking bold, italic,
  underline, capitals, and color on the same phrase. Keep links identifiable.
- Use dark body text on a light background (or a legible dark-mode equivalent),
  with limited accent color. Meaning must also be expressed in text, not color
  alone. Keep risks and uncertainty visible.
- For formatting-only edits, preserve wording, order, links, tables, diagrams,
  and existing meaningful emphasis. Compare content before and after; font
  changes can inadvertently reset bold. Do not rewrite or add summaries.

## Google Docs and formatted documents

Start around 12–13 pt body text for screen reading, then adjust for the chosen
font and actual presentation. Butterick's 10–12 pt print recommendation is not
an instruction to make a screen-shared document tiny. Aim for comfortable
leading; a word processor's line-spacing multiplier may not equal a multiple
of the font size. Check the rendered result rather than claiming exact math.

Use paragraph styles and consistent space before/after headings and paragraphs.
Keep headings with their following text where supported. Adjust margins only
when they will not damage wide tables or diagrams; preserve table geometry and
monospace alignment. Preserve native headings, links, chips, and tab structure.
Do not remove intentional emphasis or blank paragraphs merely to fit a theme.

Inspect representative rendered pages: opening, dense prose, table, and diagram
where present. Look for clipping, awkward wrapping, orphan headings, and tiny
text. After a correction, check the affected final pages again. State whether
verification used the live editor, an export, or only API style readback.

## HTML pages

Use a skill's existing renderer and stylesheet when supplied. Make reusable
style changes there only when the task authorizes changing the generator;
otherwise respect its supported customization interface.

- Start with 15–25px body text and unitless line-height around 1.2–1.45; adjust
  for the typeface and reading context. Use relative sizing that permits zoom.
- Constrain prose width; 50–65ch is a starting point, not a character count.
  CSS ch measures the zero glyph; the relationship varies with font and text.
- Let tables and code run wider or scroll inside their own containers without
  creating whole-page horizontal scrolling. Preserve code whitespace.
- Use semantic headings, lists, and tables. Keep essential orientation and
  conclusions visible; put optional evidence in native details elements with
  descriptive summaries and keyboard-visible focus.
- For offline artifacts, use local/system font fallbacks. Do not add remote
  font dependencies unless online assets are appropriate for the request.
- Verify narrow-screen layout, 200% zoom, keyboard focus, and supported color
  schemes. Inspect the result visually; HTML validity alone is not visual QA.

## Optional themes

Choose a treatment that serves the reader. These are starting palettes, not
mandatory fonts or a requirement to offer three versions. Match an existing
house style first; use alternatives when the user asks to explore variety.

| Treatment | Starting choices | Useful for |
| --- | --- | --- |
| Quiet reading | Georgia; dark text; modest bold headings; comfortable spacing | Long explanations and sustained reading |
| Technical handbook | Arial or a system sans; restrained dark-blue headings; compact, consistent hierarchy | Requirements, reference material, and review walkthroughs |
| Editorial | Playfair Display headings with Lato body; dark rust accent; more space around sections | Shareable narratives and deliberate visual experiments |

Check font availability and fallbacks. The editorial palette and larger display
headings are experimental choices, not Butterick's prescribed style. In Docs,
12–13 pt is a useful body starting range; in HTML use the screen ranges above.

## Sources

Adapted from Butterick's Practical Typography: [body text and basic ranges](https://practicaltypography.com/typography-in-ten-minutes.html),
[headings](https://practicaltypography.com/headings.html),
[font roles](https://practicaltypography.com/mixing-fonts.html),
[color](https://practicaltypography.com/color.html), and
[line-spacing caveats](https://practicaltypography.com/line-spacing.html).
