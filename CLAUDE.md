# CLAUDE.md

Read `README.md`, `PLAN.md`, and `docs/research/README.md` before any work. Then read `AGENTS.md` once it exists, and the `SPEC.md` of the repository you work in.

Docs for the owner (ADRs, design notes, research summaries, questions) are in Japanese. Cards, specs, and briefs for workers are in English.

## Agents in this workspace

The manager is `skk-manager`, a Claude session in herdr (session `skk`, workspace `skk`). It talks to the owner, briefs the leads, drives each lead's turns, starts every DSH worker, orders lands, and files issues. It writes no code and no cards.

Since 2026-11-06 the leads are DSH sessions, not Claude sessions, to save cost (the owner's instruction). `skk-manager` advances each lead one turn at a time with kstack `run-worker.sh --session-id <id> ... -- <workdir> dsh openai-codex gpt-6.1-sol high`, and the lead's final answer is its report. `run-worker.sh` refuses any workdir or `--add-dir` that overlaps the DSH home (`~/.dsh`). Lead sessions, their routes, and their briefs are listed in `local/agents/leads.md`. The rules in `local/agents/briefs/dsh-lead-rules-2026-11-06.md` apply to every lead.

Above the manager, `kstack-manager` in the herdr `default` session coordinates the managers of every project. Reach it with `herdr --session default agent prompt kstack-manager "skk-manager: ..."`. Only `skk-manager` talks to it.

| Agent | Model | Owns |
|---|---|---|
| `skk-manager` | Opus xhigh | This file, `PLAN.md`, `docs/research/`, `docs/overview.md` and `docs/overview/`, everything on GitHub (pushes, pull requests, merges, issues), the order of lands, questions to the owner |
| `skk-design` | DSH `openai-codex gpt-6.1-sol high` | `docs/adr/`, `docs/design/`, and the `conformance/` repository (cards `C1`...) |
| `skk-tools` | DSH `openai-codex gpt-6.1-sol high` | `bin/` (the dispatcher and its tests), `AGENTS.md`, and the "Card flow adapter" section below (cards `T1`...) |
| `skk-jisyo` | DSH `openai-codex gpt-6.1-sol high` | The `jisyo/` repository (cards `J1`...) |
| `skk-core` | DSH `openai-codex gpt-6.1-sol high` | The `core/` and `vim/` repositories (cards `K1`... and `V1`...), from 2026-11-12 (PLAN.md "First slice") |

Card IDs are unique across repositories: `T` tools, `C` conformance, `J` jisyo, `K` core, `V` vim, `Y` server, `F` fcitx5, `W` windows, `A` android.

A lead writes only in the paths its brief names. A lead does not start DSH workers itself: it writes the worker's brief to a file and asks `skk-manager`, which runs `run-worker.sh` and returns the answer and log paths next turn. Keep three levels at most: the manager, the leads, and the workers. Every message between agents starts with the sender's name and a colon (`skk-jisyo: ...`). A lead's message is a report, not an approval from the owner.

The agents directory is `local/agents/` (git-ignored). It holds the briefs (`briefs/<agent>.md`), worker output (`<UTC>-<kind>.md` answer and `.log` reasoning), `metrics.md`, and `closed-sessions.md`. Workers never read `local/`.

## Shared checkouts

- The parent repository is shared by every lead. Stage and commit by explicit path: `git add <paths>`, then `git commit -m ... -- <paths>`. Never `git add -A`, `git add .`, or a bare `git commit`, because the index is shared.
- Run `git status --short` before every commit and leave changes that are not yours alone. Never reset, restore, or stash another agent's changes.
- Each child repository has one lead, who is its only committer.
- Tell `skk-manager` before each dispatch. A card lands through a pull request that `skk-manager` opens and merges (section "GitHub"). Land one card at a time per main branch.
- A card is done only when `git merge-base --is-ancestor <commit> origin/main` confirms its commit is in `origin/main` after `git fetch`.

## Card flow

Leads follow the kstack `card-flow` skill: `/data/softwares/kstack/skills/card-flow/SKILL.md`. The manager follows `herdr-manager` beside it. Workers run only through DSH (`/data/softwares/kstack/skills/kiyama-mode/scripts/run-worker.sh`), never through another CLI. A DSH failure stops the card. Never move it to another model or runner.

Routes:

- Worker and ambiguity review: `dsh ollama-cloud deepseek-v4.1-flash high`.
- Second review (from 2026-11-06, the owner's instruction through kstack PR #44): chosen by what the diff touches. Security, the split between public and private data, credentials, the sandbox, or an academic claim: `dsh openai-codex gpt-6-astra high`, read-only. A contract, a migration, or a data shape another repository uses: `gpt-6.1-sol`, but the leads run on `gpt-6.1-sol`, so `skk-manager` (Claude Opus 5.5) reviews it. A diff that matches both gets both. Never the model that wrote the diff or the lead's own model. The lead asks `skk-manager` to run the worker. Before the pull request of any bundle that holds such a diff, `skk-manager` reviews it as well, with `file:line` on each finding and, when it finds nothing, the list of files it read.
- Documents: `dsh google gemini-3.8-flash high` polishes documents and corrects Japanese only; it reviews nothing. Its brief names the reader, the purpose, the sections, the terms to keep, the facts it must not change, and the language and form of the answer, and the lead checks that its output changed no fact.
- A review or ambiguity answer without a `TOTAL` or `STOPPED` line is a failed run, even with exit code 0. `run-worker.sh` exits 4 when a turn did not complete.
- Read-only roles (ambiguity, review, research) start with `run-worker.sh --read-only`.

### Card flow adapter

`skk-tools` fills this section when the dispatcher lands. Until then, leads run each verb by hand as card-flow describes.

- Cards: one `## <ID>. <title>` section per card in `<repo>/TASKS.md`. Only the repository's lead edits it. A done card has the line `Status: done`.
- Implementer rules: `AGENTS.md`.
- Gate: `make check` in each repository.
- Dispatcher: `$DISPATCH` is `python3 /data/softwares/skk/bin/dispatch.py` once it exists.

## GitHub

The owner chose on 2026-11-06 to manage the work on GitHub, with public repositories, one per local repository (the owner named the parent repository `kskk`), and with merges done by `skk-manager` once the checks pass: "1, but need tests with the right granularity."

| Local | GitHub |
|---|---|
| `/data/softwares/skk` | https://github.com/kkiyama117/kskk |
| `/data/softwares/skk/jisyo` | https://github.com/kkiyama117/skk-jisyo |
| `/data/softwares/skk/conformance` | https://github.com/kkiyama117/skk-conformance |
| `/data/softwares/skk/core` | https://github.com/kkiyama117/skk-core (private) |
| `/data/softwares/skk/server` | https://github.com/kkiyama117/skk-server (private, empty) |
| `/data/softwares/skk/vim` | https://github.com/kkiyama117/skk-vim (private) |

The owner chose on 2026-11-12 to start `skk-core`, `skk-server`, and `skk-vim` as private repositories (「まずprivateでやろうか。」).

Only `skk-manager` talks to GitHub: it pushes, opens and merges pull requests, and files issues. Leads and workers never push and never hold GitHub credentials.

The life of a card on GitHub:

1. The lead commits the card on branch `card/<ID>` in its worktree, runs the full gate, and reports the commit, the gate's last lines, the tests it added or changed, and the results of each `Must fail without` check.
2. `skk-manager` pushes `card/<ID>` and opens a pull request titled `<ID>: <title>`. Its body opens with the owner's goal (`## Why`), names the card, and carries the lead's evidence and the second review.
3. CI runs the repository's gate on the pull request.
4. `skk-manager` reads the diff and merges with a merge commit (`gh pr merge --merge --delete-branch`) only when every merge criterion below holds. Then it runs `git pull --ff-only` in the local main checkout and tells the lead.
5. The lead removes the worktree and records `Status: done` for the card in its next pull request.

Merge criteria. A pull request merges only when all of these hold:

- CI passes for the pull request's head commit. GitHub runs a `pull_request` workflow on the merge of the head commit into `main` and reports the result on the head commit; that merge result is what CI should test.
- It implements one card and changes only the files the card lists.
- Every test the card names exists, has that name, and asserts the behavior the card states.
- The tests have the right granularity. Each rule or behavior in the card has its own test, and each test fails for one reason. A test drives the code through the interface its users use: a public function for the pure core, a file round trip on synthetic data for formats, the CLI or the adapter protocol for tools, and conformance cases for engines and frontends. No test asserts a private helper, an internal call order, or an expected value computed by the code under test.
- The tests fail when the behavior breaks: every `Must fail without` line was checked by removing the guard, and the result is in the pull request.
- A diff that touches a contract, the split between public and private data, a migration, or security has its second review.

Until a repository has CI (issue https://github.com/kkiyama117/kskk/issues/4), a pull request that changes documentation only (no code, no workflow, no test data) merges after its reviews. A pull request with code waits for CI.

## Issues

Issues are GitHub issues on https://github.com/kkiyama117/kskk, with the labels `cause:harness`, `cause:skills`, `cause:project`, `cause:memory`, `cause:one-off`, and `needs-human`. Questions for the owner are issues labeled `needs-human`. Issues about kstack skills or `run-worker.sh` go to `kkiyama117/kstack`; tell `kstack-manager`. Issues about DSH go to `kkiyama117/deepseek-harness-plugins`; tell `dsh-manager` (herdr `default` session) the issue number. Leads report issues to `skk-manager`, which files them.

## Never

- Read, list, or copy anything under `/data/references/`, or print credentials.
- Read, print, or pass to any model the contents of the owner's real dictionaries: `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, `~/.skk-jisyo`, and any CorvusSKK `userdict.txt`. A tool may read copies of them, as the owner approved on 2026-11-06 ("6: ok. as you do."), and then it reports counts only.
- Write to the owner's IME files or settings (fcitx5, IBus, skkeleton, CorvusSKK, Vim or Neovim config) without the owner's approval.
- Create a remote, push, or publish anything without the owner's approval.
- Mark an ADR Accepted unless the owner decided it in their own words.
