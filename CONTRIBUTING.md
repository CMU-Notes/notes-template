# Contributing to CMU-Notes

We welcome contributions from anyone at CMU (or elsewhere). Here's how the organization works and how you can help.

## How the Organization Works

**CMU-Notes** is a GitHub organization that hosts course notes. It contains:

- **`notes-template`** (this repo): the LaTeX template that all notes follow
- **`notes-<course-name>`**: one private repo per course with the actual generated notes

Each course repo follows the exact same structure and style defined in this template.

## How to Contribute

### Option 1: Fix or improve an existing course's notes

1. **Fork** the course repo you want to improve (e.g., `CMU-Notes/notes-real-analysis`)
2. Make your changes in your fork
3. Open a **Pull Request** back to the original repo
4. Describe what you changed and why

The repo owner will review and merge.

### Option 2: Add notes for a new course

1. **Fork this template** repo
2. Follow the Quick Start in the README to set up your course
3. Fill in the templates with your course content
4. Contact the org owner to have your repo added to the organization

To request being added as a contributor:
- Open an issue on this repo titled "Request: Add notes for [Course Name]"
- Include: course code, semester, and your GitHub username
- The org admin will create the repo and add you as a collaborator

### Option 3: Improve the template itself

1. Fork this repo
2. Make your changes
3. Open a Pull Request with a clear description

## Rules for All Contributions

These are strict. PRs that break them will be rejected.

### Structure

- One `.tex` file per chapter for notes, one for questions
- Follow the folder layout: `chapters/chN/notes/notes.tex` and `chapters/chN/questions/questions.tex`
- Always compile and verify before submitting. Zero LaTeX errors.
- **Run the format checker before every PR:** `python3 check_formatting.py . --fix`
- The checker must pass with 0 failures. PRs with formatting failures will be rejected.

### Formatting

- Use the colored boxes defined in the template. Do not invent new ones without discussion.
- All boxes must use `enhanced jigsaw, breakable` with `drop shadow southeast` and `pad at break*=2mm`. Do not use flat boxes.
- `\[...\]` for display math. Never `$$...$$`.
- `align*` for multi-line equations.
- **No `$` inside tcolorbox titles.** Plain text only.
- `booktabs` for tables (`\toprule`, `\midrule`, `\bottomrule`). No vertical rules.
- Automatic theorem numbering. Never hardcode numbers.
- Every file must have page headers (`\pagestyle{fancy}`, `\lhead`, `\rhead`, `\cfoot`).
- The preamble must be identical across all chapters (except `\title`, `\author`, `\date`, `\lhead`, `\rhead`).

### Writing

- First person plural: "we define", "we show"
- Before each proof: state the strategy in one sentence
- After each proof: "We showed that ..." in one sentence
- Short direct sentences
- Motivate every definition: one sentence on WHY before the formal statement
- **No em dashes** (never use `---`)
- **No filler**: "basically", "essentially", "in other words"
- Every proof must be complete. No "left as an exercise."

### Questions

- Minimum 50 per chapter
- Progressive difficulty: straightforward first, hard last
- Difficulty communicated through box color only (green, orange, red). No text labels.
- Every question must have a full solution in Part II
- Solutions show every step. No skipping.

## Commit Messages

- Descriptive and concise: "Add Chapter 3 notes for Real Analysis"
- No `Co-authored-by` trailers
- No emoji

## Getting Help

- Open an issue on this repo for template questions
- Open an issue on the specific course repo for content questions

## Code of Conduct

Be respectful. This is a shared academic resource. Plagiarism (copying exact exam questions, submitting others' work as your own) is not tolerated and violates university policy.
