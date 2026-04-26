# Notes Template

A clean, structured LaTeX template for university course notes and practice problems. Built for CMU Qatar, usable anywhere.

## What's Inside

| Template | What it produces |
|----------|-----------------|
| `chapters/ch1/notes/notes.tex` | Full chapter notes: definitions, theorems, proofs, examples, intuition, summaries |
| `chapters/ch1/questions/questions.tex` | 50+ practice problems per chapter with full solutions |
| `compressed_notes.tex` | Condensed version of all notes (proof sketches, one example per theorem) |
| `cheatsheet.tex` | 2-3 page landscape cheatsheet with every definition and theorem |

## Quick Start

```bash
# Clone this template
git clone https://github.com/CMU-Notes/notes-template.git my-course
cd my-course

# Copy ch1 for each chapter you need
cp -r chapters/ch1 chapters/ch2
cp -r chapters/ch1 chapters/ch3

# Edit the .tex files, replacing the example content with your course material
# Compile
cd chapters/ch1/notes && pdflatex notes.tex && pdflatex notes.tex
```

## Template Design

### Notes (`notes.tex`)

Each chapter's notes use color-coded boxes for different content types:

| Box | Color | Use |
|-----|-------|-----|
| `\begin{defbox}[title]` | 🟢 Green | Definitions |
| `\begin{thmbox}[title]` | 🔵 Blue | Theorems, lemmas, corollaries |
| `\begin{exbox}[title]` | 🟠 Orange | Worked examples |
| `\begin{whybox}[title]` | 🟣 Purple | Intuition after a proof |
| `\begin{sumbox}[title]` | 🟡 Yellow | Section summary |
| `\begin{codebox}[title]` | ⬜ Gray | Code (use `\begin{verbatim}` inside) |
| `\begin{algobox}[title]` | 🟦 Teal | Pseudocode / algorithms |

Inline notes use `\note{text}` which renders as smaller italic text below the content.

**Structure of each section:**
1. One sentence motivating why the topic matters
2. Definition in a green box
3. Theorem in a blue box
4. Full proof
5. Intuition in a purple box (2-3 sentences: what is the core idea?)
6. Worked example in an orange box
7. Summary in a yellow box at the end of the section

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

## Visual Tools

All templates come with these packages loaded and ready to use:

**Figures:** `graphicx`, `subcaption`, `float`
```latex
% Single figure
\begin{figure}[H]
  \centering
  \includegraphics[width=0.6\textwidth]{image.pdf}
  \caption{Description.}\label{fig:name}
\end{figure}

% Two figures side by side
\begin{figure}[H]
  \begin{subfigure}[t]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{left.pdf}
    \caption{Left.}
  \end{subfigure}\hfill
  \begin{subfigure}[t]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{right.pdf}
    \caption{Right.}
  \end{subfigure}
  \caption{Both.}
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
- No em dashes. No "note that", "recall that", "basically", "essentially".
- `\[...\]` for display math, never `$$...$$`
- `align*` for multi-line equations
- Plain text inside box titles (no `$math$` in `\begin{thmbox}[title]`)

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
