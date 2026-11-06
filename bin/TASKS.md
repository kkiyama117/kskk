# Tasks of the parent repository

Only `skk-tools` edits this file. `Files:` paths are relative to the parent repository. `bin/TASKS.md` on a Files line is lead-owned documentation: the worker must not edit it. The lead includes the card and any preceding card's `Status: done` in that card's pull request.

### Project rules for all three cards

- `CLAUDE.md`, sections "GitHub" and "Card flow", overrides card-flow's local fast-forward land and its default second-review route. Only `skk-manager` fetches from GitHub, pushes, opens or merges pull requests, and updates the local main checkout. No dispatcher verb uses the network or advances `main`.
- The worker gate is `python3 -m unittest discover -s bin -p 'test_*.py'`, in its parent worktree. It must not write the actual checkout's git index, objects, or refs. Synthetic git repositories under `tempfile.TemporaryDirectory()` are test data and may have git state written there. Do not add an index-writing gate step.
- Tests for the dispatcher drive its command interface through `dispatch.main(argv, root=<temporary project>, worker=<fake executable>)`, capturing stdout, stderr and its return code. This is the existing in-process CLI harness, not a private-helper test. Assertions use literal expectations from this card, not values returned by another dispatcher helper. Mocks may supply the clock, `PRIME`, or the test repository graph, and may inject an OSError at the standard-library `Path.rmdir` boundary for the root-removal error test. Do not mock a private helper or assert internal calls or their order. A fake executable on `PATH` may cause an external command failure.
- One test function per row in each test table. A row tests one behavior. Its status code, diagnostics and resulting files are facets of that behavior, not independent features to combine with unrelated assertions. Split any retained test that checks independent behaviors into the named tests below. Every guard check removes only the guard, not its error-handling dependencies; a test counts only if the guard's absence causes its assertion or exception failure. Import, compile and fixture failures do not count.
- Workers receive no long-term memory. Every needed decision is in the card or the documents it names. Do not depend on a remembered exception. No worker starts a real DSH process, engine or container in tests.

## T1. Port the dispatcher to skk and finish cards after pull-request merges

Status: open

Needs: nothing in the implementation. Commit 4e8e7a3 in `/data/softwares/skk` copied `bin/dispatch.py` and `bin/test_dispatch.py` from aistore. Read the copies here, not the aistore checkout. Before T1 can merge, the parent CI from T3 must be available. T3 is independent and is intended to merge first.

Spec: this card and the introduction "Project rules for all three cards" in `bin/TASKS.md`; `AGENTS.md`; `CLAUDE.md`, sections "GitHub" and "Card flow"; `/data/softwares/kstack/skills/card-flow/SKILL.md`, sections "Project adapter" and "4. Review the diff".

Files: `bin/dispatch.py`, `bin/test_dispatch.py`, `bin/TASKS.md`.

`bin/TASKS.md` is lead-only. The worker changes only the two Python files. The lead updates the "Card flow adapter" section of `CLAUDE.md` after T2 merges, outside these implementation cards. That section's current `make check` sentence conflicts with the parent gate in `AGENTS.md` rule 19; use the gate in this card.

### Repositories and commands

1. Remove `_go_version`, `write_go_work`, its call, `GOWORK`, Go workspace files and the GOCACHE advice. Replace the old local-merge implementation with the cleanup-only `land` below. Delete `_revert_main`, `_rollback_report`, `_roll_back` and `_fast_forward`; do not retain a local-merge mode, a rollback mode, a flag selecting one, or tests for them.
2. Set `PARENT = 'skk'`, `USES = {'jisyo': [], 'conformance': ['jisyo']}`, `WORKER_ROUTE = ['dsh', 'ollama-cloud', 'deepseek-v4.1-flash', 'high']`, and `REVIEW_ROUTE = ['dsh', 'openai-codex', 'gpt-6-astra', 'high']`. The live project rules replace the former Gemini route. The `review` verb is the external review path for security, privacy, credentials, sandbox changes or academic claims. The lead decides applicability; the dispatcher does not infer categories from a diff. Pure contract, migration or cross-repository data-shape review goes to `skk-manager`, outside this verb, because the specified contract-review model matches the lead's model. A diff in both categories gets Astra and manager review. Gemini polishes documents only and is never a reviewer. Keep `ROOT` as the resolved parent of `bin/`, `KSTACK = Path('/data/softwares/kstack')`, and `WORKER = KSTACK / 'skills/kiyama-mode/scripts/run-worker.sh'`.
3. `repo_dir(root, repo)` returns `root` for `skk`, otherwise `root / repo`. All accesses to main checkouts use it, including branch/status checks, worktree creation/discard, contract discovery, main-review paths and cleanup. Worktrees remain `<root>/local/worktrees/<ID>/<repo>` on `card/<ID>`. `tasks_path(repo)` returns `bin/TASKS.md` for `skk`, otherwise `TASKS.md`.
4. `all_cards(root)` reads `root/bin/TASKS.md` when it is a file as repo `skk`. It also reads `<name>/TASKS.md` for immediate child directories other than `bin` and `local` that have both that file and a `.git` file or directory. Return cards by repository name, then file order. The heading pattern is `## ([A-Z]+[0-9]+)\. (.*)`. A section ends at the next `## ` line. Only a stripped `Status: done` marks it done. `all_cards` also returns draft cards; `Status: draft` is not done. `card` rejects a section containing a stripped `Status: draft`, after its done-card check and before checking the cards file or creating anything, with `card <ID> is draft; finish and review it before dispatch`. If both done and draft markers occur, the done-card rejection wins. No new Card data field is required: the draft marker is available in its text. `Files:` extracts backtick-delimited paths from that line. The card data fields remain `id`, `title`, `repo`, `text`, `done`, `files`.
5. The repository graph is transitive. `users(repo)` is every other repository depending on it, in USES insertion order. A card's set starts with itself and every user, then includes the transitive dependencies of every member, including the card repository's own dependencies, in USES insertion order. A repo outside USES has only itself in its set. For the real graph, both child cards create `jisyo` then `conformance`; only a jisyo card has conformance as a user. Parent cards create only `skk`.
6. Keep the command forms `ambiguity [ID ...]`, `card ID [--no-worker]`, `review ID [--main PATH ...]`, `land ID`. `card` requires its main checkout on `main`, a card marked neither done nor draft as defined in rule 4, a committed cards file, no existing worktree root, and no existing `card/<ID>` branch in its set. Its cards-file status path is `tasks_path(card.repo)`. A dirty main checkout outside that file warns but is not modified. Worktrees start from local `main`, which the manager synchronizes before dispatch. If worktree creation fails, discard only worktrees and branches this invocation created, in reverse order, then remove its worktree root. Do not delete a branch that existed before the invocation.
7. `ambiguity` with IDs removes duplicate IDs, keeping each ID's first occurrence, before resolving cards, constructing the brief or constructing its output name. It reviews the resulting cards in that order, including done or draft ones. With none it reviews all non-done cards, including drafts, in `all_cards` order. The ambiguity brief lists card IDs, repositories and titles and points to their cards files; it does not embed their full card text or Files lines. The list of repositories inside the brief follows USES order, then sorted unknown names. Contract paths are sorted within each repo. `_contract_files` searches `*.rs` recursively, skipping `.git` and `target` path components. For the parent its search root is `repo_dir(root, PARENT) / 'bin'`; for a child it is `repo_dir(root, repo)`. No other parent-directory search is added.
8. `review` without `--main` needs the card's worktrees. For each repository in name order, include `git diff <merge-base of main and HEAD>` and absolute untracked paths, so committed card changes are included but changes only on newer main are not. Empty diffs are omitted. `--main` instead uses `git diff HEAD -- <paths>` and untracked files limited to those paths in `repo_dir(root, card.repo)`, with no worktree required. Consumer paths in that brief are the card repo then its users, via `repo_dir`. Both forms run the gate before the reviewer, even on gate failure, and return the reviewer's status. A gate captures merged stdout/stderr with replacement decoding, prints `gate exit <code>`, and embeds the last 40 lines or `(no output)`.

### Cargo and gates

