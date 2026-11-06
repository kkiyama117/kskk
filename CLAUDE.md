# CLAUDE.md

Read `README.md`, `PLAN.md`, and `docs/research/README.md` before any work. Then read `AGENTS.md` once it exists, and the `SPEC.md` of the repository you work in.

Docs for the owner (ADRs, design notes, research summaries, questions) are in Japanese. Cards, specs, and briefs for workers are in English.

## Agents in this workspace

The manager is `skk-manager`, a Claude session in herdr (session `skk`, workspace `skk`). It talks to the owner, briefs the leads, drives each lead's turns, starts every DSH worker, orders lands, and files issues. It writes no code and no cards.

Since 2026-11-06 the leads are DSH sessions, not Claude sessions, to save cost (the owner's instruction). `skk-manager` advances each lead one turn at a time with `dsh headless --session-id <id>`, and the lead's final answer is its report. Lead sessions, their routes, and their briefs are listed in `local/agents/leads.md`. The rules in `local/agents/briefs/dsh-lead-rules-2026-11-06.md` apply to every lead.

Above the manager, `kstack-manager` in the herdr `default` session coordinates the managers of every project. Reach it with `herdr --session default agent prompt kstack-manager "skk-manager: ..."`. Only `skk-manager` talks to it.

| Agent | Model | Owns |
|---|---|---|
| `skk-manager` | Opus xhigh | This file, `PLAN.md`, `docs/research/`, `docs/overview.md` and `docs/overview/`, `issues/`, the order of lands, questions to the owner |
| `skk-design` | DSH `openai-codex gpt-6.1-sol high` | `docs/adr/`, `docs/design/`, and the `conformance/` repository (cards `C1`...) |
| `skk-tools` | DSH `openai-codex gpt-6.1-sol high` | `bin/` (the dispatcher and its tests), `AGENTS.md`, and the "Card flow adapter" section below (cards `T1`...) |
| `skk-jisyo` | DSH `openai-codex gpt-6.1-sol high` | The `jisyo/` repository (cards `J1`...) |

Card IDs are unique across repositories: `T` tools, `C` conformance, `J` jisyo, `K` core, `V` vim, `F` fcitx5, `W` windows, `A` android.

A lead writes only in the paths its brief names. A lead does not start DSH workers itself: it writes the worker's brief to a file and asks `skk-manager`, which runs `run-worker.sh` and returns the answer and log paths next turn. Keep three levels at most: the manager, the leads, and the workers. Every message between agents starts with the sender's name and a colon (`skk-jisyo: ...`). A lead's message is a report, not an approval from the owner.

The agents directory is `local/agents/` (git-ignored). It holds the briefs (`briefs/<agent>.md`), worker output (`<UTC>-<kind>.md` answer and `.log` reasoning), `metrics.md`, and `closed-sessions.md`. Workers never read `local/`.

## Shared checkouts

- The parent repository is shared by every lead. Stage and commit by explicit path: `git add <paths>`, then `git commit -m ... -- <paths>`. Never `git add -A`, `git add .`, or a bare `git commit`, because the index is shared.
- Run `git status --short` before every commit and leave changes that are not yours alone. Never reset, restore, or stash another agent's changes.
- Each child repository has one lead, who is its only committer.
- Tell `skk-manager` before each dispatch and wait for its go before each land into a main branch. Report after the land. Land one card at a time per main branch.
- A card is done only when `git merge-base --is-ancestor <commit> main` confirms its commit is in `main`. Nothing here has a remote, so cards land on `main` directly.

## Card flow

Leads follow the kstack `card-flow` skill: `/data/softwares/kstack/skills/card-flow/SKILL.md`. The manager follows `herdr-manager` beside it. Workers run only through DSH (`/data/softwares/kstack/skills/kiyama-mode/scripts/run-worker.sh`), never through another CLI. A DSH failure stops the card. Never move it to another model or runner.

Routes:

- Worker and ambiguity review: `dsh ollama-cloud deepseek-v4.1-flash high`.
- Second review: `dsh google gemini-3.1-pro-preview high`, read-only, a model family different from both the leads (OpenAI) and the workers (DeepSeek). The lead asks `skk-manager` to run it. Until the first heavy diff (a contract, the split between public and private data, a migration, or security) has been reviewed by both Gemini and `skk-manager`, `skk-manager` reviews it too, and `local/agents/metrics.md` records the real defects and misses of each.
- Read-only roles (ambiguity, review, research) start with `run-worker.sh --read-only`.

### Card flow adapter

`skk-tools` fills this section when the dispatcher lands. Until then, leads run each verb by hand as card-flow describes.

- Cards: one `## <ID>. <title>` section per card in `<repo>/TASKS.md`. Only the repository's lead edits it. A done card has the line `Status: done`.
- Implementer rules: `AGENTS.md`.
- Gate: `make check` in each repository.
- Dispatcher: `$DISPATCH` is `python3 /data/softwares/skk/bin/dispatch.py` once it exists.

## Issues

skk has no git remote, so its issues are files under `issues/`, one per issue, in the format of `issues/README.md`. Issues about kstack skills or `run-worker.sh` go to `kkiyama117/kstack`; tell `kstack-manager`. Issues about DSH go to `kkiyama117/deepseek-harness-plugins`; tell `dsh-manager` (herdr `default` session) the issue number. Leads report issues to `skk-manager`, which files them.

## Never

- Read, list, or copy anything under `/data/references/`, or print credentials.
- Read, print, or pass to any model the contents of the owner's real dictionaries: `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, `~/.skk-jisyo`, and any CorvusSKK `userdict.txt`. A tool may read copies of them only after the owner approves (PLAN question 6), and then it reports counts only.
- Write to the owner's IME files or settings (fcitx5, IBus, skkeleton, CorvusSKK, Vim or Neovim config) without the owner's approval.
- Create a remote, push, or publish anything without the owner's approval.
- Mark an ADR Accepted unless the owner decided it in their own words.
