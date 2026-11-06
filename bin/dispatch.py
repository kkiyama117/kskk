"""Dispatch one DSH worker on an aistore card, card review, or landing.

Run from the project root:

    python3 bin/dispatch.py ambiguity [ID ...]
    python3 bin/dispatch.py card ID [--no-worker]
    python3 bin/dispatch.py review ID [--main PATH ...]
    python3 bin/dispatch.py land ID

Cards are `## <ID>. <title>` sections of `<repo>/TASKS.md`. `ambiguity` with
IDs reviews those cards whatever their status; without IDs it reviews every
card that is not done. `card` creates one git worktree per repository the
card's repository builds with, under `local/worktrees/<ID>`, on branch
`card/<ID>`, writes a `go.work` for the set, and runs the implementer in the
card's repository. `review` pipes the diffs of every repository worktree
since it left `main` to a second reviewer; with `--main`, it pipes the uncommitted
changes of those paths in the card's repository, from the main checkout.
`land` looks up the
card for its repository and fast-forwards only the `main` branches that `card/<ID>` has commits for; a
repository without commits is printed as `unchanged`. It removes every
worktree and branch and `local/worktrees/<ID>`, changes nothing when a
worktree is not on its card branch or has changes, or when one of those
`main` branches has moved, and rolls back the fast-forwards it already made
when a later one fails, unless one of them has moved again in the meantime,
the checkout left main, or the working tree could not be rolled back.
It warns without stopping when a repository that uses the card's repository
has moved since the dispatch.

Every verb except `card` starts its worker with `--read-only`, so a read-only
worker cannot build: `review` runs its gate itself, before the reviewer, and
puts the exit code and the last lines of the output in the brief. The worker's
answer (stdout) goes to `local/agents/<UTC>-<name>.md` and its
reasoning and errors (stderr) to the matching `.log`; a name already taken
gains a `-2`, `-3`, ... suffix. Prints the paths and exits with the worker's
code.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KSTACK = Path('/data/softwares/kstack')
WORKER = KSTACK / 'skills/kiyama-mode/scripts/run-worker.sh'
WORKER_ROUTE = ['dsh', 'ollama-cloud', 'deepseek-v4.1-flash', 'high']
REVIEW_ROUTE = ['dsh', 'openai-codex', 'gpt-6.1-sol', 'high']
USES = {
    'llmgw': [],
    'rag': ['llmgw'],
    'eval': ['rag', 'llmgw'],
    'learn': ['rag', 'llmgw'],
    'adopt': ['rag', 'llmgw'],
    'server': ['llmgw', 'rag', 'eval', 'learn', 'adopt'],
    'web': ['rag', 'llmgw', 'learn', 'adopt'],
}
HEADING = re.compile(r'## ([A-Z]+[0-9]+)\. (.*)')

CARD_BRIEF = '''{opening}

Goal of the owner: build the aistore system card by card, each card small and checked, so a reviewer can trust and commit it. You implement exactly one card.

Card {id} ("{title}") of repository `{repo}`. The repository is checked out at `{wt}/{repo}`; the other directories in `{wt}` are the repositories it builds with, all on branch `card/{id}`.

1. Read `{root}/AGENTS.md` in full (the repository's own `AGENTS.md` calls it `../AGENTS.md`). Its rules override everything else, including the poteto-agent file.
2. Read `{wt}/{repo}/SPEC.md` in full, the section `## {id}.` of `{wt}/{repo}/TASKS.md`, and every document that section names.
3. Implement card {id} exactly: only the files {files}, the names and test names it gives, the values it states.
4. Write only under `{wt}/{repo}`. Read the other repositories in `{wt}` only where the card or `SPEC.md` points to them.
5. Run `{narrow}` until it exits 0. If the Go build cache is read-only in your sandbox, set GOCACHE to a directory under /tmp.
6. Do not commit. {never}
7. If the card is ambiguous, a `Needs` card is missing, or the card needs another file or a new dependency, stop and say so in the report instead of guessing.

Final report, plain text, four parts: files changed; the last 20 lines of `make check`; anything in the card you could not do; open questions.'''

AMBIGUITY_BRIEF = '''{opening}

Goal of the owner: a fast implementation model (you) will later implement these cards from the cards and the documents they cite alone. The owner wants them good enough that the implementer never has to guess. Your job now is a read-only review that finds every place you would have to guess.

`{root}/AGENTS.md` holds the rules the implementer follows. It overrides everything else, including the poteto-agent file.

Cards to review:
{card_lines}

Read `{root}/AGENTS.md`, `{root}/PLAN.md`, and for each of the repositories {repos} under `{root}`: `SPEC.md`, the sections of `TASKS.md` for these cards, `Makefile`, `go.mod`, and the contract files {contracts}. Read every document and source file a card names. You may read `{root}/llmgw` and `{root}/rag/api` for context, and the files under `/data/softwares/slack-intake/library` that a card says to port. {never}

Do not edit, create, or delete any file. Do not run git commit. Do not run any command that builds or tests code: you run read-only.

Review only the cards above; ignore every other card. For each, imagine implementing it now. Report every point where:
1. the card and its docs do not say what to do (a missing rule, an unstated default, error code, order, or tie-break),
2. two parts of the card or its docs, or the docs and the code, disagree,
3. a named test cannot be written as described (missing fixture, missing hook such as a clock or fake, behavior not observable),
4. the card needs a file, function, or type that is not on its file list or does not exist yet,
5. a cited document, section, or source file does not exist or does not match its description.

Output only this, as plain text:
- One line per finding: `<card> | <kind 1-5> | <file:line or section> | <what is missing or conflicting> | <the question the owner must answer>`.
- Then one line: `TOTAL <n>`.
Be concrete. Quote the words you mean. Skip style comments. Do not propose code.'''

REVIEW_BRIEF = '''{opening}

Goal of the owner: a worker implemented one card of the aistore system. You are the second reviewer, read-only, before the lead accepts the diff. Do not edit, create, or delete any file. Do not commit.

`{root}/AGENTS.md` holds the rules the worker had to follow.

Card {id} of repository `{repo}`, worktree `{wt}/{repo}`. Read `{root}/AGENTS.md`, `{wt}/{repo}/SPEC.md`, the card below, and the files in `{wt}` that the diff touches (any repository there). {never} Do not run any command that builds or tests code: you run read-only. The dispatcher ran `{gate}` before you started; it exited {gate_code}. The last lines of its output:

```
{gate_tail}
```

Card:

{card_text}

Diff of each repository worktree since it left main (`git diff $(git merge-base main HEAD)`: the card's commits and uncommitted changes), headed by `### <repo>`:

```diff
{diff}
```

Untracked files (read each one):
{untracked_lines}

Report every defect: a rule of the card, `SPEC.md`, or `AGENTS.md` that the diff breaks; a named test that is missing or does not assert what the card says; a bug; a changed file that is not on the card's `Files:` line.

Output only this, as plain text:
- One line per finding: `<file:line> | <high, medium, or low> | <the defect> | <the evidence: quoted code, rule, or command output>`.
- Then one line: `TOTAL <n>`.
Be concrete. Skip style comments. Do not propose code.'''

MAIN_REVIEW_BRIEF = '''{opening}

Goal of the owner: before card {id} of the aistore system runs, its lead changed files in the main checkout of repository `{repo}`, usually a contract that other repositories consume. You are the second reviewer, read-only, before the lead commits the change. Do not edit, create, or delete any file. Do not commit.

`{root}/AGENTS.md` holds the rules the implementer of the card will follow.

The main checkout is `{root}/{repo}`. Read `{root}/AGENTS.md`, `{root}/{repo}/SPEC.md`, the card below, the files that the change touches, and the code that uses them in {consumers}. {never} Do not run any command that builds or tests code: you run read-only. The dispatcher ran `{gate}` before you started; it exited {gate_code}. The last lines of its output:

```
{gate_tail}
```

Card:

{card_text}

Uncommitted change in the main checkout (`git diff HEAD`):

```diff
{diff}
```

Untracked files (read each one):
{untracked_lines}

Report every defect: a bug or a gap in the change; a rule of the card, `SPEC.md`, or `AGENTS.md` that the change breaks or leaves unstated; a part of the card that the change cannot support; code in {consumers} that the change breaks.

Output only this, as plain text:
- One line per finding: `<file:line> | <high, medium, or low> | <the defect> | <the evidence: quoted code, rule, or command output>`.
- Then one line: `TOTAL <n>`.
Be concrete. Skip style comments. Do not propose code.'''

HARNESS_LINE = 'the worker did not start (cause:harness). Report it; do not switch the model or the runner.'


class DispatchError(Exception):
    """A problem the lead has to fix before the verb can run."""


@dataclass
class Card:
    id: str
    title: str
    repo: str
    text: str
    done: bool
    files: list


def git(*args, cwd=None, allow_failure=False):
    done = subprocess.run(['git', *[str(arg) for arg in args]], cwd=cwd,
                          capture_output=True, text=True)
    if done.returncode and not allow_failure:
        raise DispatchError(f'git {" ".join(str(arg) for arg in args)}: {done.stderr.strip()}')
    return done


def parse_cards(repo, text):
    lines = text.splitlines()
    cards = []
    index = 0
    while index < len(lines):
        match = HEADING.match(lines[index])
        if not match:
            index += 1
            continue
        end = index + 1
        while end < len(lines) and not lines[end].startswith('## '):
            end += 1
        body = lines[index:end]
        cards.append(Card(match.group(1), match.group(2), repo, '\n'.join(body),
                          any(line.strip() == 'Status: done' for line in body),
                          files_of(body)))
        index = end
    return cards


def files_of(body):
    for line in body:
        if line.startswith('Files:'):
            return re.findall(r'`([^`]+)`', line)
    return []


def all_cards(root):
    cards = []
    for repo in sorted(path.name for path in root.iterdir()
                       if path.is_dir() and (path / 'TASKS.md').is_file()):
        cards.extend(parse_cards(repo, (root / repo / 'TASKS.md').read_text(encoding='utf-8')))
    return cards


def find_card(root, card_id):
    matches = [card for card in all_cards(root) if card.id == card_id]
    if not matches:
        raise DispatchError(f'no card {card_id} in any TASKS.md')
    if len(matches) > 1:
        repos = ', '.join(card.repo for card in matches)
        raise DispatchError(f'card {card_id} is in two repositories: {repos}')
    return matches[0]


def _uses(name, target):
    return any(dep == target or _uses(dep, target) for dep in USES.get(name, ()))


def users(repo):
    return [name for name in USES if name != repo and _uses(name, repo)]


def repo_set(repo):
    if repo not in USES:
        return [repo]
    members = {repo, *users(repo)}
    pending = list(members)
    while pending:
        for dep in USES.get(pending.pop(), ()):
            if dep not in members:
                members.add(dep)
                pending.append(dep)
    return [name for name in USES if name in members]


def worktree_root(root, card_id):
    return root / 'local/worktrees' / card_id


def _go_version(text):
    for line in text.splitlines():
        if line.startswith('go '):
            return line.split()[1]
    raise DispatchError('go.work has no go line')


def write_go_work(root, wt_root, repos):
    version = _go_version((root / 'go.work').read_text(encoding='utf-8'))
    used = ''.join(f'\t./{repo}\n' for repo in repos if (wt_root / repo / 'go.mod').is_file())
    (wt_root / 'go.work').write_text(f'go {version}\n\nuse (\n{used})\n', encoding='utf-8')
    if (root / 'go.work.sum').is_file():
        shutil.copyfile(root / 'go.work.sum', wt_root / 'go.work.sum')


def gates(wt_root, card):
    def gate(repo):
        return f'GOWORK={wt_root}/go.work make -C {wt_root}/{repo} check'
    narrow = gate(card.repo)
    return narrow, ' && '.join([narrow, *(gate(repo) for repo in users(card.repo))])


def main_gate(root, card):
    return ' && '.join(f'GOWORK={root}/go.work make -C {root}/{repo} check'
                       for repo in [card.repo, *users(card.repo)])


def run_gate(command, cwd):
    done = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors='replace')
    tail = '\n'.join(done.stdout.splitlines()[-40:])
    print(f'gate exit {done.returncode}')
    return done.returncode, tail or '(no output)'


def _status_paths(tree):
    status = git('status', '--porcelain', '-z', '--untracked-files=all', cwd=tree).stdout
    parts = status.split('\0')
    paths = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        paths.append(entry[3:])
        if 'R' in entry[:2] or 'C' in entry[:2]:
            paths.append(parts[index])
            index += 1
    return paths


def off_list(wt_root, card):
    outside = []
    trees = sorted(path for path in wt_root.iterdir() if (path / '.git').exists())
    for tree in trees:
        for path in _status_paths(tree):
            if tree.name == card.repo and any(fnmatch.fnmatchcase(path, pattern)
                                              for pattern in card.files):
                continue
            outside.append(f'{tree.name}/{path}')
    return outside


def _opening():
    return (f'Read `{KSTACK}/agents/poteto-agent.md` in full and follow it. '
            f"kiyama-mode's `SKILL.md` is at `{KSTACK}/skills/kiyama-mode/SKILL.md`. "
            'You cannot spawn subagents.')


def _never(root):
    return (f'Never read anything under `/data/references/`, under `{root}/local/agents/`, or under '
            f'`{root}/local/worktrees/` outside the worktree this brief names (if it names one), or any '
            'credentials (API keys, tokens, `.env` and `.secret.toml` files, DSH or provider configuration). '
            'Search only the paths this brief and the card name. Never run `grep -r` or any other recursive '
            f'search from `{root}`, from a worktree root, or from a repository root.')


def card_brief(root, wt_root, card):
    files = ', '.join(f'`{path}`' for path in card.files)
    narrow = gates(wt_root, card)[0]
    return CARD_BRIEF.format(opening=_opening(), never=_never(root), root=root, wt=wt_root,
                             id=card.id, title=card.title, repo=card.repo, files=files,
                             narrow=narrow)


def _ordered(names):
    return ([name for name in USES if name in names]
            + sorted(name for name in names if name not in USES))


def _contract_files(root, repos):
    found = []
    for repo in repos:
        directory = root / repo
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob('*.go')):
            if '.git' in path.parts:
                continue
            with path.open(encoding='utf-8', errors='replace') as handle:
                if handle.readline().rstrip('\n') == '// CONTRACT: do not edit':
                    found.append(path)
    return found


def ambiguity_brief(root, cards):
    repos = _ordered({card.repo for card in cards})
    contracts = _contract_files(root, repos)
    return AMBIGUITY_BRIEF.format(
        opening=_opening(), never=_never(root), root=root,
        card_lines='\n'.join(f'- {card.id} ({card.repo}): {card.title}' for card in cards),
        repos=', '.join(f'`{repo}`' for repo in repos),
        contracts=', '.join(f'`{path}`' for path in contracts) if contracts else 'none')


def review_brief(root, wt_root, card, diff, untracked, gate_code, gate_tail):
    return REVIEW_BRIEF.format(
        opening=_opening(), never=_never(root), root=root, wt=wt_root, id=card.id,
        repo=card.repo, card_text=card.text, diff=diff, gate=gates(wt_root, card)[0],
        gate_code=gate_code, gate_tail=gate_tail,
        untracked_lines='\n'.join(f'- {path}' for path in untracked) if untracked else 'none')


def main_review_brief(root, card, diff, untracked, gate_code, gate_tail):
    repos = [card.repo, *users(card.repo)]
    lines = '\n'.join(f'- {root}/{card.repo}/{path}' for path in untracked)
    return MAIN_REVIEW_BRIEF.format(
        opening=_opening(), never=_never(root), root=root, id=card.id, repo=card.repo,
        card_text=card.text, diff=diff, gate=main_gate(root, card),
        gate_code=gate_code, gate_tail=gate_tail,
        consumers=', '.join(f'`{root}/{repo}`' for repo in repos),
        untracked_lines=lines or 'none')


def _open_outputs(root, stamp, name):
    out = root / 'local/agents'
    out.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        suffix = '' if index == 1 else f'-{index}'
        answer = out / f'{stamp}-{name}{suffix}.md'
        try:
            stdout = answer.open('x', encoding='utf-8')
        except FileExistsError:
            index += 1
            continue
        log = out / f'{stamp}-{name}{suffix}.log'
        try:
            stderr = log.open('x', encoding='utf-8')
        except FileExistsError:
            stdout.close()
            answer.unlink()
            index += 1
            continue
        return answer, log, stdout, stderr


def run_worker(root, name, workdir, route, brief, read_only, worker=WORKER, env=None):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    answer, log, stdout, stderr = _open_outputs(root, stamp, name)
    command = [str(worker), *(['--read-only'] if read_only else []), str(workdir), *route]
    with stdout, stderr:
        code = subprocess.run(command, input=brief, text=True,
                              stdout=stdout, stderr=stderr, env=env).returncode
    print(f'answer {answer}')
    print(f'log {log}')
    print(f'exit {code}')
    if code and _harness_failure(log):
        print(HARNESS_LINE)
    return code


def _harness_failure(log):
    text = log.read_text(encoding='utf-8', errors='replace')
    return 'UNKNOWN_MODEL' in text or 'MISSING_CREDENTIAL' in text


def _branch_exists(repo, branch):
    done = git('rev-parse', '--verify', '--quiet', f'refs/heads/{branch}', cwd=repo,
               allow_failure=True)
    return done.returncode == 0


def _ambiguity(args, root, worker):
    if args.ids:
        cards = [find_card(root, card_id) for card_id in args.ids]
        name = 'ambiguity-' + '-'.join(args.ids)
    else:
        cards = [card for card in all_cards(root) if not card.done]
        name = 'ambiguity-all'
    if not cards:
        raise DispatchError('no cards to review')
    return run_worker(root, name, root, WORKER_ROUTE, ambiguity_brief(root, cards),
                      read_only=True, worker=worker)


def _discard_card(root, wt_root, branch, made):
    for repo in reversed(made):
        git('worktree', 'remove', '--force', wt_root / repo, cwd=root / repo,
            allow_failure=True)
        git('branch', '-D', branch, cwd=root / repo, allow_failure=True)
    shutil.rmtree(wt_root, ignore_errors=True)


def _make_card(root, wt_root, branch, repos):
    (root / 'local/worktrees').mkdir(parents=True, exist_ok=True)
    try:
        wt_root.mkdir()
    except FileExistsError:
        raise DispatchError(f'worktree {wt_root} exists; land or remove it first')
    made = []
    try:
        for repo in repos:
            git('worktree', 'add', '-b', branch, wt_root / repo, 'main', cwd=root / repo)
            made.append(repo)
        write_go_work(root, wt_root, repos)
    except Exception:
        _discard_card(root, wt_root, branch, made)
        raise


def _card(args, root, worker):
    card = find_card(root, args.id)
    wt_root = worktree_root(root, card.id)
    branch = f'card/{card.id}'
    head = git('symbolic-ref', '--quiet', '--short', 'HEAD', cwd=root / card.repo,
               allow_failure=True).stdout.strip()
    if head != 'main':
        raise DispatchError(f'{card.repo}: the main checkout is not on branch main')
    if card.done:
        raise DispatchError(f'card {card.id} is done')
    tasks = git('-c', 'core.quotepath=false', 'status', '--porcelain', '--', 'TASKS.md',
                cwd=root / card.repo).stdout
    if tasks.strip():
        raise DispatchError(f'{card.repo}: TASKS.md has uncommitted changes; '
                            'commit the card first')
    if wt_root.exists():
        raise DispatchError(f'worktree {wt_root} exists; land or remove it first')
    repos = repo_set(card.repo)
    taken = [repo for repo in repos if _branch_exists(root / repo, branch)]
    if taken:
        raise DispatchError(f'branch {branch} already exists in {", ".join(taken)}')
    for repo in repos:
        if _status_paths(root / repo):
            print(f'warning: {repo} has uncommitted changes in the main checkout; '
                  'the worktree starts from main')
    _make_card(root, wt_root, branch, repos)
    narrow, full = gates(wt_root, card)
    print(f'worktree {wt_root}')
    print(f'narrow gate: {narrow}')
    print(f'full gate: {full}')
    if args.no_worker:
        return 0
    env = {**os.environ, 'GOWORK': str(wt_root / 'go.work')}
    code = run_worker(root, f'card-{card.id}', wt_root / card.repo, WORKER_ROUTE,
                      card_brief(root, wt_root, card), read_only=False, worker=worker, env=env)
    outside = off_list(wt_root, card)
    if outside:
        print('changes outside Files:')
        for path in outside:
            print(f'  {path}')
    else:
        print('no changes outside Files')
    return code


def _worktree_repos(wt_root):
    return sorted(path.name for path in wt_root.iterdir()
                  if path.is_dir() and (path / '.git').exists())


def _worktree_changes(wt_root):
    diffs = []
    untracked = []
    for repo in _worktree_repos(wt_root):
        tree = wt_root / repo
        base = git('merge-base', 'main', 'HEAD', cwd=tree).stdout.strip()
        diff = git('diff', base, cwd=tree).stdout
        if diff.strip():
            diffs.append(f'### {repo}\n{diff}')
        untracked.extend(str(tree / path) for path in _untracked(tree))
    return ''.join(diffs), untracked


def _untracked(tree, pathspec=()):
    out = git('ls-files', '--others', '--exclude-standard', '-z', *pathspec, cwd=tree).stdout
    return [path for path in out.split('\0') if path]


def _review(args, root, worker):
    card = find_card(root, args.id)
    if args.main:
        tree = root / card.repo
        diff = git('diff', 'HEAD', '--', *args.main, cwd=tree).stdout
        untracked = _untracked(tree, ('--', *args.main))
        if not diff.strip() and not untracked:
            raise DispatchError(f'no uncommitted changes in {", ".join(args.main)} of {card.repo}')
        gate_code, gate_tail = run_gate(main_gate(root, card), tree)
        env = {**os.environ, 'GOWORK': str(root / 'go.work')}
        return run_worker(root, f'review-{card.id}-main', tree, REVIEW_ROUTE,
                          main_review_brief(root, card, diff, untracked, gate_code, gate_tail),
                          read_only=True, worker=worker, env=env)
    wt_root = worktree_root(root, card.id)
    if not wt_root.is_dir():
        raise DispatchError(f'no worktree {wt_root}')
    diff, untracked = _worktree_changes(wt_root)
    gate_code, gate_tail = run_gate(gates(wt_root, card)[0], wt_root / card.repo)
    return run_worker(root, f'review-{card.id}', wt_root / card.repo, REVIEW_ROUTE,
                      review_brief(root, wt_root, card, diff, untracked, gate_code, gate_tail),
                      read_only=True, worker=worker)


def _ancestor(root, repo, ancestor, descendant):
    done = git('merge-base', '--is-ancestor', ancestor, descendant, cwd=root / repo,
               allow_failure=True)
    return done.returncode == 0


def _check_landable(root, wt_root, repo, branch, own):
    head = git('symbolic-ref', '--quiet', '--short', 'HEAD', cwd=wt_root / repo,
               allow_failure=True).stdout.strip()
    if head != branch:
        raise DispatchError(f'{repo}: the worktree is not on {branch}; check out {branch} '
                            'and commit there')
    if _status_paths(wt_root / repo):
        raise DispatchError(f'{repo}: worktree has uncommitted changes; commit or discard them first')
    if not own:
        return
    if git('rev-parse', '--abbrev-ref', 'HEAD', cwd=root / repo).stdout.strip() != 'main':
        raise DispatchError(f'{repo}: the main checkout is not on branch main')
    if not _ancestor(root, repo, 'main', branch):
        raise DispatchError(f'{repo}: main has moved since the dispatch. Rebase {branch} onto '
                            f'main in {wt_root / repo}, run the full gate again, then land again.')


def _revert_main(root, repo, branch, before, after):
    """Return why the rollback of one repository stopped, or None on success."""
    tree = root / repo
    head = git('symbolic-ref', '--quiet', 'HEAD', cwd=tree, allow_failure=True).stdout.strip()
    if head != 'refs/heads/main':
        return 'the main checkout is no longer on main'
    # update-ref moves main only from this land's commit and read-tree keeps other agents' changes; reset --keep drops them.
    moved = git('update-ref', '-m', f'dispatch: roll back {branch}', 'refs/heads/main',
                before, after, cwd=tree, allow_failure=True)
    if moved.returncode:
        return 'main moved in another checkout during the land'
    tree_done = git('read-tree', '-m', '-u', after, before, cwd=tree, allow_failure=True)
    if tree_done.returncode:
        git('update-ref', 'refs/heads/main', after, before, cwd=tree)
        return f'the working tree could not be rolled back: {tree_done.stderr.strip()}'
    return None


def _rollback_report(failed, stderr, stopped, before, after, now, rolled):
    lines = [f'{failed}: the fast-forward failed: {stderr}. '
             f'The rollback stopped at {stopped[0]}: {stopped[1]}. Check each repository:']
    for repo in now:
        state = 'rolled back' if repo in rolled else 'not rolled back'
        lines.append(f'  {repo} before {before[repo]} after {after[repo]} now {now[repo]} {state}')
    return '\n'.join(lines)


def _roll_back(root, branch, failed, stderr, before, after, merged):
    rolled = set()
    stopped = None
    for repo in reversed(merged):
        reason = _revert_main(root, repo, branch, before[repo], after[repo])
        if reason:
            stopped = (repo, reason)
            break
        rolled.add(repo)
    if stopped is None:
        raise DispatchError(f'{failed}: the fast-forward failed: {stderr}. '
                            'Nothing was landed; fix the main checkout and land again.')
    now = {repo: git('rev-parse', 'main', cwd=root / repo).stdout.strip() for repo in merged}
    raise DispatchError(_rollback_report(failed, stderr, stopped, before, after, now, rolled))


def _fast_forward(root, branch, targets):
    before = {}
    after = {}
    merged = []
    for repo in targets:
        before[repo] = git('rev-parse', 'main', cwd=root / repo).stdout.strip()
        after[repo] = git('rev-parse', branch, cwd=root / repo).stdout.strip()
        done = git('merge', '--ff-only', '--no-overwrite-ignore', branch, cwd=root / repo,
                   allow_failure=True)
        if done.returncode:
            _roll_back(root, branch, repo, done.stderr.strip(), before, after, merged)
        merged.append(repo)


def _land(args, root):
    card = find_card(root, args.id)
    wt_root = worktree_root(root, args.id)
    if not wt_root.is_dir():
        raise DispatchError(f'no worktree {wt_root}')
    branch = f'card/{args.id}'
    repos = _worktree_repos(wt_root)
    tip = {}
    own = {}
    for repo in repos:
        tip[repo] = git('rev-parse', branch, cwd=root / repo).stdout.strip()
        own[repo] = not _ancestor(root, repo, branch, 'main')
    for repo in repos:
        _check_landable(root, wt_root, repo, branch, own[repo])
    for repo in repos:
        if not own[repo] and repo in users(card.repo) and not _ancestor(root, repo, 'main', branch):
            print(f'warning: {repo} main has moved since the dispatch, so the full gate ran '
                  f'against an older {repo}')
    _fast_forward(root, branch, [repo for repo in repos if own[repo]])
    for repo in repos:
        git('worktree', 'remove', wt_root / repo, cwd=root / repo)
        if own[repo]:
            git('branch', '-d', branch, cwd=root / repo)
            print(f'landed {repo} {git("log", "--oneline", "-1", cwd=root / repo).stdout.strip()}')
        elif git('update-ref', '-d', f'refs/heads/{branch}', tip[repo], cwd=root / repo,
                 allow_failure=True).returncode:
            print(f'kept {repo} {branch}: it gained commits during the land; '
                  'land again or delete it by hand')
        else:
            print(f'unchanged {repo}')
    shutil.rmtree(wt_root)
    return 0


def main(argv=None, root=ROOT, worker=WORKER):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = parser.add_subparsers(dest='verb', required=True)
    ambiguity = verbs.add_parser('ambiguity', help='review cards for missing decisions')
    ambiguity.add_argument('ids', nargs='*', metavar='id')
    card = verbs.add_parser('card', help='make the worktrees and run the implementer')
    card.add_argument('id')
    card.add_argument('--no-worker', action='store_true')
    review = verbs.add_parser('review', help='run the second reviewer on a worktree or the main checkout')
    review.add_argument('id')
    review.add_argument('--main', nargs='+', metavar='PATH')
    land = verbs.add_parser('land', help='fast-forward main and remove the worktrees')
    land.add_argument('id')
    args = parser.parse_args(argv)
    root = Path(root)
    try:
        if args.verb == 'ambiguity':
            return _ambiguity(args, root, worker)
        if args.verb == 'card':
            return _card(args, root, worker)
        if args.verb == 'review':
            return _review(args, root, worker)
        return _land(args, root)
    except DispatchError as error:
        print(f'dispatch: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
