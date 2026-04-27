# Notes Template

A clean, structured LaTeX template for university course notes and practice problems. Built for CMU Qatar, usable anywhere.

## What's Inside

| Template | What it produces |
|----------|-----------------|
| `chapters/ch1/notes/notes.tex` | Full chapter notes: definitions, theorems, proofs, examples, intuition, summaries |
| `chapters/ch1/questions/questions.tex` | 50+ practice problems per chapter with full solutions |
| `compressed_notes.tex` | Condensed version of all notes (proof sketches, one example per theorem) |
| `cheatsheet.tex` | 2-3 page landscape cheatsheet with every definition and theorem |
| `check_formatting.py` | Deterministic format checker and auto-fixer |

## Quick Start

```bash
# Clone this template
git clone https://github.com/CMU-Notes/notes-template.git my-course
cd my-course

# Copy ch1 for each chapter you need
cp -r chapters/ch1 chapters/ch2
cp -r chapters/ch1 chapters/ch3

# Edit the .tex files, replacing the example content with your course material
# Compile (run twice for TOC)
cd chapters/ch1/notes && pdflatex notes.tex && pdflatex notes.tex

# Check formatting across all chapters
cd ../../.. && python3 check_formatting.py . --fix
```

## Template Design

### Notes (`notes.tex`)

Each chapter's notes use color-coded boxes with drop shadows for different content types:

| Box | Color | Use |
|-----|-------|-----|
| `\begin{defbox}[title]` | 🔵 Blue | Definitions |
| `\begin{thmbox}[title]` | 🔴 Red | Theorems, lemmas, corollaries |
| `\begin{exbox}[title]` | 🟢 Green | Worked examples |
| `\begin{whybox}[title]` | 🟠 Orange | Intuition after a proof |
| `\begin{sumbox}[title]` | 🟣 Purple | Section summary |
| `\begin{codebox}[title]` | ⬜ Gray | Code (use `\begin{verbatim}` inside) |
| `\begin{algobox}[title]` | 🟦 Teal | Pseudocode / algorithms |

All boxes use `enhanced jigsaw, breakable` with `drop shadow southeast` and `pad at break*=2mm`. This means:
- Boxes have depth/shadow (not flat)
- Large boxes can break across pages cleanly (borders preserved on both halves)
- Small boxes that break awkwardly can be fixed with `\needspace{5cm}` before the box

Inline notes use `\note{text}` which renders as smaller italic text below the content.

**Structure of each section:**
1. One sentence motivating why the topic matters
2. Definition in a blue box
3. Theorem in a red box
4. Full proof
5. Intuition in an orange box (2-3 sentences: what is the core idea?)
6. Worked example in a green box
7. Summary in a purple box at the end of the section

### Questions (`questions.tex`)

Practice problems use color-coded boxes for difficulty:

| Box | Color | Difficulty |
|-----|-------|------------|
| `\begin{qeasy}[Q1]` | 🟢 Green | Direct application, one concept |
| `\begin{qmedium}[Q4]` | 🟠 Orange | Combine ideas, exam-level |
| `\begin{qhard}[Q8]` | 🔴 Red | Multi-step proofs, tricky |

Solutions go in Part II using `\begin{solution}[Q1]` (gray boxes).

The title is just "Q1", "Q2", etc. No other labels. The color communicates the difficulty.

### Cheatsheet (`cheatsheet.tex`)

- 6pt font, 4-column landscape layout
- Minimal margins, no title block
- Every definition + theorem + one-line proof idea using `\pf{...}`
- Target: 2-3 pages for an entire course

### Compressed Notes (`compressed_notes.tex`)

- 30-50% the length of the full notes
- Same colored boxes as full notes
- Proof sketches instead of full proofs
- One example per major theorem

## Format Checker

`check_formatting.py` checks and auto-fixes formatting across all chapters:

```bash
# Check only (report issues)
python3 check_formatting.py .

# Check and auto-fix
python3 check_formatting.py . --fix

# Compare against a template repo
python3 check_formatting.py . --template /path/to/notes-template

# Also analyze PDFs for visual issues (cut boxes, overlapping text, blank pages)
python3 check_formatting.py . --fix --visual
```

**What it checks:**
- Preamble identity across all chapters (must match template exactly)
- Document class consistency
- Required elements: `\maketitle`, `\tableofcontents`, `\newpage`, headers (`\lhead`, `\rhead`, `\cfoot`)
- Forbidden patterns: `$$...$$`, `$` in box titles, `\textwidth` tables without `tabularx`
- Notation consistency: raw `\mathbb{R}` vs `\R` macros
- Box styling: `enhanced jigsaw`, `drop shadow`, hex colors (not `green!4`)
- Hyperref consistency across files
- PDF analysis: cut boxes, overlapping text, blank pages, margin overflow

## Visual Tools

All templates come with these packages loaded and ready to use:

**Figures:** `graphicx`, `subcaption`, `float`
```latex
\begin{figure}[H]
  \centering
  \includegraphics[width=0.6\textwidth]{image.pdf}
  \caption{Description.}\label{fig:name}
\end{figure}
```

**Plots:** `pgfplots`
```latex
\begin{center}
  \begin{tikzpicture}
    \begin{axis}[xlabel={$x$}, ylabel={$f(x)$}, grid=major]
      \addplot[blue, thick, domain=0:1]{x^2};
    \end{axis}
  \end{tikzpicture}
\end{center}
```

**Diagrams:** `tikz` with libraries for arrows, positioning, shapes, automata, trees, decorations, patterns

**Tables:** `booktabs` (clean rules), `tabularx` (auto-width), `longtable` (multi-page)

**Code:** `codebox` with `\begin{verbatim}` inside (or uncomment `listings` package for syntax highlighting)

## Writing Style

All notes in this organization follow these conventions:

- First person plural: "we define", "we show", "we prove"
- Before each proof: one sentence stating the strategy
- After each proof: "We showed that ..." (one sentence)
- Short direct sentences. No filler.
- Motivate every definition before stating it
- No em dashes. No "basically", "essentially".
- `\[...\]` for display math, never `$$...$$`
- `align*` for multi-line equations
- Plain text inside box titles (no `$math$` in `\begin{thmbox}[title]`)

## Page Headers

Every file must have page headers set up in the preamble:

```latex
\pagestyle{fancy}
\lhead{{\small COURSE-CODE \quad Chapter N: Title}}
\rhead{{\small Fall 2025}}
\cfoot{\thepage}
```

The format checker will auto-inject these from `\title` and `\author` if missing.

## LaTeX Requirements

Standard packages from any modern TeX distribution (TeX Live, MiKTeX):

```
amsmath, amssymb, amsthm, mathtools, tcolorbox, tikz, pgfplots,
graphicx, subcaption, float, booktabs, tabularx, longtable,
enumitem, hyperref, fancyhdr, titlesec, lmodern, microtype
```

Optional: `listings`, `algorithm`, `algpseudocode` (uncomment in preamble if available)

## License

Free to use for any educational purpose.