9. `PARENT_GATE = "python3 -m unittest discover -s bin -p 'test_*.py'"`. `gate_command(tree, repo)` is `cd {tree} && {PARENT_GATE}` for `skk`, otherwise `CARGO_NET_OFFLINE=true CARGO_TARGET_DIR={tree}/target make -C {tree} check`. `gates(wt_root, card)` returns narrow and full. Narrow is the card repo's gate; full appends each user's gate with ` && `, including users without a Makefile. `main_gate` uses those same repositories via `repo_dir`. The dispatcher does not hide build output: unignored `target/` is an outside-Files change. Editing child `.gitignore` files is not part of T1.
10. `PRIME = ['cargo', 'test', '--locked', '--no-run', '--all-targets']`. `cargo_env(tree)` extends the inherited environment with `CARGO_NET_OFFLINE=true` and `CARGO_TARGET_DIR=str(tree / 'target')`. Just after creating all worktrees, and before printing their paths or starting a worker, run PRIME in each set member whose worktree contains `Cargo.toml`, in set order. Capture stdout and stderr together with text replacement decoding. This is the only pre-worker dependency preparation outside the sandbox. It runs on the freshly created checkout, including with `--no-worker`. It does not run on code written by a worker.
11. Print `prime <repo> exit <code>` for each prime, including a failure. On failure, discard this card's worktrees and branches and stop without starting the worker. The error text is `<repo>: cargo test --locked --no-run --all-targets failed in the worktree (exit <code>); run cargo fetch and make check in <path>, then dispatch again. Last lines:\n<tail>`. `<path>` is the absolute main checkout via `repo_dir`. `<tail>` is the last 20 lines of captured output, or exactly `(no output)` when it is empty. The command name in this message does not change when tests replace PRIME. The message addresses the lead, not implementers bound by `AGENTS.md` rule 4.
12. `card` workers receive `cargo_env` for their own repository, including the parent. Review and ambiguity workers receive `env=None`, thus inherit the caller's environment rather than having cargo values set by the dispatcher. Tests remove `CARGO_NET_OFFLINE` and `CARGO_TARGET_DIR` from the test process environment in setUp and restore them with cleanup. Do not change the production `env=None` rule to make a test deterministic.

### Land is cleanup, not a merge

13. Only after the manager merges the pull request, fetches, and pulls local main, may the lead request `land <ID>`. The manager performs the fetch and pull, not the dispatcher. `land` trusts the manager-supplied local `origin/main` snapshot; it cannot prove its freshness. It never fetches, pushes, merges, resets, rebases, updates `main`, or marks a card done.
14. Require the worktree root. Its discovered repository worktrees must match `repo_set(card.repo)` exactly. Before any cleanup or per-repo validation, report the first missing repo in sorted name order as `<repo>: missing worktree <path>; cleanup requires every repository in the card's set`. If none is missing, report the first unexpected repo in sorted order as `<repo>: unexpected worktree <path>; cleanup only handles the card's repository set`. `<path>` is `<wt_root>/<repo>`. Do not remove any worktree or branch on either failure. After this set check, preflight every expected repository worktree in name order before removing anything. Require its HEAD on `card/<ID>` and a clean status. Resolve its branch tip, require `refs/remotes/origin/main` to exist, require the main checkout on `main`, require local `main` equal to that remote-tracking tip, and require the card tip to be an ancestor of that tip. These checks also apply to dependency-only repositories; a tip already present in remote main needs no new PR. A failed preflight leaves all worktrees and branches intact. Remove the old "main moved" and "unchanged user" rules; a PR merge normally moves main.
15. After preflight, remove each worktree without `--force`, then delete only its `refs/heads/card/<ID>` with the preflight tip as the expected old value using `git update-ref -d`. If a Git cleanup command fails, stop with the usual Git-command error. Earlier successful cleanup is not rolled back; main was never changed. A concurrently changed branch must be retained by the expected-tip check. Print `cleaned <repo> <tip>` only after that repo's cleanup succeeds. Finally remove the now-empty worktree root with `rmdir`, not recursive deletion. If `rmdir` raises OSError with errno ENOTEMPTY or EEXIST, report `worktree <path> is not empty after cleanup; remove its remaining files by hand`. For every other OSError, report `worktree <path> could not be removed: <error>`, where `<error>` is `str(error)`. Both are DispatchError messages, so the CLI prints its `dispatch: ` prefix and returns 2. Do not let an OSError traceback escape. Do not delete unknown remaining files. A partial Git cleanup failure can leave an incomplete repository set; a retry must refuse it under rule 14 rather than silently skipping it. Ask the lead to inspect and finish that cleanup manually.
16. The `land` help text is `verify merged card tips and remove the worktrees`. No fast-forward/rollback CLI or output remains. T1 itself follows the same PR flow, even though its initial worktree is created by hand after dispatch approval. The lead creates `card/T1` at `local/worktrees/T1/skk` from synchronized local `main`, commits its documentation there by explicit path if not already on main, then asks the manager to start its worker. The manager merges, fetches and pulls before any cleanup. Card completion is `git merge-base --is-ancestor <implementation commit> origin/main` after the manager's fetch, not merely passing the worker gate. Record `Status: done` in the next PR.

### Messages and output retained by the port

17. This is the complete application-message catalogue after T1. Values in angle brackets are substituted, not printed literally. `DispatchError` is caught by the CLI, printed to stderr as `dispatch: <message>\n`, and returns 2. Successful non-worker commands return 0; worker commands return the worker status. T2 will separately strengthen failure detection. Argparse's own usage/errors remain generated by argparse, not hand-copied.

| Condition | Exact message or output line |
|---|---|
| unknown ID | `no card <ID> in any TASKS.md` |
| duplicate ID | `card <ID> is in two repositories: <repository names joined with ', '>` |
| no open ambiguity cards | `no cards to review` |
| main checkout off main | `<repo>: the main checkout is not on branch main` |
| done card dispatch | `card <ID> is done` |
| draft card dispatch | `card <ID> is draft; finish and review it before dispatch` |
| dirty cards file | `<repo>: <tasks_path> has uncommitted changes; commit the card first` |
| existing worktree | `worktree <path> exists; land or remove it first` |
| existing branch | `branch card/<ID> already exists in <repository names joined with ', '>` |
| dirty main warning | `warning: <repo> has uncommitted changes in the main checkout; the worktree starts from main` |
| created worktree | `worktree <path>` |
| narrow gate | `narrow gate: <command>` |
| full gate | `full gate: <command>` |
| changes outside card | `changes outside Files:` followed by one line `  <repo>/<path>` per path in repo-name then status order |
| no outside changes | `no changes outside Files` |
| review/land missing worktree | `no worktree <path>` |
| main review has no changes | `no uncommitted changes in <requested paths joined with ', '> of <repo>` |
| worktree off its branch | `<repo>: the worktree is not on card/<ID>; check out card/<ID> and commit there` |
| dirty worktree | `<repo>: worktree has uncommitted changes; commit or discard them first` |
| missing remote main snapshot | `<repo>: origin/main is missing; ask skk-manager to fetch` |
| local main not synchronized | `<repo>: main differs from origin/main; ask skk-manager to pull --ff-only` |
| unmerged card tip | `<repo>: card/<ID> is not merged into origin/main; ask skk-manager to merge its pull request and fetch` |
| failed Git command | `git <arguments joined with spaces>: <stripped stderr>` |
| top-level argparse description | the complete module docstring in rule 21 |
| ambiguity help | `review cards for missing decisions` |
| card help | `make the worktrees and run the implementer` |
| review help | `run the second reviewer on a worktree or the main checkout` |
| land help | `verify merged card tips and remove the worktrees` |
| gate result | `gate exit <code>` |
| prime result/error | the exact lines and error in rule 11 |
| cleanup success/root failure | the exact lines and errors in rule 15 |
| missing/unexpected repository worktree | the exact errors in rule 14 |
| worker output paths and status | `answer <absolute path>`, then `log <absolute path>`, then `exit <code>` |
| harness warning | `the worker did not start (cause:harness). Report it; do not switch the model or the runner.` |

18. Retain these output-file rules: create `root/local/agents`; use UTC format `%Y%m%dT%H%M%SZ`; write `<UTC>-<name>.md` for stdout and `.log` for stderr, UTF-8. Never overwrite either existing file: try `-2`, `-3`, etc. if either name is taken. The verb names are `ambiguity-<IDs joined with '-'>`, `ambiguity-all`, `card-<ID>`, `review-<ID>`, `review-<ID>-main`. The worker command is `<worker> [--read-only] <workdir> <route tokens>`, brief on stdin. Only `card` omits `--read-only`. No fallback or retry is added. Before T2, a nonzero status and `UNKNOWN_MODEL` or `MISSING_CREDENTIAL` anywhere in the log prints the harness warning once; do not enlarge T1 into T2.
19. Outside-Files detection compares each worktree's porcelain status paths with the card's `Files:` patterns via case-sensitive fnmatch, and allows paths only in the card repo. For a rename or copy, consider both source and destination. Handle NUL-delimited paths, non-ASCII paths and literal ` -> ` in names. Never write git state in an actual main checkout while detecting status; use `GIT_OPTIONAL_LOCKS=0` for status subprocesses if needed.

### Complete worker-facing prose

20. Use the following full text for each template. Blank lines separate paragraphs. Braced fields have the existing meanings except the explicit changes below. `opening` and `never` are given here as complete text, so no instruction depends on an aistore sentence or on memory.

`opening`, with the KSTACK path filled in:

```text
Read `/data/softwares/kstack/agents/poteto-agent.md` in full and follow it. kiyama-mode's `SKILL.md` is at `/data/softwares/kstack/skills/kiyama-mode/SKILL.md`. You cannot spawn subagents.
```

