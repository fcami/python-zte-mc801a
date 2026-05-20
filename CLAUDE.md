# CLAUDE.md — working rules for this repository

These rules apply to any Claude (or Claude-driven) session operating on
this repository. They are not aspirational; treat them as gating
conditions on ending a turn or making a commit.

## End-of-turn invariants

- **Never end a turn with untracked files in the working tree.** If a
  file is intentionally transient, add it to `.gitignore` in the same turn.
  If it is work-in-progress, commit it on a branch or stash it. Abandoning
  files in `git status`'s "Untracked" section is forbidden.
- **Never end a turn with the test suite or linter red.** Run `python -m
  pytest tests/ -v` and `python -m flake8 python_zte_mc801a/ tests/` before
  declaring a turn complete. If either is red, fix it or revert.
- **Never end a turn with secrets in tracked files.** `settings.yml`,
  `watchdog.yml`, and `data.json` are gitignored for a reason — they hold
  plaintext credentials or runtime state. If you add a new config file with
  secrets, gitignore it in the same turn.

## Commit discipline (Beck / Fowler)

- **Smallest meaningful change.** Each commit represents one logical
  change. If the subject line wants to say "and", split the commit.
- **Green at every revision.** Tests and lint must pass at every commit,
  not just at the branch tip. The repo must be checkout-and-run from any
  single commit on `master`.
- **Tidy first.** Refactoring commits are separate from behaviour-change
  commits. If you must restructure to make a feature easy, land the
  restructuring first, then the feature — never in the same commit.
- **Tests travel with code.** New behaviour and the tests that verify it
  land in the same commit. Do not split production code into commit N and
  its tests into commit N+1.
- **One concern per commit.** A single commit does not simultaneously add
  a feature, fix an unrelated bug, bump a dependency, and reformat code.
  Each concern is its own commit.
- **No commented-out code, no debug prints, no `TODO: remove this`
  markers in committed files.** Git history is the archive for things that
  might be needed later.

## Commit message format

- Subject ≤ 72 characters, imperative mood (`add X`, not `added X` or
  `adds X`). Conventional Commits prefixes (`feat:`, `fix:`, `chore:`,
  `docs:`, `refactor:`, `test:`) are used in this repo and should continue.
- Body wrapped at ~72 columns, separated from the subject by a blank
  line. The body explains **why**, not what — the diff already shows what.
- Reference the audit gap, TODO item, or user-story ID in the body when
  applicable (e.g. `Closes audit gap 1 / TODO item 3`).
- No `Co-Authored-By` trailer unless the user explicitly requests it.

## Git safety

- **Stage files explicitly by name.** Never `git add -A`, `git add .`, or
  `git add -u`. Those globs would catch `settings.yml`, `watchdog.yml`, or
  `data.json` if they ever appear unstaged before `.gitignore` is updated.
- **Never `--amend` a commit that has been pushed.** For unpushed
  commits, `--amend` is permitted only on the most recent commit for
  message fixes or forgotten files.
- **Never `--no-verify`, `--no-gpg-sign`, or `--signoff` unless the user
  explicitly requests it.** If a hook fails, fix the underlying issue.
- **Never `git push --force` to `master`.** If a force-push is genuinely
  needed (e.g. an accidentally pushed secret), stop and ask the user first.
- **Never run `git reset --hard`, `git clean -fd`, or `git checkout --`
  to discard work without confirming with the user first.** Investigate
  unfamiliar files before deleting; they may be the user's in-progress
  work.

## When in doubt

Ask before committing if the change touches files outside the immediate
task, spans multiple logical concerns, or modifies CI / hooks /
`.gitignore` / `pyproject.toml`. The cost of one clarifying question is
low; the cost of an unwanted commit — especially one containing
credentials — is high.
