#!/usr/bin/env python3
"""
check_formatting.py — Deterministic format checker and auto-fixer.

Checks AND auto-fixes formatting inconsistencies across all chapters.
Only flags visual issues (figures, rendering) for manual/AI review.

Usage:
    python3 check_formatting.py [repo_path] [--fix] [--visual]

    --fix     Auto-fix all deterministic issues (preamble, colors, etc.)
    --visual  Screenshot every page for visual inspection

Without --fix, runs in check-only mode (reports but doesn't change files).
"""

import os
import sys
import re
import hashlib
import shutil
import subprocess
import argparse

# ─── Helpers ──────────────────────────────────────────────────────────

def find_files(repo, name, subdir=None):
    """Find all files matching name under repo/chapters/*/subdir/."""
    results = []
    chapters_dir = os.path.join(repo, 'chapters')
    if not os.path.isdir(chapters_dir):
        return results
    for ch in sorted(os.listdir(chapters_dir)):
        if subdir:
            path = os.path.join(chapters_dir, ch, subdir, name)
        else:
            for root, dirs, files in os.walk(os.path.join(chapters_dir, ch)):
                if name in files:
                    path = os.path.join(root, name)
                    results.append(path)
                    continue
            continue
        if os.path.isfile(path):
            results.append(path)
    return results

def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def extract_preamble(content):
    """Everything before \\begin{document}."""
    idx = content.find('\\begin{document}')
    if idx == -1:
        return content
    return content[:idx]

def extract_body(content):
    """Everything from \\begin{document} onward."""
    idx = content.find('\\begin{document}')
    if idx == -1:
        return ''
    return content[idx:]

def _find_variable_blocks(lines):
    """Find line ranges for variable commands (\title, \lhead, etc.) that may span multiple lines.
    Returns dict: command_key -> (start_idx, end_idx_exclusive)"""
    keys = ['\\title', '\\lhead', '\\rhead', '\\author', '\\date']
    blocks = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_key = None
        for k in keys:
            if k in line:
                matched_key = k
                break
        if matched_key:
            # Count braces to find where the command ends
            start = i
            depth = 0
            for ch in line:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            i += 1
            while depth > 0 and i < len(lines):
                for ch in lines[i]:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                i += 1
            blocks[matched_key] = (start, i)
        else:
            i += 1
    return blocks

def strip_variable_lines(preamble):
    """Remove lines belonging to variable commands (handles multi-line \\title etc.)."""
    lines = preamble.split('\n')
    blocks = _find_variable_blocks(lines)
    # Collect all line indices to skip
    skip = set()
    for (start, end) in blocks.values():
        skip.update(range(start, end))
    return '\n'.join(l for i, l in enumerate(lines) if i not in skip)

# ─── Checks ──────────────────────────────────────────────────────────

class CheckResult:
    def __init__(self):
        self.fails = []
        self.fixes = []
        self.warnings = []

    def fail(self, msg):
        self.fails.append(msg)

    def fix(self, msg):
        self.fixes.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def report(self):
        print("\n" + "=" * 70)
        print(f"RESULTS: {len(self.fails)} failures, {len(self.fixes)} auto-fixed, {len(self.warnings)} warnings")
        print("=" * 70)
        if self.fixes:
            print("\nAUTO-FIXED:")
            for f in self.fixes:
                print(f"  ✓ {f}")
        if self.warnings:
            print("\nWARNINGS (need visual check):")
            for w in self.warnings:
                print(f"  ⚠ {w}")
        if self.fails:
            print("\nFAILURES (could not auto-fix):")
            for f in self.fails:
                print(f"  ✗ {f}")
        if not self.fails and not self.warnings:
            print("\n✓ ALL CHECKS PASSED.")
        return len(self.fails)