`never`, with root filled in:

```text
Never read anything under `/data/references/`, under `{root}/local/agents/`, or under `{root}/local/worktrees/` outside the worktree this brief names (if it names one), or any credentials (API keys, tokens, `.env` files, DSH or provider configuration). Never open, list, or copy the owner's real dictionaries or IME files: `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, `~/.skk-jisyo`, or any CorvusSKK `userdict.txt`. Search only the paths this brief and the card name. Never run `grep -r` or any other recursive search from `{root}`, from a worktree root, from a repository root, or from your home directory.
```

`CARD_BRIEF`; `tasks` is `tasks_path(card.repo)`; `files` is the backtick-quoted Files list joined with `, `:

```text
{opening}

Goal of the owner: build the skk project card by card, each card small and checked, so a reviewer can trust and commit it. You implement exactly one card.

Card {id} ("{title}") of repository `{repo}`. The repository is checked out at `{wt}/{repo}`; the other directories in `{wt}` are the repositories it builds with, all on branch `card/{id}`.

1. Read `{root}/AGENTS.md` in full. Its rules override everything else, including the poteto-agent file.
2. Read `{wt}/{repo}/SPEC.md` in full if it exists (the parent repository has none), the section `## {id}.` of `{wt}/{repo}/{tasks}`, and every document that section names.
3. Implement card {id} exactly: only the files {files}, the names and test names it gives, the values it states. A file the card reserves for the lead is not yours to edit.
4. Write only under `{wt}/{repo}`. Read the other repositories in `{wt}` only where the card or `SPEC.md` points to them.
5. Run `{narrow}` until it exits 0.
6. Do not commit. {never}
7. If the card is ambiguous, a `Needs` card is missing, or the card needs another file or a new dependency, stop and say so in the report instead of guessing.

Final report, plain text, four parts: files changed; the last 20 lines of the gate's output; anything in the card you could not do; open questions.
```

`AMBIGUITY_BRIEF`; `repos` is each absolute `repo_dir` as `` `<path>` (cards in `<tasks_path>`)``, joined with `, ` in rule 7 order. `contracts` is backtick-quoted absolute paths joined with `, `, or `none`. Each `card_lines` line is `- <ID> (<repo>): <title>`:

```text
{opening}

Goal of the owner: a fast implementation model (you) will later implement these cards from the cards and the documents they cite alone. The owner wants them good enough that the implementer never has to guess. Your job now is a read-only review that finds every place you would have to guess.

`{root}/AGENTS.md` holds the rules the implementer follows. It overrides everything else, including the poteto-agent file.

Cards to review:
{card_lines}

Read `{root}/AGENTS.md`, `{root}/PLAN.md`, and for each repository {repos}: its `SPEC.md` if it has one, the sections of its cards file for these cards, its `Makefile` and `Cargo.toml` if it has them, and the contract files {contracts}. Read every document and source file a card names. You may read `{root}/docs/` for context. {never}

Do not edit, create, or delete any file. Do not run git commit. Do not run any command that builds or tests code: you run read-only. Never redirect output to a file or write anywhere, including temporary directories. Read long files in parts of at most 200 lines and continue through the final line. If a tool cuts a requested range, read the omitted range in smaller parts; anything still cut or unread must be listed with its cut count on the UNREAD line.

A finding about ddskk or another engine's behavior requires a primary source, the manual or source code quoted with line numbers. Mark it unverified if you cannot check that source.

Review only the cards above; ignore every other card. For each, imagine implementing it now. Report every point where:
1. the card and its docs do not say what to do (a missing rule, an unstated default, error code, order, or tie-break),
2. two parts of the card or its docs, or the docs and the code, disagree,
3. a named test cannot be written as described (missing fixture, missing hook such as a clock or fake, behavior not observable),
4. the card needs a file, function, or type that is not on its file list or does not exist yet,
5. a cited document, section, or source file does not exist or does not match its description.

Output only this, as plain text:
- One line per finding: <card> | <kind 1-5> | <file:line or section> | <what is missing or conflicting> | <the question the owner must answer>.
- Before the final line, write UNREAD <paths, remaining ranges and tool-cut counts>, or UNREAD none.
- Next write DENIED <every command that failed or was denied, summarized on one line>, or DENIED none.
- If you completed the review, end with TOTAL <n>.
- If you stop without reviewing, end with STOPPED <reason> and write no TOTAL line. Still include UNREAD and DENIED before STOPPED. A baseline mismatch or unread input is not a clean review.
Do not wrap findings, UNREAD, DENIED, TOTAL or STOPPED in backticks or a code block.
Be concrete. Quote the words you mean. Skip style comments. Do not propose code.
```

`REVIEW_BRIEF`; `gate` is the narrow gate, `untracked_lines` is each absolute path prefixed with `- `, or `none`. In the actual template, replace the lines `[gate block]` and `[diff block]` below with fenced code blocks holding `{gate_tail}` and `{diff}` respectively. The gate block opens with three backticks and no language tag; the diff block opens with three backticks followed by `diff`. Each closes with three backticks. They are the only blocks in this specification that stand for a fence, to avoid closing the enclosing example:

```text
{opening}

Goal of the owner: a worker implemented one card of the skk project. You are the second reviewer, read-only, before the lead accepts the diff. Do not edit, create, or delete any file. Do not commit.

`{root}/AGENTS.md` holds the rules the worker had to follow.

Card {id} of repository `{repo}`, worktree `{wt}/{repo}`. Read `{root}/AGENTS.md`, `{wt}/{repo}/SPEC.md` if it exists, the card below, and the files in `{wt}` that the diff touches (any repository there). {never} Do not run any command that builds or tests code: you run read-only. Never redirect output to a file or write anywhere, including temporary directories. Read long files in parts of at most 200 lines and continue through the final line. If a tool cuts a requested range, read the omitted range in smaller parts; anything still cut or unread must be listed with its cut count on the UNREAD line. The dispatcher ran `{gate}` before you started; it exited {gate_code}. The last lines of its output:

[gate block]

Card:

{card_text}