def check_and_fix_preamble(repo, notes_files, question_files, do_fix, result,
                          ref_notes_path=None, ref_questions_path=None):
    """Ensure every file's preamble matches the TEMPLATE exactly (except title/header).
    If ref_notes_path/ref_questions_path given, use those as golden reference.
    Otherwise fall back to the first file found (ch1)."""
    print("\n[1] PREAMBLE IDENTITY")

    if not notes_files:
        result.fail("No notes files found")
        return

    # Use template reference if provided, else fall back to first file
    notes_ref_file = ref_notes_path if ref_notes_path else notes_files[0]
    questions_ref_file = ref_questions_path if ref_questions_path else (question_files[0] if question_files else None)

    ref_source = "template" if ref_notes_path else "ch1 (no --template given)"
    print(f"  Reference: {ref_source}")

    ref_content = read_file(notes_ref_file)
    ref_preamble = extract_preamble(ref_content)
    ref_stripped = strip_variable_lines(ref_preamble)

    # When using a template reference, check ALL files including ch1
    files_to_check = notes_files if ref_notes_path else notes_files[1:]
    for f in files_to_check:
        if f == notes_ref_file:
            continue  # Don't compare reference against itself
        content = read_file(f)
        preamble = extract_preamble(content)
        stripped = strip_variable_lines(preamble)

        if stripped != ref_stripped:
            if do_fix:
                body = extract_body(content)
                if not body:
                    body = '\\begin{document}\n\\end{document}\n'
                    result.warn(f"File had no \\begin{{document}}, added stub: {f}")

                # Extract variable BLOCKS from the target file (may be single or multi-line)
                old_preamble_lines = preamble.split('\n')
                old_blocks = _find_variable_blocks(old_preamble_lines)
                # For each variable command, grab ALL its lines from the target
                old_block_text = {}
                for key, (s, e) in old_blocks.items():
                    old_block_text[key] = '\n'.join(old_preamble_lines[s:e])

                # Now rebuild from template preamble, replacing variable BLOCKS
                ref_lines = ref_preamble.split('\n')
                ref_blocks = _find_variable_blocks(ref_lines)

                # Build output: iterate template lines, skip template's variable blocks,
                # insert target's variable blocks at the right positions
                new_lines = []
                skip_until = -1
                for i, line in enumerate(ref_lines):
                    if i < skip_until:
                        continue
                    # Check if this line starts a variable block in the template
                    replaced = False
                    for key, (s, e) in ref_blocks.items():
                        if i == s:
                            # Replace entire template block with target's block
                            if key in old_block_text:
                                new_lines.append(old_block_text[key])
                            else:
                                # Target doesn't have this command — keep template's
                                new_lines.extend(ref_lines[s:e])
                            skip_until = e
                            replaced = True
                            break
                    if not replaced:
                        new_lines.append(line)

                new_preamble = '\n'.join(new_lines)
                # Ensure preamble ends with newline before \begin{document}
                if not new_preamble.endswith('\n'):
                    new_preamble += '\n'
                # Ensure body starts with \begin{document}
                if not body.startswith('\\begin{document}'):
                    body = '\\begin{document}\n' + body

                new_content = new_preamble + body
                # Final sanity check
                if '\\begin{document}' not in new_content:
                    result.fail(f"BUG: sync would remove \\begin{{document}} from {f} — skipping")
                    continue
                write_file(f, new_content)
                result.fix(f"Preamble synced to template: {f}")
            else:
                result.fail(f"Preamble mismatch vs template: {f}")
        else:
            print(f"  OK: {f}")

    # Same for questions
    if question_files:
        q_ref_file = questions_ref_file if questions_ref_file else question_files[0]
        if q_ref_file and os.path.isfile(q_ref_file):
            ref_q = read_file(q_ref_file)
            ref_q_preamble = extract_preamble(ref_q)
            ref_q_pre = strip_variable_lines(ref_q_preamble)
            q_files_to_check = question_files if ref_questions_path else question_files[1:]
            for f in q_files_to_check:
                if f == q_ref_file:
                    continue
                content = read_file(f)
                stripped = strip_variable_lines(extract_preamble(content))
                if stripped != ref_q_pre:
                    if do_fix:
                        body = extract_body(content)
                        if not body:
                            body = '\\begin{document}\n\\end{document}\n'
                            result.warn(f"Questions file had no \\begin{{document}}, added stub: {f}")

                        old_lines = extract_preamble(content).split('\n')
                        old_blocks = _find_variable_blocks(old_lines)
                        old_block_text = {}
                        for key, (s, e) in old_blocks.items():
                            old_block_text[key] = '\n'.join(old_lines[s:e])

                        ref_lines = ref_q_preamble.split('\n')
                        ref_blocks = _find_variable_blocks(ref_lines)

                        new_lines = []
                        skip_until = -1
                        for i, line in enumerate(ref_lines):
                            if i < skip_until:
                                continue
                            replaced = False
                            for key, (s, e) in ref_blocks.items():
                                if i == s:
                                    if key in old_block_text:
                                        new_lines.append(old_block_text[key])
                                    else:
                                        new_lines.extend(ref_lines[s:e])
                                    skip_until = e
                                    replaced = True
                                    break
                            if not replaced:
                                new_lines.append(line)

                        new_preamble = '\n'.join(new_lines)
                        if not new_preamble.endswith('\n'):
                            new_preamble += '\n'
                        if not body.startswith('\\begin{document}'):
                            body = '\\begin{document}\n' + body
                        new_content = new_preamble + body
                        if '\\begin{document}' not in new_content:
                            result.fail(f"BUG: sync would remove \\begin{{document}} from {f} — skipping")
                            continue
                        write_file(f, new_content)
                        result.fix(f"Questions preamble synced to template: {f}")
                    else:
                        result.fail(f"Questions preamble mismatch vs template: {f}")
                else:
                    print(f"  OK: {f}")