Diff of each repository worktree since it left main (`git diff $(git merge-base main HEAD)`: the card's commits and uncommitted changes), headed by `### <repo>`:

[diff block]

Untracked files (read each one):
{untracked_lines}

Read the whole supplied diff and every permitted file it touches or names through the final line, not only its hunks. Never bypass a prohibited path; list it as unread. A finding about ddskk or another engine's behavior requires the manual or source code as a primary source, quoted with line numbers. Mark a finding unverified if you cannot check that source.

Report every defect: a rule of the card, `SPEC.md`, or `AGENTS.md` that the diff breaks; a named test that is missing or does not assert what the card says; a bug; a changed file that is not on the card's `Files:` line.

Output only this, as plain text:
- One line per finding: <file:line> | <high, medium, or low> | <the defect> | <the evidence: quoted code, rule, or command output>.
- Before the final line, write UNREAD <paths, remaining ranges and tool-cut counts>, or UNREAD none.
- Next write DENIED <every command that failed or was denied, summarized on one line>, or DENIED none.
- If you completed the review, end with TOTAL <n>.
- If you stop without reviewing, end with STOPPED <reason> and write no TOTAL line. Still include UNREAD and DENIED before STOPPED. A baseline mismatch or unread input is not a clean review.
Do not wrap findings, UNREAD, DENIED, TOTAL or STOPPED in backticks or a code block.
Be concrete. Skip style comments. Do not propose code.
```

`MAIN_REVIEW_BRIEF`; `main = repo_dir(root, card.repo)`, `gate = main_gate(root, card)`. `consumers` is backtick-quoted paths for the card repo and its users, joined with `, `. Untracked paths are absolute under `main`. The block substitutions are the same as above:

```text
{opening}

Goal of the owner: before card {id} of the skk project runs, its lead changed files in the main checkout of repository `{repo}`, usually a contract that other repositories consume. You are the second reviewer, read-only, before the lead commits the change. Do not edit, create, or delete any file. Do not commit.

`{root}/AGENTS.md` holds the rules the implementer of the card will follow.

The main checkout is `{main}`. Read `{root}/AGENTS.md`, `{main}/SPEC.md` if it exists, the card below, the files that the change touches, and the code that uses them in {consumers}. {never} Do not run any command that builds or tests code: you run read-only. Never redirect output to a file or write anywhere, including temporary directories. Read long files in parts of at most 200 lines and continue through the final line. If a tool cuts a requested range, read the omitted range in smaller parts; anything still cut or unread must be listed with its cut count on the UNREAD line. The dispatcher ran `{gate}` before you started; it exited {gate_code}. The last lines of its output:

[gate block]

Card:

{card_text}

Uncommitted change in the main checkout (`git diff HEAD`):

[diff block]

Untracked files (read each one):
{untracked_lines}

Read the whole supplied diff and every permitted file it touches or names through the final line, not only its hunks. Never bypass a prohibited path; list it as unread. A finding about ddskk or another engine's behavior requires the manual or source code as a primary source, quoted with line numbers. Mark a finding unverified if you cannot check that source.

Report every defect: a bug or a gap in the change; a rule of the card, `SPEC.md`, or `AGENTS.md` that the change breaks or leaves unstated; a part of the card that the change cannot support; code in {consumers} that the change breaks.

Output only this, as plain text:
- One line per finding: <file:line> | <high, medium, or low> | <the defect> | <the evidence: quoted code, rule, or command output>.
- Before the final line, write UNREAD <paths, remaining ranges and tool-cut counts>, or UNREAD none.
- Next write DENIED <every command that failed or was denied, summarized on one line>, or DENIED none.
- If you completed the review, end with TOTAL <n>.
- If you stop without reviewing, end with STOPPED <reason> and write no TOTAL line. Still include UNREAD and DENIED before STOPPED. A baseline mismatch or unread input is not a clean review.
Do not wrap findings, UNREAD, DENIED, TOTAL or STOPPED in backticks or a code block.
Be concrete. Skip style comments. Do not propose code.
```

21. Replace the entire module docstring, including its first line and the old Go sentence, with this text. This is not a clause-only replacement:

```text
Dispatch one DSH worker on a skk card, card review, or post-merge cleanup.

Run from the project root:

    python3 bin/dispatch.py ambiguity [ID ...]
    python3 bin/dispatch.py card ID [--no-worker]
    python3 bin/dispatch.py review ID [--main PATH ...]
    python3 bin/dispatch.py land ID

Cards are `## <ID>. <title>` sections of each child repository's `TASKS.md`.
The parent repository's cards are in `bin/TASKS.md`, under the name `skk`.
`ambiguity` with IDs reviews those cards whatever their status; without IDs
it reviews every card that is not done. `card` creates the repository set's
worktrees under `local/worktrees/<ID>`, on branch `card/<ID>`, from local main.
Before any worker starts, cargo repositories are primed with
`cargo test --locked --no-run --all-targets`. Cargo runs offline and its target
directory is inside each worktree. `--no-worker` still performs this prime.
`review` shows changes since the merge-base of main and HEAD; `--main` instead
shows selected uncommitted changes in the main checkout.
`land` verifies card tips against the manager-fetched `origin/main` snapshot
and removes only merged card worktrees and branches. The manager must merge
the pull requests, fetch, and pull local main first. No verb accesses GitHub,
merges locally, or advances main. Cleanup cannot prove snapshot freshness.
Only `card` starts a writable worker. `review` runs the gate before starting
its read-only worker and includes its exit code and last lines in the brief.
Worker answers and logs go to `local/agents/<UTC>-<name>.md` and `.log`;
collisions gain `-2`, `-3`, etc. Worker verbs print the paths and worker status.
```

### Tests

22. Keep synthetic fixtures in a TemporaryDirectory. Rename the fixture root to `base / 'skk'`, equal to PARENT. Initialize it on main. Commit and track `.gitignore`, `AGENTS.md` and `bin/TASKS.md`. The `.gitignore` contains only `local/` and one `/<repo>/` line for each child; it does not ignore `AGENTS.md` or `bin/TASKS.md`. The parent fixture has no SPEC or Makefile. Its T1 section is titled `Port`, status open, Files `bin/dispatch.py`, `bin/test_dispatch.py` only. Do not copy this real card or real tests into it. Child fixture names are `llmgw`, `rag`, `eval`, `learn`, `adopt`, `server`, `web`. Each has SPEC text `# spec\n` and Makefile text `check:\n\t@true\n`, with no go.mod or Cargo.toml by default. The parent's AGENTS text is `# Rules for implementation agents\n`. Child cards are specified in the fixture-text table below, not inherited by reference. Rename GO_REPOS to TEST_REPOS and remove GO_WORK and WT_GO_WORK. TEST_USES is `{'llmgw': [], 'rag': ['llmgw'], 'eval': ['rag', 'llmgw'], 'learn': ['rag', 'llmgw'], 'adopt': ['rag', 'llmgw'], 'server': ['llmgw', 'rag', 'eval', 'learn', 'adopt'], 'web': ['rag', 'llmgw', 'learn', 'adopt']}`. Patch USES for fixture tests, except the real-graph rows below. Store the real graph before patching. The fake worker's default stdout is `UNREAD none\nDENIED none\nTOTAL 0\n` and default stderr is `reasoning text\n`; tests needing another answer or log pass it explicitly. It records its arguments, brief, run count, and `${CARGO_NET_OFFLINE:-}|${CARGO_TARGET_DIR:-}` in `cargo.txt`; never create or assert `gowork.txt`, including in the renamed `test_review_main_runs_the_cargo_gate`.
The child cards file starts with `# <repo> tasks` and a blank line. Each row below adds a heading `## <ID>. <title>`, a blank line, `Status: <status>`, a blank line, then the Needs line if the table supplies one, followed by a blank line. Next is `Files: ` and the listed patterns, each backtick-quoted and joined with `, `, followed by a period, a blank line, and the body sentence. End each body with two newlines. `adopt` and `server` have only `# adopt tasks\n` and `# server tasks\n` respectively. This grammar defines the fixture strings, not extra cards in this real TASKS.md.

| Repo | ID | Title | Status | Needs line | Files patterns | Body sentence |
|---|---|---|---|---|---|---|
| llmgw | L1 | Fake server | done | `Needs: nothing.` | `fake/fake.go`, `fake/fake_test.go` | Build package `fake`. |
| llmgw | L2 | Config and client skeleton | open | `Needs: L1.` | `config.go`, `client.go` | Load the config. |
| rag | R1 | Ingest | open | omitted | `ingest.go`, `testdata/docs/*.txt` | Ingest documents. |
| eval | E1 | Build queries | open | omitted | `impl.go`, `impl_test.go`, `testdata/docs/*.txt` | Build queries. |
| learn | N1 | Lessons | open | omitted | `lesson.go` | Write the lessons. |
| web | W1 | Shell | open | omitted | `index.html` | Build the shell. |

23. For cleanup tests, prepare synthetic origin snapshots using temporary local bare repositories, never GitHub. A fixture helper may simulate the manager pushing a card, merging it with a merge commit in another temporary checkout, fetching origin and pulling fixture main. Dependency-only repositories have an origin snapshot containing their original tips. The helper is fixture setup, not the system under test. Snapshot refs, worktree registrations and branch tips before each refused cleanup and assert they remain unchanged. Success must not change main or origin/main. A fake Git executable may inject a cleanup failure or late branch update at the process boundary; it must delegate other commands to real Git and use only temporary fixture paths.
24. Replace direct helper tests with the following CLI tests. Delete `test_card_writes_go_work_with_the_version_of_the_parent` and every old `test_land*` function; the cleanup rows below replace them. Retain other existing test names only for their single behavior, rewrite their setup/asserts to the rules above, and remove expected values computed by dispatcher helpers. Replace private-helper fault injection with external executable fault injection. The table lists the required coverage, including renamed/split cases.

| Test | Setup and observable assertions |
|---|---|
| `test_card_parsing` | Create E1 worktrees with `card E1 --no-worker`, then `review E1`; fake reviewer's brief contains title `Build queries`, the full E1 card section and its literal Files patterns, without the W1 section. No change to the ambiguity brief's card-list-only format. |
| `test_all_cards_are_in_repository_name_order` | `ambiguity` without IDs; card lines are E1, N1, L2, R1, T1, W1 in that order. |
| `test_unknown_card` | `card Z9 --no-worker`; exit 2, `dispatch: no card Z9 in any TASKS.md\n`. |
| `test_duplicate_card` | Add E1 to rag; `ambiguity E1` exits 2 with `dispatch: card E1 is in two repositories: eval, rag\n`. |
| `test_card_without_worker` | `card E1 --no-worker`; set directories are adopt, eval, learn, llmgw, rag, server, all on card/E1; no worker run. |
| `test_card_does_not_write_go_workspace` | `card E1 --no-worker`; no go.work or go.work.sum anywhere in its worktree root, and no GOWORK in printed gates. |
| `test_help_describes_post_merge_cleanup` | Root `--help` returns argparse status 0 and contains the complete rule 21 docstring, with no aistore or local fast-forward claim; `land --help` describes only merged-tip verification and cleanup. |
| `test_child_gate_commands` | `card E1 --no-worker`; narrow is `CARGO_NET_OFFLINE=true CARGO_TARGET_DIR={wt}/eval/target make -C {wt}/eval check`; full appends the same form for server with ` && `. Execute the narrow command, exit 0. |
| `test_card_in_learn_brings_web` | `card N1 --no-worker`; set includes web, full gates are learn, server, web in that order. |
| `test_real_jisyo_repository_set` | Use real USES, synthetic jisyo/conformance repos with cards J1/C1, no old children; `card J1 --no-worker`; worktrees jisyo and conformance, full gates jisyo then conformance. |
| `test_real_conformance_repository_set` | Same graph; `card C1 --no-worker`; both worktrees, narrow equals full conformance gate. |
| `test_card_refuses_a_done_card` | `card L1 --no-worker` exits 2 with `dispatch: card L1 is done\n`, creates nothing. |
| `test_card_refuses_a_draft_card` | Commit parent fixture T1 with Status: draft; `card T1 --no-worker` exits 2 with `dispatch: card T1 is draft; finish and review it before dispatch\n`; no branch, worktree or worker. |
| `test_done_card_takes_precedence_over_draft` | Commit parent T1 with both Status: done and Status: draft; card T1 --no-worker exits 2 with `dispatch: card T1 is done\n`, creates nothing. |
| `test_card_refuses_an_existing_worktree` | Existing empty wt root; exit 2 with rule 17 error; root stays empty, no worker. |
| `test_card_refuses_an_existing_branch` | Existing card/E1 in rag; exit 2, names rag, no new worktree or branch. |
| `test_card_refuses_an_uncommitted_tasks_file` | Dirty eval/TASKS.md; exit 2 with exact rule 17 error, no new worktree or branch. |
| `test_card_refuses_when_main_checkout_is_not_on_main` | Rename eval main to trunk; exit 2 with exact rule 17 error, creates nothing. |
| `test_card_cleanup_keeps_what_it_did_not_create` | External fake Git makes branch precheck appear absent but worktree add fail on existing rag branch; branch preserved, only newly created worktrees/branches discarded. |
| `test_card_cleans_up_after_a_failed_worktree_add` | rag main renamed to trunk; creation fails and all this invocation's worktrees/branches disappear, original refs untouched. |
| `test_gates_include_users_without_a_makefile` | Remove server Makefile; `card E1 --no-worker` still prints server's gate in full gate. |
| `test_card_warns_about_a_dirty_main_checkout` | Dirty llmgw; dispatch succeeds, exact warning in rule 17, main file content unchanged. |
| `test_card_with_worker` | Fake worker exits 3 with `implemented E1` and `reasoning`; CLI returns 3, saves exact output and log, prints their paths and exit 3. |
| `test_card_worker_route` | `card E1`; argv has eval workdir, then literal DeepSeek route from rule 2, no read-only flag. |
| `test_card_worker_cargo_environment` | `card E1`; cargo.txt stripped is `true|{wt}/eval/target`. |
| `test_card_reports_no_changes_outside_files` | Fake worker writes eval/impl.go and eval/testdata/docs/note.txt; CLI prints `no changes outside Files`. |
| `test_card_reports_an_outside_file` | Fake worker writes eval/extra.go and allowed impl.go; only extra.go is listed outside Files. |
| `test_off_list_reports_both_sides_of_a_rename` | Before fake worker returns, its script runs git mv in temporary worktree for SPEC.md to impl_test.go and TASKS.md to other.go; CLI lists eval/SPEC.md, eval/TASKS.md, eval/other.go, not allowed impl_test.go. |
| `test_off_list_reports_a_name_with_an_arrow` | Fake worker writes eval/impl.go -> x.go; CLI lists the full literal path. |
| `test_off_list_reports_a_non_ascii_path` | Fake worker writes eval/メモ.txt with core.quotepath true; CLI lists that path, not escaped bytes. |
| `test_harness_failure_is_reported_once` | Fake worker exits 2 with `error: UNKNOWN_MODEL: nope`; CLI prints the literal harness warning once. |
| `test_harness_line_needs_a_nonzero_exit` | Worker exits 0 with bare `MISSING_CREDENTIAL`; CLI exit 0, no harness warning. This is not a colon-form DSH failure; T2 preserves this test. |
| `test_run_worker_never_overwrites_output` | Fixed clock 20260102T030405Z; invoke `ambiguity E1` twice; original and -2 answer/log pairs retain exact fake output. |
| `test_run_worker_skips_a_taken_name` | Pre-create only the fixed-time answer; invoke ambiguity E1; original preserved, -2 pair written. |
| `test_ambiguity_reviews_the_cards_that_are_not_done` | No IDs; card-list lines for E1,N1,L2,R1,T1,W1 included, L1 excluded. Do not assert embedded card sections or Files lines. |
| `test_ambiguity_with_ids_reviews_a_done_card` | `ambiguity L1`; includes only L1 and the exact card line `- L1 (llmgw): Fake server`. |
| `test_ambiguity_includes_a_draft_without_ids` | Commit parent T1 with Status: draft; `ambiguity` lists T1, showing all_cards returned it as non-done. |
| `test_ambiguity_reviews_an_explicit_draft` | Commit parent T1 with Status: draft; `ambiguity T1` lists it once and exits 0. |
| `test_ambiguity_deduplicates_requested_ids` | `ambiguity E1 R1 E1`; card-list lines E1 then R1 exactly once each; answer/log basenames end in ambiguity-E1-R1, never ambiguity-E1-R1-E1. |
| `test_ambiguity_without_cards` | Mark all child and parent fixture cards done; exit 2 with `dispatch: no cards to review\n`, no worker. |
| `test_ambiguity_worker_route` | `ambiguity E1`; read-only flag, root workdir, literal DeepSeek route. |
| `test_ambiguity_inherits_environment` | `ambiguity E1` in cleared cargo environment; cargo.txt stripped is `|`. |
| `test_ambiguity_lists_contract_files` | eval/contract.rs and eval/target/debug/gen.rs start with contract marker; brief includes only contract.rs. |
| `test_ambiguity_does_not_read_go_contracts` | eval/contract.go has marker; `ambiguity E1` does not list it. |
| `test_ambiguity_lists_contract_files_of_the_parent` | Commit bin/contract.rs and docs/other.rs with marker; `ambiguity T1` includes bin contract only. |
| `test_ambiguity_output_format_is_plain` | ambiguity brief's complete Output paragraph matches rule 20's literal plain lines, with no backticks around finding/TOTAL formats. |
| `test_read_only_briefs_forbid_all_writes` | Via ambiguity E1, review E1 and main review of a rag change, each received brief explicitly forbids output redirection and every write, including temporary directories. |
| `test_read_only_briefs_require_chunked_reads` | Same three command forms; each brief requires parts of at most 200 lines and continuation to the final line. |
| `test_read_only_briefs_report_unread_inputs` | Same forms; each requires UNREAD with paths, remaining ranges and tool-cut counts, or UNREAD none. |
| `test_read_only_briefs_report_failed_commands` | Same forms; each requires a DENIED line listing every failed or denied command, or DENIED none, before TOTAL or STOPPED. |
| `test_read_only_briefs_stop_without_total` | Same forms; each requires STOPPED with a reason and no TOTAL if review stops without reviewing. |
| `test_review` | Worktree committed impl.go change and untracked notes.txt; review brief contains card, committed diff and absolute untracked path, with merge-base description from rule 20. |
| `test_review_worker_route` | `review E1`; read-only flag, eval workdir and literal Astra route from rule 2, no Gemini or lead-model substitution. |
| `test_review_inherits_environment` | `review E1`; cargo.txt stripped is `|`. |
| `test_review_lists_untracked_files_as_absolute_paths` | Untracked eval/notes.txt and learn/other.txt; review lists both absolute paths. |
| `test_review_lists_a_non_ascii_untracked_file` | Untracked eval/メモ.txt; review lists absolute unescaped path. |
| `test_review_runs_the_gate_before_the_reviewer_even_when_it_fails` | eval Makefile prints gate-marker and exits 3; make returns 2, fake reviewer still runs; brief says exited 2 and contains marker, CLI reports gate exit 2 and returns reviewer 0. This is gate-failure delivery, not a mock call-order assert. |
| `test_review_shows_every_changed_repository` | Committed eval and rag changes, untracked learn note; brief's diff sections eval then rag, learn note only in untracked paths. |
| `test_review_ignores_commits_main_gained_after_the_dispatch` | Change eval worktree, then commit separate main-only files in rag/eval; review contains only worktree delta. |
| `test_review_main` | Dirty rag contract.go, unrelated dirty other.go, requested untracked new.txt; `--main contract.go new.txt` includes only requested diff/untracked, names root/rag. |
| `test_review_main_names_the_users` | Review rag main change; consumers are rag, eval, learn, adopt, server, web with absolute paths in that order. |
| `test_review_main_runs_the_cargo_gate` | Rename old test_review_main_pins_gowork; rag main contract change; brief has rule 9 gates for rag and server; no gowork.txt assert. |
| `test_review_main_inherits_environment` | `review R1 --main contract.go`; cargo.txt stripped is `|`. |
| `test_review_main_without_changes` | No change in requested SPEC.md; exit 2 with exact rule 17 message, no worker. |
| `test_review_without_main_still_needs_a_worktree` | No worktree; review E1 exits 2 with exact missing-worktree message. |
| `test_parent_cards_are_read_from_bin` | Add notrepo/TASKS.md without .git, local/TASKS.md with local/.git, bin/TASKS.md already exists; ambiguity brief has T1 as repo skk, no notrepo/local/bin cards. |
| `test_card_in_the_parent` | `card T1 --no-worker`; only wt/skk on card/T1, common git dir root/.git; narrow and full are `cd {wt}/skk && python3 -m unittest discover -s bin -p 'test_*.py'`. |
| `test_card_in_the_parent_refuses_an_uncommitted_tasks_file` | Dirty bin/TASKS.md; exit 2, `dispatch: skk: bin/TASKS.md has uncommitted changes; commit the card first\n`, creates nothing. |
| `test_card_brief_for_the_parent` | Fake worker gets wt/skk/bin/TASKS.md, optional SPEC text, parent gate, lead-only file exclusion and complete CARD_BRIEF from rule 20; no aistore/GOCACHE. |
| `test_card_with_worker_in_the_parent_lists_files_relative_to_the_parent` | Fake worker writes bin/dispatch.py and bin/other.py; outside list contains only skk/bin/other.py. |
| `test_review_main_in_the_parent` | Fixture bin contains only TASKS.md and new.py; `review T1 --main bin/new.py`; absolute root/bin/new.py, main checkout root, parent gate; no root/skk; do not assert gate status. |
| `test_card_dictionary_fence` | `card E1`; received brief includes the exact dictionary sentence in rule 20. |
| `test_ambiguity_dictionary_fence` | `ambiguity E1`; same dictionary sentence. |
| `test_review_dictionary_fence` | `review E1`; same dictionary sentence. |
| `test_main_review_dictionary_fence` | Main review of rag change; same dictionary sentence. |
| `test_briefs_share_the_search_rule_and_name_the_worktree` | Via separate card and review invocations, check the exact search restriction and named current worktree from rule 20; this row no longer tests the dictionary guard. |
| `test_card_uses_locked_prime` | Commit eval Cargo.toml; supply fake cargo on PATH, without replacing PRIME; `card E1 --no-worker`; recorded cargo arguments are exactly `test`, `--locked`, `--no-run`, `--all-targets`. |
| `test_card_primes_cargo` | Commit synthetic Cargo.toml in eval; replace PRIME with a fake executable that records cwd and cargo vars; exactly `{wt}/eval|true|{wt}/eval/target`, one prime line `prime eval exit 0`; worker observes prime record already exists. |
| `test_card_primes_with_no_worker` | Same cargo fixture; `card E1 --no-worker` still records one prime, zero worker runs. |
| `test_card_does_not_prime_without_a_manifest` | Default fixture; `card E1` records no prime even with a supplied PRIME executable. |
| `test_card_stops_when_the_prime_fails` | PRIME prints prime-marker and exits 4; CLI exits 2 with rule 11 error, includes marker; no worker or card worktrees/branches. |
| `test_failed_prime_tail_is_twenty_lines` | PRIME emits 25 numbered synthetic lines and exits 4; error contains only lines 6 through 25 after Last lines, not lines 1 through 5. |
| `test_failed_prime_without_output` | PRIME exits 4 silently; error ends `Last lines:\n(no output)\n`. |
| `test_land_after_a_merge_commit` | Synthetic manager merges E1 eval with merge commit, fetches and pulls all fixtures; `land E1` removes registered worktrees, branches and empty wt root, prints cleaned lines with preflight tips; main/origin refs unchanged. |
| `test_land_in_the_parent` | Same PR simulation for T1 parent with committed bin/new.py; cleanup succeeds via root rather than root/skk; main/origin unchanged. |
| `test_land_refuses_an_unmerged_tip` | Origin/main lacks E1 eval commit and main equals origin; exit 2 with exact unmerged-tip error; no cleanup anywhere. |
| `test_land_refuses_missing_origin_main` | Otherwise merged fixture, delete eval origin/main; exit 2 with missing-snapshot error; no cleanup. |
| `test_land_refuses_unsynchronized_main` | Merged eval remote snapshot, local main still at prior tip; exact sync error, no cleanup. |
| `test_land_refuses_main_checkout_off_main` | Merged snapshots; main checkout switched to other branch; exact off-main error, no cleanup. |
| `test_land_refuses_a_dirty_worktree` | Otherwise merged snapshots; rag worktree has dirty.txt; exact dirty error; all registrations and refs preserved. |
| `test_land_stops_on_a_detached_worktree` | Otherwise merged snapshots; detach rag worktree; exact branch error; all registrations and refs preserved. |
| `test_land_needs_a_worktree` | Missing root; exit 2 with rule 17 error. |
| `test_land_refuses_a_missing_repository_worktree` | Eligible E1 fixture, manually remove only rag's registered worktree but retain its card/E1 branch; land exits 2 with rule 14's missing-worktree error; that branch and every remaining worktree/ref are unchanged. |
| `test_land_refuses_an_unexpected_repository_worktree` | Eligible E1 fixture; add a separate web worktree on card/E1 under its root. web is outside E1's set. land exits 2 with rule 14's unexpected-worktree error; no worktree or branch is removed. |
| `test_land_preflights_all_repositories` | Earlier adopt repo eligible, later eval tip unmerged; neither worktree removed; main unchanged. |
| `test_land_keeps_main_checkout_changes` | Eligible cleanup, synthetic main has staged SPEC edit and ignored file; cleanup preserves both bytes and staged diff as well as main ref. |
| `test_land_keeps_a_branch_that_gained_commits` | External fake Git updates learn card branch after worktree removal but before expected-tip delete; cleanup exits 2, preserves new tip; main unchanged. No mock of dispatch.git. |
| `test_land_reports_root_removal_io_error` | Eligible cleanup; inject `PermissionError('synthetic-rmdir-denial')` at Path.rmdir while invoking land. CLI exits 2 with `dispatch: worktree {wt} could not be removed: synthetic-rmdir-denial\n`, not a traceback; main refs unchanged. |
| `test_land_keeps_unknown_files_under_its_root` | Eligible cleanup, extra wt/keep.txt; worktrees cleaned but root removal fails with exact rule 15 error; keep.txt unchanged. |

Must fail without: draft-card dispatch rejection → `test_card_refuses_a_draft_card`.
Must fail without: read-only no-write instruction → `test_read_only_briefs_forbid_all_writes`.
Must fail without: repository-set completeness check → `test_land_refuses_a_missing_repository_worktree`.
Must fail without: unexpected repository rejection → `test_land_refuses_an_unexpected_repository_worktree`.
Must fail without: failed-prime stop → `test_card_stops_when_the_prime_fails`.
Must fail without: dictionary sentence → `test_card_dictionary_fence`, `test_ambiguity_dictionary_fence`, `test_review_dictionary_fence`, `test_main_review_dictionary_fence`.
Must fail without: merged-tip ancestry check → `test_land_refuses_an_unmerged_tip`.
Must fail without: remote-snapshot existence check → `test_land_refuses_missing_origin_main`.
Must fail without: local-main synchronization check → `test_land_refuses_unsynchronized_main`.
Must fail without: worktree cleanliness check → `test_land_refuses_a_dirty_worktree`.
Must fail without: worktree branch check → `test_land_stops_on_a_detached_worktree`.
Must fail without: complete preflight before cleanup → `test_land_preflights_all_repositories`.
Must fail without: expected-tip branch deletion → `test_land_keeps_a_branch_that_gained_commits`.
Must fail without: nonrecursive root removal → `test_land_keeps_unknown_files_under_its_root`.

Done: the parent gate exits 0 in the worker's worktree. The lead then verifies each named guard and the full diff, obtains Astra security review and manager review under the live project rules, and reports the implementation commit to the manager for its PR. T1 is not done until the commit is an ancestor of manager-fetched origin/main. Never merge or advance main locally.

## T2. Summarize ambiguity and reject DSH failures

Status: open

Needs: T1 merged into origin/main.

Spec: this card, the introduction "Project rules for all three cards", and T1's rules, prose templates and test-fixture description in `bin/TASKS.md`; `AGENTS.md`; `CLAUDE.md`, sections "GitHub" and "Card flow"; `/data/softwares/kstack/skills/card-flow/SKILL.md`, sections "Project adapter", "2. Review the cards for ambiguity" and "4. Review the diff"; `/data/softwares/kstack/skills/kiyama-mode/scripts/run-worker-project.mjs`, the stderr projector.

Files: `bin/dispatch.py`, `bin/test_dispatch.py`, `bin/TASKS.md`.

The worker does not edit `bin/TASKS.md`. T2 changes only worker-result classification and ambiguity summary output. All CLI forms, routes, complete brief prose, repository discovery, cargo gates/prime, cleanup-only land, output filenames and messages are specified by T1 above, not by an aistore source. Do not add another merge path or worker fallback.

### Worker results

1. Rename the current body of `run_worker` to `_run`, keeping its parameters and returning `(code, answer, log)`. The public `run_worker` keeps its signature and returns the status only. Test via the CLI, not either helper. Keep the output paths and exact lines `answer <path>`, `log <path>`, `exit <code>`, and the exact harness warning `the worker did not start (cause:harness). Report it; do not switch the model or the runner.`
2. Before printing `exit`, read the log as UTF-8 with replacement decoding. A DSH failure is a line matching `^dsh: ([A-Z][A-Z0-9_]*):`. Collect group 1 once per distinct code in first-appearance order. If any occur, print `dsh failure <codes joined with ', '>`. Change status 0 to 1, preserve a nonzero status, and use that resulting status for printing, classification and return. Never print the remainder of a DSH failure line, since it may contain provider text. Answer and log files remain unchanged. This applies to every worker verb, not just card.
2b. For a read-only review or ambiguity run, also read the answer as UTF-8 with replacement decoding. Its last nonempty stripped line must match `TOTAL <nonnegative decimal integer>` or `STOPPED <nonempty reason>`. If it does not, print `incomplete review answer: missing TOTAL or STOPPED` before the exit line. Change status 0 to 4; preserve any already nonzero status, including a DSH failure status from rule 2 or runner exit 4. This marker check does not apply to card implementers. A STOPPED report is a completed report of a stopped review, not review approval; it must have no TOTAL. The dispatcher does not infer the stop rule or a clean review from its process status.
3. On a nonzero resulting status, print the harness warning once if either holds: no line begins `dsh: tool:` and no line begins `dsh: reasoning:`; or a line starting with none of `dsh: tool`, `dsh: reasoning:`, and two spaces contains `UNKNOWN_MODEL` or `MISSING_CREDENTIAL`. Otherwise do not print it. A quoted marker in tool target/reasoning text is not evidence of failure. Projector lines start lowercase after `dsh: `; they do not match rule 2. Bare `MISSING_CREDENTIAL` without the DSH colon form still does not turn an exit 0 into failure.

### Ambiguity summary

4. `summarize_ambiguity(text, card_ids)` returns newline-free strings in the order below. A finding is a line split by `|` into at least five parts, with stripped part 1 in reviewed IDs and stripped part 2 matching `^(?:kind\s*)?([1-5])$` ignoring case. Other nonempty lines count as other, except TOTAL lines. The reported total is the number in the last stripped line matching `^TOTAL (\d+)$`; earlier TOTAL lines are not other lines. A finding for an unreviewed ID is other. Blank lines are ignored. No backticks or code fences are stripped; the worker's required output is plain lines.
5. Reviewed IDs are T1 rule 7's first-occurrence-normalized list, so a repeated CLI ID has one summary, not one per occurrence. Return one `summary <ID> kind1=<n> kind2=<n> kind3=<n> kind4=<n> kind5=<n> kind245=<yes|no>` per reviewed ID in brief order, then `summary other <n>`, then `summary total counted=<number of findings> reported=<last total or 'missing'>`. kind245 is yes if a finding has kind 2, 4 or 5. The summary never decides the stop rule; the lead closes or answers findings and decides it.
6. `_ambiguity` calls `_run`, reads its answer file with UTF-8 replacement decoding, and prints the summary lines after the resulting `exit` line, even on failure. Return that resulting status. IDs without explicit CLI arguments are all non-done cards, including drafts, in all_cards order. UNREAD, DENIED and STOPPED lines are other lines, not findings or TOTAL lines; a STOPPED report therefore has reported=missing. The lead checks these lines before accepting a review. Summary does not run for card or review.

### Tests

Use the T1 CLI fixture and fake-worker records. No direct tests of `_harness_failure`, `dsh_failures`, `_run`, `summarize_ambiguity` or internal print order. Output order on the CLI is an observable interface, not internal call order. Required rows each have their own test function. Existing T1 tests remain and must pass.

| Test | Synthetic CLI input and observable assertions |
|---|---|
| `test_harness_line_ignores_a_marker_in_a_tool_line` | Worker exits 1, stderr `dsh: tool: bash grep UNKNOWN_MODEL x`; card E1 returns 1, no warning. |
| `test_harness_line_ignores_a_marker_in_a_tool_error` | Exit 1, stderr `dsh: tool: read a.rs` then `dsh: tool-error: bash exit-1 grep MISSING_CREDENTIAL x`; no warning. |
| `test_harness_line_ignores_a_marker_in_reasoning` | Exit 1, stderr `dsh: reasoning:` and `  UNKNOWN_MODEL`; no warning. |
| `test_harness_line_for_a_marker_outside_tool_lines` | Exit 2, stderr `dsh: tool: read a.rs` then `dsh: UNKNOWN_MODEL: no such model`; returns 2, warning once. |
| `test_harness_line_when_no_tool_ran` | Exit 3, stderr `dsh: session: s` only; returns 3, warning once. |
| `test_ambiguity_prints_a_summary_per_card` | stdout E1 kinds 1 and 4, R1 kind 3, TOTAL 3; ambiguity E1 R1 L2; exact E1 counts 1,0,0,1,0/yes, R1 counts 0,0,1,0,0/no, L2 all zero/no, in requested order; other 0, counted 3 reported 3. |
| `test_ambiguity_summary_deduplicates_requested_ids` | Worker stdout `E1 | 1 | a | b | c`, TOTAL 1; ambiguity E1 R1 E1; one E1 summary kind1=1, one zero R1 summary, in that order; counted 1, reported 1. |
| `test_ambiguity_summary_counts_footer_lines_as_other` | Worker stdout `UNREAD none`, `DENIED none`, `TOTAL 0`; ambiguity E1; other 2, counted 0 reported 0. |
| `test_ambiguity_stopped_report_has_no_total` | stdout `UNREAD none`, `DENIED none`, `STOPPED synthetic baseline mismatch`; ambiguity E1; other 3, counted 0 reported missing; no fabricated TOTAL 0. |
| `test_ambiguity_accepts_kind_prefix` | stdout `E1 | KiNd 3 | a | b | c`, TOTAL 1; E1 kind3=1, rest zero, kind245=no. |
| `test_ambiguity_kind245_for_kind2` | stdout E1 kind 2 only; E1 kind245=yes. |
| `test_ambiguity_kind245_for_kind5` | stdout E1 kind 5 only; E1 kind245=yes. |
| `test_ambiguity_counts_unreviewed_ids_as_other` | stdout `Z9 | 2 | a | b | c`, TOTAL 1; ambiguity E1; other 1, counted 0 reported 1. |
| `test_ambiguity_counts_a_note_as_other` | stdout `a note`, TOTAL 0; other 1, counted 0 reported 0. |
| `test_ambiguity_ignores_blank_lines` | stdout blank lines and TOTAL 0; other 0. |
| `test_ambiguity_rejects_a_short_finding` | stdout `E1 | 2 | a | b`, TOTAL 1; counted 0, other 1. |
| `test_ambiguity_does_not_strip_backticks` | stdout a backtick-wrapped E1 finding, TOTAL 1; counted 0, other 1. |
| `test_ambiguity_uses_the_last_total` | stdout TOTAL 2 then TOTAL 4; counted 0, reported 4, other 0. |
| `test_ambiguity_summary_without_total` | stdout `E1 | 2 | a | b | c`; E1 kind2=1, kind245=yes, counted 1 reported missing; marker validation makes its exit 4. |
| `test_ambiguity_summary_after_a_failed_worker` | stdout TOTAL 0, worker exit 5; summary follows exit 5 and CLI returns 5. |
| `test_ambiguity_summary_without_ids_lists_open_cards` | No CLI IDs, stdout TOTAL 0; summary IDs E1,N1,L2,R1,T1,W1, not L1. |
| `test_ambiguity_rejects_an_incomplete_exit_zero_answer` | Worker exit 0, stderr `dsh: tool: read a.rs`, stdout partial without marker; ambiguity E1 returns 4, prints incomplete-answer message then exit 4; summary reported=missing. |
| `test_review_rejects_an_incomplete_exit_zero_answer` | Same fake output, E1 worktree exists; review E1 returns 4 with incomplete-answer message. |
| `test_review_preserves_runner_exit_four` | Worker exit 4, stdout partial without marker; review E1 returns 4, never 0. |
| `test_card_does_not_require_a_review_marker` | Worker exit 0, stdout implementation report without marker; card E1 returns 0. |
| `test_dsh_failure_fails_an_exit_zero_run` | Worker exit 0, stdout partial, stderr tool read then `dsh: PI_AI_ERROR: Internal Server Error`; card exits 1; dsh failure PI_AI_ERROR then exit 1; no harness warning. |
| `test_dsh_failure_hides_the_provider_message` | Same failure, stdout partial; CLI stdout lacks Internal Server Error; saved answer is partial plus newline, log retains full supplied stderr. |
| `test_dsh_failure_ignores_projector_lines` | Exit 0; stderr lines `dsh: session: s`, `dsh: tool: bash echo dsh: X_Y: z`, `dsh: tool-error: bash exit-1 x`, `dsh: tool-unchecked: read a`, `dsh: unparsed: 10 bytes`, `dsh: error: lower case`, `dsh: reasoning:`, `  dsh: FAKE_CODE: quoted`; no dsh failure line, exit 0. |
| `test_dsh_failure_keeps_a_nonzero_exit` | Exit 7, stderr tool read then `dsh: OTHER_CODE: x`; returns 7, prints OTHER_CODE. |
| `test_dsh_failure_deduplicates_codes` | Exit 7, stderr tool read then OTHER_CODE twice and PI_AI_ERROR; one failure line `dsh failure OTHER_CODE, PI_AI_ERROR`. |
| `test_dsh_failure_fails_an_ambiguity_run` | Exit 0, stdout TOTAL 0, stderr tool read then PI_AI_ERROR; ambiguity E1 returns 1, summary still printed after exit 1. |
| `test_dsh_failure_fails_a_review_run` | Create E1 worktree, review fake worker exit 0 and stderr tool read then PI_AI_ERROR; review returns 1. |

Must fail without: incomplete read-only answer rejection in rule 2b → `test_ambiguity_rejects_an_incomplete_exit_zero_answer`, `test_review_rejects_an_incomplete_exit_zero_answer`.
Must fail without: tool-target exclusion in rule 3 → `test_harness_line_ignores_a_marker_in_a_tool_line`, `test_harness_line_ignores_a_marker_in_a_tool_error`.
Must fail without: reasoning exclusion in rule 3 → `test_harness_line_ignores_a_marker_in_reasoning`.
Must fail without: no-tool/no-reasoning rule → `test_harness_line_when_no_tool_ran`.
Must fail without: changing DSH-failed exit 0 to 1 → `test_dsh_failure_fails_an_exit_zero_run`, `test_dsh_failure_fails_an_ambiguity_run`, `test_dsh_failure_fails_a_review_run`.
Must fail without: printing only failure codes → `test_dsh_failure_hides_the_provider_message`.

Done: parent gate exits 0, the lead checks each guard and obtains the required reviews, and the manager merges the implementation PR. Completion requires the implementation commit to be an ancestor of origin/main after the manager's fetch. The worker does not commit or change Status.

## T3. Run the parent gate on pull requests

Status: open

Needs: no implementation card. T3 merges before T1 so T1's PR has CI. The manager supplied the action pins and Python availability evidence; all values the worker needs are written below. No worker reads the manager's private evidence file.

Spec: this card and the introduction "Project rules for all three cards" in `bin/TASKS.md`; `AGENTS.md`; `CLAUDE.md`, section "GitHub". The manager's turn identifies parent issue 4 as the CI request and issue 1 as the dispatcher step. No worker contacts GitHub.

Files: `.github/workflows/check.yml`, `bin/test_ci_workflow.py`, `bin/TASKS.md`.

The worker changes only the workflow and its tests. `bin/TASKS.md` is lead-only. The workflow file is an explicit exception to the brief's earlier bin-only implementation scope, requested by the manager for parent CI. No existing workflow file was found under the parent's `.github/workflows/`.

### Workflow contract

1. The workflow's name is `check`. Its event is `pull_request` with no branch, path or activity-type filter, and no `pull_request_target` trigger. It runs the parent gate on every pull request, not the Rust child gates. Workflow token permissions are exactly contents read. It does not use secrets, upload artifacts, publish, or push.
2. One job named `check` runs on `ubuntu-latest`. It checks out the PR's tested revision with credentials persistence disabled, sets up Python, then runs exactly `python3 -m unittest discover -s bin -p 'test_*.py'` from repository root in a bash step. Do not use continue-on-error or an if condition on the job or gate. No pip packages, real workers or network-using tests.
3. Python version is exactly `3.15.2`. This matches the local interpreter version recorded by the manager for the standard-library-only gate. The manager's evidence lists Linux x64 builds for Ubuntu 22.04, 24.04 and 26.04, and identifies ubuntu-latest as Ubuntu 24.04. This supports the selected CI runner and version; it is not a claim that this workflow has run or that every Python version is supported. Do not silently substitute another version.
4. Pin checkout as `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`, with the full-line YAML comment `# actions/checkout v7.0.1` immediately before its uses property. Pin Python setup as `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`, with the full-line YAML comment `# actions/setup-python v7.1.0` immediately before its uses property. Use the SHA, never the mutable version tag, as the action reference.
5. Use JSON flow syntax for the workflow data in the `.yml` file, with only those two full-line YAML comments added. No inline comments. Tests discard only lines whose stripped text starts with `#`, then parse the remaining JSON with the standard library. They also inspect the raw lines for the two required adjacent version comments. This is a fixed-format workflow contract, not a general YAML parser. Tests read this declared workflow file only, then copy inputs to a TemporaryDirectory; they do not change it. No YAML dependency or private validation helper. Tests check the public workflow fields and execute the declared gate command in synthetic temporary projects. The success project has one passing unittest; the failure project has one failing unittest. Neither starts workers or uses the network.
6. The root data has name `check`, on `{'pull_request': {}}`, permissions `{'contents': 'read'}`, and exactly one jobs member, `check`, with runs-on `ubuntu-latest`. Its steps are exactly three objects: the pinned checkout with its with mapping equal to `{'persist-credentials': false}` and no ref override; the pinned Python setup with its with mapping equal to `{'python-version': '3.15.2'}`; then run equal to the parent gate and shell `bash`. The single-quoted mappings here describe JSON values; the workflow uses valid JSON quoting. No defaults or working-directory override. No additional job or step. The normal checkout action PR revision is used; the manager checks the resulting CI run before merging. All T3 code and workflow changes need CI on their PR. Only documentation-only PRs have the temporary no-CI exception in CLAUDE.md.

### Tests

Each row is one test function in `bin/test_ci_workflow.py`.

| Test | Observable assertion |
|---|---|
| `test_ci_runs_on_pull_requests` | Declared on event has unfiltered pull_request. |
| `test_ci_avoids_privileged_pull_request_target` | No pull_request_target event is declared. |
| `test_ci_token_is_read_only` | Workflow permissions are exactly contents read. |
| `test_ci_checkout_is_pinned` | First step uses exactly actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1, not a tag. |
| `test_ci_checkout_version_comment` | The raw line immediately before checkout's uses property is exactly the full-line comment # actions/checkout v7.0.1, after stripping indentation. |
| `test_ci_checks_out_without_persisting_credentials` | Checkout's persist-credentials is false. |
| `test_ci_python_setup_is_pinned` | Second step uses exactly actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0, not a tag. |
| `test_ci_python_setup_version_comment` | The raw line immediately before setup's uses property is exactly # actions/setup-python v7.1.0, after stripping indentation. |
| `test_ci_uses_the_selected_python` | Setup's python-version is exactly the string 3.15.2. |
| `test_ci_workflow_name` | Workflow name is exactly check. |
| `test_ci_has_only_declared_steps` | Exactly three steps, with keys uses/with, uses/with, run/shell in that order, and no extra step. |
| `test_ci_job_uses_the_selected_runner` | Exactly one job check with runs-on ubuntu-latest. |
| `test_ci_runs_the_parent_gate` | The job's bash run step uses exactly the parent gate, with no alternate child gate. |
| `test_ci_gate_runs_at_repository_root` | Workflow, job and step do not redirect working-directory outside repository root. |
| `test_ci_cannot_skip_the_gate` | No job/gate if condition. |
| `test_ci_cannot_ignore_gate_failure` | No job/gate continue-on-error setting. |
| `test_ci_gate_succeeds_on_a_passing_project` | Execute declared run command in synthetic passing project; status 0. |
| `test_ci_gate_fails_on_a_failing_project` | Execute same declared command in synthetic failing project; status nonzero and unittest failure in output. |

Must fail without: pinned checkout action reference → `test_ci_checkout_is_pinned`.
Must fail without: pinned Python setup action reference → `test_ci_python_setup_is_pinned`.
Must fail without: read-only token permission → `test_ci_token_is_read_only`.
Must fail without: disabled credential persistence → `test_ci_checks_out_without_persisting_credentials`.
Must fail without: pull_request trigger field → `test_ci_runs_on_pull_requests`.
Must fail without: parent gate step → `test_ci_runs_the_parent_gate`.

For these configuration guard checks, remove the named field or step from a saved workflow copy, run its named test, then restore and cmp the original. The test must fail on the missing public configuration, not on a JSON parse error or a missing fixture. The tests for forbidden events, conditions and failure masking also assert that those fields are absent; do not describe adding such a forbidden field as removal of an existing code guard.

Done: the parent gate exits 0 in the worker worktree, each named guard check fails for its stated reason when removed, and the manager observes this workflow's CI result on T3's own PR head before merging. The lead cannot verify GitHub Actions locally. Completion is the implementation commit's ancestry in origin/main after the manager's fetch. No direct main commit or local main merge.