def check_document_class(notes_files, question_files, result):
    """All files must have same documentclass."""
    print("\n[2] DOCUMENT CLASS")
    all_files = notes_files + question_files
    if not all_files:
        return

    classes = {}
    for f in all_files:
        content = read_file(f)
        m = re.search(r'\\documentclass\[?[^\]]*\]?\{[^}]+\}', content)
        if m:
            classes[f] = m.group()

    if classes:
        ref = list(classes.values())[0]
        for f, cls in classes.items():
            if cls != ref:
                result.fail(f"Documentclass mismatch: {f} has '{cls}', expected '{ref}'")
            else:
                print(f"  OK: {f}")


def check_required_elements(notes_files, question_files, do_fix, result):
    """Check required structural elements and auto-fix missing ones."""
    print("\n[3] REQUIRED ELEMENTS")

    for f in notes_files:
        content = read_file(f)
        modified = False

        # Check for \maketitle
        if '\\maketitle' not in content:
            if do_fix and '\\begin{document}' in content:
                content = content.replace('\\begin{document}', '\\begin{document}\n\\maketitle')
                modified = True
                result.fix(f"Added missing maketitle: {f}")
            else:
                result.fail(f"Missing maketitle: {f}")

        # Check for \thispagestyle{fancy} after \maketitle (forces headers on page 1)
        if '\\maketitle' in content and '\\thispagestyle{fancy}' not in content:
            if do_fix:
                content = content.replace('\\maketitle', '\\maketitle\n\\thispagestyle{fancy}')
                modified = True
                result.fix(f"Added \\thispagestyle{{fancy}} after \\maketitle: {f}")
            else:
                result.fail(f"Missing \\thispagestyle{{fancy}} after \\maketitle (headers won't show on page 1): {f}")

        # Check for \tableofcontents (notes must have it)
        if '\\tableofcontents' not in content:
            if do_fix and '\\maketitle' in content:
                content = content.replace('\\maketitle', '\\maketitle\n\\tableofcontents\n\\newpage')
                modified = True
                result.fix(f"Added missing TOC + newpage: {f}")
            else:
                result.fail(f"Missing tableofcontents: {f}")

        # Check newpage after tableofcontents
        toc_idx = content.find('\\tableofcontents')
        if toc_idx != -1:
            after_toc = content[toc_idx + len('\\tableofcontents'):].lstrip()
            if not after_toc.startswith('\\newpage'):
                if do_fix:
                    content = content[:toc_idx] + '\\tableofcontents\n\\newpage\n' + \
                              content[toc_idx + len('\\tableofcontents'):].lstrip('\n')
                    modified = True
                    result.fix(f"Added newpage after TOC: {f}")
                else:
                    result.fail(f"Missing newpage after TOC: {f}")

        # Check for \pagestyle{fancy} and headers — auto-fix by deriving from \title and path
        header_block = []
        if '\\pagestyle{fancy}' not in content or '\\lhead' not in content or \
           '\\rhead' not in content or '\\cfoot' not in content:
            # Try to extract course name and chapter info from \title or path
            course_name = ''
            chapter_info = ''
            # Parse \title content using brace counting
            title_start = content.find('\\title{')
            if title_start != -1:
                depth = 0
                raw_title = ''
                for ch in content[title_start + 7:]:
                    if ch == '{':
                        depth += 1
                        raw_title += ch
                    elif ch == '}':
                        if depth == 0:
                            break
                        depth -= 1
                        raw_title += ch
                    else:
                        raw_title += ch
                # Strip ALL LaTeX formatting commands repeatedly
                clean = raw_title
                for _ in range(5):
                    clean = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', clean)
                # Replace LaTeX linebreaks: \\, \\[4pt], or literal newlines → separator
                clean = re.sub(r'\\{1,2}\[[^\]]*\]', ' | ', clean)  # \[4pt] or \\[4pt]
                clean = re.sub(r'\\\\', ' | ', clean)  # bare \\
                clean = re.sub(r'\n', ' | ', clean)
                # Strip remaining commands like \Large, \small
                clean = re.sub(r'\\[a-zA-Z]+\b\s*', '', clean)
                clean = re.sub(r'[{}]', '', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                # Split on separator to get course name (first part)
                parts = [p.strip() for p in clean.split('|') if p.strip()]
                course_name = parts[0] if parts else clean
            # Get chapter number from path
            ch_match = re.search(r'ch(\d+)', f)
            ch_num = ch_match.group(1) if ch_match else '?'

            if '\\pagestyle{fancy}' not in content:
                header_block.append('\\pagestyle{fancy}')
            if '\\lhead' not in content:
                if course_name:
                    header_block.append(f'\\lhead{{{{\\small {course_name} \\\\quad Chapter {ch_num}}}}}')
                else:
                    header_block.append(f'\\lhead{{{{\\small Chapter {ch_num}}}}}')
            if '\\rhead' not in content:
                # Try to find semester from \author or just use generic
                author_match = re.search(r'\\author\{(.+?)\}', content)
                semester = ''
                if author_match:
                    a = author_match.group(1)
                    sem_match = re.search(r'((?:Fall|Spring|Summer|Winter)\s+\d{4})', a)
                    if sem_match:
                        semester = sem_match.group(1)
                if semester:
                    header_block.append(f'\\rhead{{{{\\small {semester}}}}}')
                else:
                    header_block.append('\\rhead{{\\small}}')
            if '\\cfoot' not in content:
                header_block.append('\\cfoot{\\thepage}')

        if header_block:
            if do_fix and '\\begin{document}' in content:
                inject = '\n'.join(header_block) + '\n'
                content = content.replace('\\begin{document}', inject + '\\begin{document}')
                modified = True
                result.fix(f"Injected missing header commands ({len(header_block)}) derived from title/path: {f}")
            else:
                for h in header_block:
                    cmd = h.split('{')[0]
                    result.fail(f"Missing {cmd}: {f}")

        # Check \title exists and has the right structure
        if '\\title' not in content:
            result.fail(f"Missing \\title: {f}")
        else:
            # Title should have course name on line 1 and chapter on line 2
            # Find title content (handle nested braces)
            title_start = content.find('\\title{')
            if title_start != -1:
                # Count braces to find matching close
                depth = 0
                title_content = ''
                for ch in content[title_start + 7:]:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        if depth == 0:
                            break
                        depth -= 1
                    title_content += ch
                if '\\\\' not in title_content:
                    result.warn(f"Title may be single-line (should have course name + chapter): {f}")

        # Check for fancyhdr package
        if 'fancyhdr' not in content:
            result.fail(f"Missing fancyhdr package: {f}")

        # Check box usage
        for box in ['defbox', 'thmbox', 'exbox']:
            if f'\\begin{{{box}}}' not in content:
                result.warn(f"No {box} used in: {f}")

        if modified:
            write_file(f, content)

        if not modified and not any(f in msg for msg in result.fails + result.warnings):
            print(f"  OK: {f}")

    # Questions files checks
    for f in question_files:
        content = read_file(f)
        modified = False

        # Questions must NOT have TOC
        if '\\tableofcontents' in content:
            if do_fix:
                content = content.replace('\\tableofcontents', '')
                content = re.sub(r'\n\s*\\newpage\s*\n', '\n', content, count=1)
                write_file(f, content)
                result.fix(f"Removed TOC from questions: {f}")
                modified = True
            else:
                result.fail(f"Forbidden TOC in questions: {f}")

        # Questions must have \maketitle
        if '\\maketitle' not in content:
            if do_fix and '\\begin{document}' in content:
                content = content.replace('\\begin{document}', '\\begin{document}\n\\maketitle')
                write_file(f, content)
                result.fix(f"Added missing maketitle to questions: {f}")
                modified = True
            else:
                result.fail(f"Missing maketitle in questions: {f}")

        # Check for \thispagestyle{fancy} after \maketitle
        if '\\maketitle' in content and '\\thispagestyle{fancy}' not in content:
            if do_fix:
                content = content.replace('\\maketitle', '\\maketitle\n\\thispagestyle{fancy}')
                modified = True
                result.fix(f"Added \\thispagestyle{{fancy}} after \\maketitle in questions: {f}")

        # Questions must have headers — auto-fix by deriving from \title and path
        q_header_block = []
        if '\\pagestyle{fancy}' not in content or '\\lhead' not in content or \
           '\\rhead' not in content or '\\cfoot' not in content:
            course_name = ''
            title_start = content.find('\\title{')
            if title_start != -1:
                depth = 0
                raw_title = ''
                for ch in content[title_start + 7:]:
                    if ch == '{':
                        depth += 1
                        raw_title += ch
                    elif ch == '}':
                        if depth == 0:
                            break
                        depth -= 1
                        raw_title += ch
                    else:
                        raw_title += ch
                clean = raw_title
                for _ in range(5):
                    clean = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', clean)
                clean = re.sub(r'\\{1,2}\[[^\]]*\]', ' | ', clean)
                clean = re.sub(r'\\\\', ' | ', clean)
                clean = re.sub(r'\n', ' | ', clean)
                clean = re.sub(r'\\[a-zA-Z]+\b\s*', '', clean)
                clean = re.sub(r'[{}]', '', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                parts = [p.strip() for p in clean.split('|') if p.strip()]
                course_name = parts[0] if parts else clean
            ch_match = re.search(r'ch(\d+)', f)
            ch_num = ch_match.group(1) if ch_match else '?'

            if '\\pagestyle{fancy}' not in content:
                q_header_block.append('\\pagestyle{fancy}')
            if '\\lhead' not in content:
                if course_name:
                    q_header_block.append(f'\\lhead{{{{\\small {course_name} \\\\quad Chapter {ch_num} Practice Problems}}}}')
                else:
                    q_header_block.append(f'\\lhead{{{{\\small Chapter {ch_num} Practice Problems}}}}')
            if '\\rhead' not in content:
                author_match = re.search(r'\\author\{(.+?)\}', content)
                semester = ''
                if author_match:
                    sem_match = re.search(r'((?:Fall|Spring|Summer|Winter)\s+\d{4})', author_match.group(1))
                    if sem_match:
                        semester = sem_match.group(1)
                if semester:
                    q_header_block.append(f'\\rhead{{{{\\small {semester}}}}}')
                else:
                    q_header_block.append('\\rhead{{\\small}}')
            if '\\cfoot' not in content:
                q_header_block.append('\\cfoot{\\thepage}')

        if q_header_block:
            if do_fix and '\\begin{document}' in content:
                inject = '\n'.join(q_header_block) + '\n'
                content = content.replace('\\begin{document}', inject + '\\begin{document}')
                modified = True
                result.fix(f"Injected missing header commands in questions ({len(q_header_block)}) derived from title/path: {f}")
            else:
                for h in q_header_block:
                    cmd = h.split('{')[0]
                    result.fail(f"Missing {cmd} in questions: {f}")

        # Questions must have \title
        if '\\title' not in content:
            result.fail(f"Missing \\title in questions: {f}")

        if not modified and not any(f in msg for msg in result.fails):
            print(f"  OK: {f}")


def check_forbidden_patterns(notes_files, question_files, do_fix, result):
    """Check and optionally fix forbidden patterns."""
    print("\n[4] FORBIDDEN PATTERNS")

    all_files = notes_files + question_files
    for f in all_files:
        content = read_file(f)
        lines = content.split('\n')
        issues = []

        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith('%'):
                continue
            if '$$' in line:
                issues.append(f"  Dollar-dollar math at line {i}")
            if '---' in line and '\\---' not in line:
                issues.append(f"  Em dash at line {i}")
            if '{{' in line and '\\{\\{' not in line:
                # Skip template placeholders like {{COURSE_NAME}}
                if re.search(r'\{\{[A-Z_]+\}\}', line):
                    continue
                # Skip LaTeX double braces like {{\small ...}}
                if re.search(r'\{\{\\', line):
                    continue
                issues.append(f"  Unreplaced placeholder at line {i}")
            if 'Co-authored-by' in line:
                issues.append(f"  Co-authored trailer at line {i}")

        if issues:
            for iss in issues:
                result.fail(f"{f}: {iss}")
        else:
            print(f"  OK: {f}")

    # Check that every figure and table has \caption and \label
    for f in all_files:
        content = read_file(f)
        # Find all \begin{figure} blocks
        for env, label_prefix in [('figure', 'fig:'), ('table', 'tab:')]:
            starts = [m.start() for m in re.finditer(r'\\begin\{' + env + r'\}', content)]
            for s in starts:
                # Find matching \end{env}
                end = content.find(f'\\end{{{env}}}', s)
                if end == -1:
                    continue
                block = content[s:end]
                line_num = content[:s].count('\n') + 1
                if '\\caption' not in block:
                    result.fail(f"{f} line {line_num}: {env} without \\caption")
                if f'\\label{{{label_prefix}' not in block and '\\label{' not in block:
                    result.warn(f"{f} line {line_num}: {env} without \\label{{{label_prefix}...}}")

    # Check for excessive \newpage usage
    for f in all_files:
        content = read_file(f)
        body_start = content.find('\\begin{document}')
        if body_start == -1:
            continue
        body = content[body_start:]

        # Count newpage/clearpage/pagebreak in the body
        newpages = [(m.start(), m.group()) for m in re.finditer(r'\\(newpage|clearpage|pagebreak)', body)]

        # Allowed: 1 after \tableofcontents, 1 before Part II in questions
        allowed = 0
        if '\\tableofcontents' in body:
            allowed += 1
        if 'questions' in f:
            allowed += 2  # one after maketitle, one between Part I and Part II

        if len(newpages) > allowed:
            excess = len(newpages) - allowed
            if do_fix:
                # Remove newpages that are NOT right after \tableofcontents
                # and NOT before "Part II" or "\part"
                lines = content.split('\n')
                removed = 0
                new_lines = []
                skip_next_empty = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped in ('\\newpage', '\\clearpage', '\\pagebreak'):
                        # Check if this is after TOC
                        prev_content = '\n'.join(new_lines[-3:]) if len(new_lines) >= 3 else ''
                        # Check if next non-empty line is Part II or section
                        next_lines = [l.strip() for l in lines[i+1:i+4] if l.strip()]
                        next_content = next_lines[0] if next_lines else ''

                        is_after_toc = '\\tableofcontents' in prev_content
                        is_after_maketitle = '\\maketitle' in prev_content or '\\thispagestyle' in prev_content
                        is_before_part2 = 'Part II' in next_content or '\\part' in next_content

                        if is_after_toc or is_after_maketitle or is_before_part2:
                            new_lines.append(line)  # keep it
                        else:
                            removed += 1  # skip it
                            skip_next_empty = True
                            continue
                    elif skip_next_empty and stripped == '':
                        skip_next_empty = False
                        continue  # remove blank line after removed newpage
                    else:
                        skip_next_empty = False
                    new_lines.append(line)

                if removed > 0:
                    write_file(f, '\n'.join(new_lines))
                    result.fix(f"Removed {removed} unnecessary \\newpage commands: {f}")
            else:
                result.warn(f"{f}: has {len(newpages)} newpage/clearpage commands (expected max {allowed}) — likely wasting space")


def check_notation(notes_files, question_files, do_fix, result):
    """Check for raw macros that should use shortcuts."""
    print("\n[5] NOTATION CONSISTENCY")

    raw_patterns = [
        (r'\\mathbb\{R\}', '\\R'),
        (r'\\mathbb\{N\}', '\\N'),
        (r'\\mathbb\{Q\}', '\\Q'),
        (r'\\mathbb\{Z\}', '\\Z'),
    ]

    all_files = notes_files + question_files
    for f in all_files:
        content = read_file(f)
        file_issues = False

        for pattern, macro in raw_patterns:
            # Only check in body, not preamble
            body_start = content.find('\\begin{document}')
            if body_start == -1:
                continue
            body = content[body_start:]
            # Skip lines that are newcommand definitions
            for i, line in enumerate(body.split('\n'), 1):
                if 'newcommand' in line or line.strip().startswith('%'):
                    continue
                if re.search(pattern, line):
                    if do_fix:
                        new_body = re.sub(pattern, macro, body)
                        content = content[:body_start] + new_body
                        write_file(f, content)
                        result.fix(f"Replaced raw macro with {macro}: {f}")
                    else:
                        result.fail(f"Raw macro (use {macro}): {f}")
                    file_issues = True
                    break

        if not file_issues:
            print(f"  OK: {f}")


def check_box_styling(notes_files, question_files, do_fix, result):
    """Verify boxes use enhanced + shadow styling."""
    print("\n[6] BOX STYLING")

    all_files = notes_files + question_files
    for f in all_files:
        content = read_file(f)
        if 'newtcolorbox' not in content:
            continue

        issues = []
        fixed_something = False

        if 'enhanced' not in content:
            issues.append("Missing 'enhanced'")
        if 'drop shadow' not in content:
            issues.append("Missing 'drop shadow'")
        if 'skins' not in content:
            issues.append("Missing 'skins' library")
        if re.search(r'colback\s*=\s*\w+!\d+', content):
            issues.append("Using flat colors (e.g., green!4) instead of hex")

        # Boxes must use 'enhanced jigsaw' (not plain 'enhanced') for clean page breaks
        if 'enhanced jigsaw' not in content and 'enhanced,' in content:
            if do_fix:
                content = content.replace('enhanced,', 'enhanced jigsaw,')
                fixed_something = True
                issues.append("Fixed enhanced → enhanced jigsaw (clean page breaks)")
            else:
                issues.append("Boxes use 'enhanced' instead of 'enhanced jigsaw' — breaks look ugly")

        # Boxes must have 'pad at break*=2mm' for spacing at page breaks
        if 'breakable' in content and 'pad at break' not in content:
            if do_fix:
                content = content.replace('drop shadow southeast}',
                    'pad at break*=2mm,\n  drop shadow southeast}')
                fixed_something = True
                issues.append("Fixed: added 'pad at break*=2mm' for clean page breaks")
            else:
                issues.append("Breakable boxes missing 'pad at break*=2mm'")

        if fixed_something:
            write_file(f, content)
            for i in issues:
                if 'Fixed' in i:
                    result.fix(f"{f}: {i}")
                else:
                    result.fail(f"{f}: {i}")
        elif issues:
            for iss in issues:
                result.fail(f"{f}: {iss}")
        else:
            print(f"  OK: {f}")


def check_hyperref(notes_files, question_files, result):
    """All files must have identical hypersetup."""
    print("\n[7] HYPERREF CONSISTENCY")

    all_files = notes_files + question_files
    setups = {}
    for f in all_files:
        content = read_file(f)
        m = re.search(r'\\hypersetup\{([^}]+)\}', content, re.DOTALL)
        if m:
            setups[f] = m.group(1).strip()

    if len(set(setups.values())) <= 1:
        print("  OK: All hypersetup blocks match.")
    else:
        ref_setup = list(setups.values())[0] if setups else None
        for f, s in setups.items():
            if s != ref_setup:
                result.fail(f"Hypersetup mismatch: {f}")


def analyze_pdfs(repo, result):
    """Analyze every PDF for rendering issues: cut boxes, overlapping text, blank pages."""
    print("\n[8] PDF ANALYSIS")

    try:
        import fitz
    except ImportError:
        result.warn("pymupdf not installed, skipping PDF analysis")
        return

    screenshot_dir = os.path.join(repo, '_screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)

    pdf_count = 0
    screenshot_count = 0

    for root, dirs, files in os.walk(repo):
        if '_screenshots' in root:
            continue
        for f in files:
            if not f.endswith('.pdf'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, repo)
            try:
                doc = fitz.open(path)
                pdf_count += 1

                for i in range(len(doc)):
                    page = doc[i]
                    page_h = page.rect.height
                    page_w = page.rect.width
                    text_dict = page.get_text("dict")

                    # ── Check 1: Text cut at page bottom ──
                    # If text content exists in the last 15 points of the page,
                    # a box or paragraph is likely split awkwardly
                    for block in text_dict.get("blocks", []):
                        if block["type"] != 0:  # text blocks only
                            continue
                        bbox = block["bbox"]
                        if bbox[3] > page_h - 15 and bbox[1] > page_h - 60:
                            # Text block starts AND ends near the bottom = cut content
                            result.warn(f"Possible cut box/text at bottom of page {i+1}: {rel}")
                            break

                    # ── Check 2: Text overlapping (two text blocks at same position) ──
                    spans = []
                    for block in text_dict.get("blocks", []):
                        if block["type"] != 0:
                            continue
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                if span["text"].strip():
                                    spans.append({
                                        "y": round(span["bbox"][1], 0),
                                        "x": round(span["bbox"][0], 0),
                                        "text": span["text"][:30]
                                    })

                    # Group spans by approximate y position
                    from collections import defaultdict
                    y_groups = defaultdict(list)
                    for s in spans:
                        y_groups[s["y"]].append(s)

                    for y, group in y_groups.items():
                        if len(group) > 8:
                            # Many text spans at the exact same y = possible overlap
                            xs = sorted([s["x"] for s in group])
                            # Check if multiple spans start at very close x positions
                            for j in range(len(xs) - 1):
                                if xs[j+1] - xs[j] < 2 and xs[j+1] - xs[j] >= 0:
                                    result.warn(f"Possible overlapping text at page {i+1}, y={y}: {rel}")
                                    break

                    # ── Check 3: Blank pages ──
                    text = page.get_text().strip()
                    if len(text) < 10 and i > 0:  # Skip first page if it's just a title
                        result.warn(f"Nearly blank page {i+1}: {rel}")

                    # ── Check 4: Content outside margins ──
                    margin = 30  # ~0.4 inches
                    for block in text_dict.get("blocks", []):
                        if block["type"] != 0:
                            continue
                        bbox = block["bbox"]
                        if bbox[0] < margin and bbox[2] - bbox[0] > 50:
                            result.warn(f"Content may extend into left margin on page {i+1}: {rel}")
                            break
                        if bbox[2] > page_w - margin and bbox[2] - bbox[0] > 50:
                            result.warn(f"Content may extend into right margin on page {i+1}: {rel}")
                            break

                    # ── Screenshot every page ──
                    pix = page.get_pixmap(dpi=150)
                    slug = rel.replace('/', '_').replace('.pdf', '')
                    out = os.path.join(screenshot_dir, f"{slug}_p{i+1}.png")
                    pix.save(out)
                    screenshot_count += 1

                doc.close()
            except Exception as e:
                result.warn(f"Could not analyze {path}: {e}")

    print(f"  Analyzed {pdf_count} PDFs, generated {screenshot_count} screenshots in _screenshots/")
    if screenshot_count > 0:
        result.warn(f"VISUAL CHECK NEEDED: Review screenshots in _screenshots/ for issues the script cannot catch (figure quality, aesthetic problems)")


def compile_all(repo, result):
    """Compile every .tex file twice."""
    print("\n[9] COMPILE ALL")

    for root, dirs, files in os.walk(os.path.join(repo, 'chapters')):
        for f in files:
            if not f.endswith('.tex'):
                continue
            path = os.path.join(root, f)
            for pass_num in [1, 2]:
                r = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f],
                    cwd=root, capture_output=True, text=True
                )
                if r.returncode != 0:
                    # Check for actual errors (not just warnings)
                    log = os.path.join(root, f.replace('.tex', '.log'))
                    if os.path.exists(log):
                        with open(log) as lf:
                            for line in lf:
                                if line.startswith('!'):
                                    result.fail(f"Compile error in {path}: {line.strip()}")
                                    break

    # Also compile top-level files
    for f in ['cheatsheet.tex', 'compressed_notes.tex']:
        path = os.path.join(repo, f)
        if os.path.isfile(path):
            for _ in [1, 2]:
                subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f],
                    cwd=repo, capture_output=True
                )

    print("  Compilation complete.")


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Format checker and auto-fixer')
    parser.add_argument('repo', nargs='?', default='.', help='Path to repo')
    parser.add_argument('--fix', action='store_true', help='Auto-fix deterministic issues')
    parser.add_argument('--visual', action='store_true', help='Analyze PDFs and generate screenshots')
    parser.add_argument('--template', type=str, default=None,
                        help='Path to template repo (golden reference). If not given, uses ch1 of the repo as reference.')
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    result = CheckResult()

    notes_files = find_files(repo, 'notes.tex', 'notes')
    question_files = find_files(repo, 'questions.tex', 'questions')

    # Determine reference files (template is golden, fallback to ch1)
    template_dir = None
    if args.template:
        template_dir = os.path.abspath(args.template)
    
    ref_notes = None
    ref_questions = None
    if template_dir:
        t_notes = find_files(template_dir, 'notes.tex', 'notes')
        t_questions = find_files(template_dir, 'questions.tex', 'questions')
        ref_notes = t_notes[0] if t_notes else None
        ref_questions = t_questions[0] if t_questions else None

    print(f"Repo: {repo}")
    if template_dir:
        print(f"Template: {template_dir}")
    print(f"Notes files: {len(notes_files)}")
    print(f"Question files: {len(question_files)}")
    print("Mode:", "FIX" if args.fix else "CHECK ONLY")
    print("=" * 70)

    # Deterministic checks (can auto-fix)
    check_and_fix_preamble(repo, notes_files, question_files, args.fix, result,
                           ref_notes_path=ref_notes, ref_questions_path=ref_questions)
    check_document_class(notes_files, question_files, result)
    check_required_elements(notes_files, question_files, args.fix, result)
    check_forbidden_patterns(notes_files, question_files, args.fix, result)
    check_notation(notes_files, question_files, args.fix, result)

    # Style checks (report only, can't auto-fix safely)
    check_box_styling(notes_files, question_files, args.fix, result)
    check_hyperref(notes_files, question_files, result)

    # Compile everything
    if args.fix:
        compile_all(repo, result)

    # Visual inspection
    if args.visual:
        analyze_pdfs(repo, result)

    return result.report()


if __name__ == '__main__':
    sys.exit(main())
