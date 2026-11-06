import contextlib
import datetime
import io
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dispatch  # noqa: E402

GO_WORK = '''go 1.27

use (
\t./llmgw
\t./rag
\t./eval
\t./learn
\t./adopt
\t./server
\t./web
)
'''

LLMGW_TASKS = '''# llmgw tasks

## L1. Fake server

Status: done

Needs: nothing.

Files: `fake/fake.go`, `fake/fake_test.go`.

Build package `fake`.

## L2. Config and client skeleton

Status: open

Needs: L1.

Files: `config.go`, `client.go`.

Load the config.
'''

RAG_TASKS = '''# rag tasks

## R1. Ingest

Status: open

Files: `ingest.go`, `testdata/docs/*.txt`.

Ingest documents.
'''

EVAL_TASKS = '''# eval tasks

## E1. Build queries

Status: open

Files: `impl.go`, `impl_test.go`, `testdata/docs/*.txt`.

Build queries.
'''

WEB_TASKS = '''# web tasks

## W1. Shell

Status: open

Files: `index.html`.

Build the shell.
'''

LEARN_TASKS = '''# learn tasks

## N1. Lessons

Status: open

Files: `lesson.go`.

Write the lessons.
'''

GO_REPOS = ['llmgw', 'rag', 'eval', 'learn', 'adopt', 'server', 'web']

# web is a Go repository now, but it does not use eval, so card E1 builds without it.
EVAL_REPOS = ['llmgw', 'rag', 'eval', 'learn', 'adopt', 'server']

WT_GO_WORK = '''go 1.27

use (
\t./llmgw
\t./rag
\t./eval
\t./learn
\t./adopt
\t./server
)
'''


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def commit(directory, message):
    git('add', '-A', cwd=directory)
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-m', message, cwd=directory)


def make_repo(directory, tasks, with_go=True):
    directory.mkdir()
    (directory / 'TASKS.md').write_text(tasks)
    (directory / 'SPEC.md').write_text('# spec\n')
    if with_go:
        (directory / 'go.mod').write_text(f'module aistore/{directory.name}\n\ngo 1.27\n')
        (directory / 'Makefile').write_text('check:\n\t@true\n')
    git('init', '-b', 'main', cwd=directory)
    commit(directory, 'init')


def build_project(base):
    root = base / 'aistore'
    root.mkdir()
    (root / 'go.work').write_text(GO_WORK)
    (root / 'AGENTS.md').write_text('# Rules for implementation agents\n')
    tasks = {'llmgw': LLMGW_TASKS, 'rag': RAG_TASKS, 'eval': EVAL_TASKS,
             'learn': LEARN_TASKS, 'adopt': '# adopt tasks\n', 'server': '# server tasks\n'}
    for repo, text in tasks.items():
        make_repo(root / repo, text)
    make_repo(root / 'web', WEB_TASKS)
    return root


def fake_worker(directory, record, stdout_text='answer text', stderr_text='reasoning text',
                code=0, touch=(), name='fake-worker.sh'):
    path = directory / name
    lines = ['#!/usr/bin/env bash', 'set -u',
             f'printf "%s\\n" "$@" >> {shlex.quote(str(record / "argv.txt"))}',
             f'printf "run\\n" >> {shlex.quote(str(record / "runs.txt"))}',
             f'printf "%s\\n" "${{GOWORK:-}}" >> {shlex.quote(str(record / "gowork.txt"))}',
             f'cat >> {shlex.quote(str(record / "stdin.txt"))}',
             f'printf "%s\\n" {shlex.quote(stderr_text)} >&2',
             f'printf "%s\\n" {shlex.quote(stdout_text)}']
    for item in touch:
        lines += [f'mkdir -p {shlex.quote(str(Path(item).parent))}',
                  f'printf "x\\n" > {shlex.quote(str(item))}']
    lines.append(f'exit {code}')
    path.write_text('\n'.join(lines) + '\n')
    path.chmod(0o755)
    return path


def never_text(root):
    return (f'Never read anything under `/data/references/`, under `{root}/local/agents/`, or under '
            f'`{root}/local/worktrees/` outside the worktree this brief names (if it names one), or any '
            'credentials (API keys, tokens, `.env` and `.secret.toml` files, DSH or provider configuration). '
            'Search only the paths this brief and the card name. Never run `grep -r` or any other recursive '
            f'search from `{root}`, from a worktree root, or from a repository root.')


def clock_at(stamp):
    class Fixed:
        @staticmethod
        def now(tz=None):
            return stamp
    return Fixed


def brief_never(text):
    start = text.index('Never read anything')
    end = text.index('repository root.') + len('repository root.')
    return text[start:end]


class DispatchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.root = build_project(self.base)
        self.record = self.base / 'record'
        self.record.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def worker(self, **kwargs):
        return fake_worker(self.base, self.record, **kwargs)

    def invoke(self, *argv, worker=None):
        worker = worker or self.worker()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = dispatch.main(list(argv), root=self.root, worker=worker)
        return code, out.getvalue(), err.getvalue()

    def recorded(self, name):
        path = self.record / name
        return path.read_text().splitlines() if path.exists() else []

    def runs(self):
        return len(self.recorded('runs.txt'))

    def record_text(self, name):
        return (self.record / name).read_text()

    def only_answer(self):
        answers = sorted((self.root / 'local/agents').glob('*.md'))
        self.assertEqual(len(answers), 1)
        return answers[0], answers[0].with_suffix('.log')

    def test_card_parsing(self):
        cards = {(card.repo, card.id): card for card in dispatch.all_cards(self.root)}
        self.assertEqual(cards[('eval', 'E1')].title, 'Build queries')
        self.assertEqual(cards[('eval', 'E1')].files,
                         ['impl.go', 'impl_test.go', 'testdata/docs/*.txt'])
        self.assertFalse(cards[('eval', 'E1')].done)
        self.assertTrue(cards[('llmgw', 'L1')].done)
        self.assertFalse(cards[('llmgw', 'L2')].done)
        self.assertEqual(cards[('llmgw', 'L1')].files, ['fake/fake.go', 'fake/fake_test.go'])
        self.assertIn('## E1. Build queries', cards[('eval', 'E1')].text)
        self.assertNotIn('## W1', cards[('llmgw', 'L1')].text)

    def test_all_cards_are_in_repository_name_order(self):
        repos = [card.repo for card in dispatch.all_cards(self.root)]
        self.assertEqual(repos, sorted(repos))
        self.assertEqual(repos[0], 'eval')

    def test_unknown_card(self):
        with self.assertRaises(dispatch.DispatchError) as caught:
            dispatch.find_card(self.root, 'Z9')
        self.assertEqual(str(caught.exception), 'no card Z9 in any TASKS.md')
        code, out, err = self.invoke('card', 'Z9', '--no-worker')
        self.assertEqual(code, 2)
        self.assertEqual(err, 'dispatch: no card Z9 in any TASKS.md\n')

    def test_duplicate_card(self):
        tasks = self.root / 'rag' / 'TASKS.md'
        tasks.write_text(tasks.read_text() + '\n## E1. Duplicate\n\nStatus: open\n')
        with self.assertRaises(dispatch.DispatchError) as caught:
            dispatch.find_card(self.root, 'E1')
        message = str(caught.exception)
        self.assertIn('eval', message)
        self.assertIn('rag', message)

    def test_repo_set_and_users(self):
        self.assertEqual(dispatch.repo_set('eval'), EVAL_REPOS)
        self.assertEqual(dispatch.repo_set('llmgw'), GO_REPOS)
        self.assertEqual(dispatch.repo_set('web'), ['llmgw', 'rag', 'learn', 'adopt', 'web'])
        self.assertEqual(dispatch.repo_set('docs'), ['docs'])
        self.assertEqual(dispatch.users('learn'), ['server', 'web'])
        self.assertEqual(dispatch.users('adopt'), ['server', 'web'])
        self.assertEqual(dispatch.users('rag'), ['eval', 'learn', 'adopt', 'server', 'web'])
        self.assertEqual(dispatch.users('llmgw'),
                         ['rag', 'eval', 'learn', 'adopt', 'server', 'web'])
        self.assertEqual(dispatch.users('server'), [])

    def test_card_without_worker(self):
        wt = self.root / 'local/worktrees/E1'
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(self.runs(), 0)
        self.assertFalse((self.root / 'local/agents').exists())
        self.assertEqual(sorted(path.name for path in wt.iterdir() if path.is_dir()),
                         sorted(EVAL_REPOS))
        for repo in EVAL_REPOS:
            self.assertEqual(git('rev-parse', '--abbrev-ref', 'HEAD', cwd=wt / repo).strip(),
                             'card/E1')
        self.assertEqual((wt / 'go.work').read_text(), WT_GO_WORK)
        narrow = f'GOWORK={wt}/go.work make -C {wt}/eval check'
        full = f'{narrow} && GOWORK={wt}/go.work make -C {wt}/server check'
        self.assertIn(f'worktree {wt}\n', out)
        self.assertIn(f'narrow gate: {narrow}\n', out)
        self.assertIn(f'full gate: {full}\n', out)
        gate = subprocess.run(['bash', '-c', narrow], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(gate.returncode, 0, gate.stderr)

    def test_card_in_learn_brings_web(self):
        wt = self.root / 'local/worktrees/N1'
        code, out, err = self.invoke('card', 'N1', '--no-worker')
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(sorted(path.name for path in wt.iterdir() if path.is_dir()),
                         sorted(GO_REPOS))
        self.assertIn(f'full gate: GOWORK={wt}/go.work make -C {wt}/learn check && '
                      f'GOWORK={wt}/go.work make -C {wt}/server check && '
                      f'GOWORK={wt}/go.work make -C {wt}/web check\n', out)

    def test_card_writes_go_work_with_the_version_of_the_parent(self):
        (self.root / 'go.work').write_text('go 1.28\n\nuse (\n)\n')
        (self.root / 'go.work.sum').write_text('sum line\n')
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 0)
        wt = self.root / 'local/worktrees/E1'
        self.assertTrue((wt / 'go.work').read_text().startswith('go 1.28\n\nuse (\n'))
        self.assertEqual((wt / 'go.work.sum').read_text(), 'sum line\n')

    def test_card_refuses_a_done_card(self):
        code, out, err = self.invoke('card', 'L1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('L1 is done', err)
        self.assertFalse((self.root / 'local/worktrees/L1').exists())

    def test_card_refuses_an_existing_worktree(self):
        (self.root / 'local/worktrees/E1').mkdir(parents=True)
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('exists', err)
        self.assertEqual(list((self.root / 'local/worktrees/E1').iterdir()), [])
        self.assertEqual(self.runs(), 0)

    def test_card_refuses_an_existing_branch(self):
        git('branch', 'card/E1', cwd=self.root / 'rag')
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('card/E1', err)
        self.assertIn('rag', err)
        self.assertFalse((self.root / 'local/worktrees/E1').exists())
        self.assertEqual(self.runs(), 0)

    def test_card_refuses_an_uncommitted_tasks_file(self):
        mains = {repo: git('rev-parse', 'main', cwd=self.root / repo).strip() for repo in GO_REPOS}
        tasks = self.root / 'eval' / 'TASKS.md'
        tasks.write_text(tasks.read_text() + '\n## E2. Later\n\nStatus: open\n')
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('eval: TASKS.md has uncommitted changes; commit the card first', err)
        self.assertFalse((self.root / 'local/worktrees/E1').exists())
        for repo in GO_REPOS:
            self.assertEqual(git('rev-parse', 'main', cwd=self.root / repo).strip(), mains[repo])
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
        self.assertEqual(self.runs(), 0)

    def test_card_refuses_when_main_checkout_is_not_on_main(self):
        git('branch', '-m', 'main', 'trunk', cwd=self.root / 'eval')
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertEqual(err, 'dispatch: eval: the main checkout is not on branch main\n')
        self.assertFalse((self.root / 'local/worktrees/E1').exists())
        for repo in GO_REPOS:
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
        self.assertEqual(self.runs(), 0)

    def test_card_cleanup_keeps_what_it_did_not_create(self):
        git('branch', 'card/E1', cwd=self.root / 'rag')
        wt = self.root / 'local/worktrees/E1'
        with mock.patch.object(dispatch, '_branch_exists', return_value=False):
            code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('rag', err)
        self.assertFalse(wt.exists())
        self.assertIn('card/E1', git('branch', '--list', 'card/E1', cwd=self.root / 'rag'))
        for repo in GO_REPOS:
            if repo == 'rag':
                continue
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
            self.assertEqual(len(git('worktree', 'list', cwd=self.root / repo).splitlines()), 1)

    def test_card_cleans_up_after_a_failed_worktree_add(self):
        mains = {repo: git('rev-parse', 'main', cwd=self.root / repo).strip()
                 for repo in GO_REPOS if repo != 'rag'}
        git('branch', '-m', 'main', 'trunk', cwd=self.root / 'rag')
        trunk = git('rev-parse', 'trunk', cwd=self.root / 'rag').strip()
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 2)
        self.assertIn('rag', err)
        self.assertFalse((self.root / 'local/worktrees/E1').exists())
        for repo in GO_REPOS:
            if repo != 'rag':
                self.assertEqual(git('rev-parse', 'main', cwd=self.root / repo).strip(),
                                 mains[repo])
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
            self.assertEqual(len(git('worktree', 'list', cwd=self.root / repo).splitlines()), 1)
        self.assertEqual(git('rev-parse', 'trunk', cwd=self.root / 'rag').strip(), trunk)
        self.assertEqual(self.runs(), 0)

    def test_gates_include_users_without_a_makefile(self):
        (self.root / 'server' / 'Makefile').unlink()
        card = dispatch.find_card(self.root, 'E1')
        wt = self.root / 'local/worktrees/E1'
        wt.mkdir(parents=True)
        narrow, full = dispatch.gates(wt, card)
        self.assertEqual(narrow, f'GOWORK={wt}/go.work make -C {wt}/eval check')
        self.assertIn(f'GOWORK={wt}/go.work make -C {wt}/server check', full)
        brief = dispatch.main_review_brief(self.root, card, '', [], 0, 'ok')
        self.assertIn(f'GOWORK={self.root}/go.work make -C {self.root}/server check', brief)

    def test_card_warns_about_a_dirty_main_checkout(self):
        (self.root / 'llmgw' / 'local.txt').write_text('dirty\n')
        code, out, err = self.invoke('card', 'E1', '--no-worker')
        self.assertEqual(code, 0)
        self.assertIn('warning: llmgw has uncommitted changes in the main checkout; '
                      'the worktree starts from main', out)
        self.assertEqual(git('rev-parse', '--abbrev-ref', 'HEAD',
                             cwd=self.root / 'local/worktrees/E1/llmgw').strip(), 'card/E1')

    def test_briefs_share_the_search_rule_and_name_the_worktree(self):
        card = dispatch.find_card(self.root, 'E1')
        wt = self.root / 'local/worktrees/E1'
        wt.mkdir(parents=True)
        card_text = dispatch.card_brief(self.root, wt, card)
        review_text = dispatch.review_brief(self.root, wt, card, 'diff body', ['a.txt'], 0, 'ok')
        self.assertEqual(brief_never(card_text), brief_never(review_text))
        for text in (card_text, review_text):
            self.assertEqual(brief_never(text), never_text(self.root))
            self.assertIn(f'{self.root}/local/agents/', text)
            self.assertIn(f'{self.root}/local/worktrees/', text)
            self.assertIn(str(wt), text)

    def test_card_with_worker(self):
        wt = self.root / 'local/worktrees/E1'
        card = dispatch.find_card(self.root, 'E1')
        worker = self.worker(stdout_text='implemented E1', stderr_text='reasoning', code=3,
                             touch=[wt / 'eval/extra.go', wt / 'eval/impl.go',
                                    wt / 'eval/testdata/docs/note.txt'])
        code, out, err = self.invoke('card', 'E1', worker=worker)
        self.assertEqual(code, 3)
        answer, log = self.only_answer()
        self.assertEqual(answer.read_text(), 'implemented E1\n')
        self.assertEqual(log.read_text(), 'reasoning\n')
        self.assertIn(f'answer {answer}\n', out)
        self.assertIn(f'log {log}\n', out)
        self.assertIn('exit 3\n', out)
        argv = self.recorded('argv.txt')
        self.assertEqual(argv[0], str(wt / 'eval'))
        self.assertEqual(argv[1:], dispatch.WORKER_ROUTE)
        self.assertNotIn('--read-only', argv)
        self.assertEqual(self.record_text('stdin.txt'), dispatch.card_brief(self.root, wt, card))
        self.assertEqual(self.record_text('gowork.txt').strip(), str(wt / 'go.work'))
        self.assertIn('changes outside Files:\n  eval/extra.go\n', out)
        self.assertNotIn('impl.go', out)
        self.assertNotIn('note.txt', out)

    def test_card_reports_no_changes_outside_files(self):
        wt = self.root / 'local/worktrees/E1'
        worker = self.worker(touch=[wt / 'eval/impl.go', wt / 'eval/testdata/docs/note.txt'])
        code, out, err = self.invoke('card', 'E1', worker=worker)
        self.assertEqual(code, 0)
        self.assertIn('no changes outside Files\n', out)
        self.assertNotIn('changes outside Files:', out)

    def test_off_list_reports_both_sides_of_a_rename(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        tree = wt / 'eval'
        git('mv', 'SPEC.md', 'impl_test.go', cwd=tree)
        git('mv', 'TASKS.md', 'other.go', cwd=tree)
        card = dispatch.find_card(self.root, 'E1')
        self.assertEqual(sorted(dispatch.off_list(wt, card)),
                         ['eval/SPEC.md', 'eval/TASKS.md', 'eval/other.go'])

    def test_off_list_reports_a_name_with_an_arrow(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go -> x.go').write_text('package eval\n')
        card = dispatch.find_card(self.root, 'E1')
        self.assertEqual(dispatch.off_list(wt, card), ['eval/impl.go -> x.go'])

    def test_off_list_reports_a_non_ascii_path(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        git('config', 'core.quotepath', 'true', cwd=wt / 'eval')
        (wt / 'eval' / 'メモ.txt').write_text('note\n')
        card = dispatch.find_card(self.root, 'E1')
        self.assertEqual(dispatch.off_list(wt, card), ['eval/メモ.txt'])

    def test_harness_failure_is_reported_once(self):
        worker = self.worker(stderr_text='error: UNKNOWN_MODEL: nope', code=2)
        code, out, err = self.invoke('card', 'E1', worker=worker)
        self.assertEqual(code, 2)
        self.assertIn(dispatch.HARNESS_LINE + '\n', out)
        self.assertEqual(out.count(dispatch.HARNESS_LINE), 1)
        self.assertEqual(self.runs(), 1)

    def test_harness_line_needs_a_nonzero_exit(self):
        worker = self.worker(stderr_text='MISSING_CREDENTIAL', code=0)
        code, out, err = self.invoke('card', 'E1', worker=worker)
        self.assertEqual(code, 0)
        self.assertNotIn(dispatch.HARNESS_LINE, out)
        self.assertEqual(self.runs(), 1)

    def test_run_worker_never_overwrites_output(self):
        worker = self.worker(stdout_text='answer text', stderr_text='reasoning text')
        stamp = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)

        class Fixed:
            @staticmethod
            def now(tz=None):
                return stamp

        patched = mock.patch.object(dispatch, 'datetime', Fixed)
        with patched, contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                dispatch.run_worker(self.root, 'probe', self.root, ['dsh'], 'brief',
                                    read_only=False, worker=worker)
        out = self.root / 'local/agents'
        self.assertEqual(sorted(path.name for path in out.iterdir()),
                         ['20260102T030405Z-probe-2.log', '20260102T030405Z-probe-2.md',
                          '20260102T030405Z-probe.log', '20260102T030405Z-probe.md'])
        for path in out.iterdir():
            self.assertEqual(path.read_text(), 'answer text\n' if path.suffix == '.md'
                             else 'reasoning text\n')

    def test_run_worker_skips_a_taken_name(self):
        worker = self.worker()
        stamp = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        out = self.root / 'local/agents'
        out.mkdir(parents=True)
        (out / '20260102T030405Z-probe.md').write_text('taken\n')
        with mock.patch.object(dispatch, 'datetime', clock_at(stamp)), \
                contextlib.redirect_stdout(io.StringIO()):
            dispatch.run_worker(self.root, 'probe', self.root, ['dsh'], 'brief',
                                read_only=False, worker=worker)
        self.assertEqual(sorted(path.name for path in out.iterdir()),
                         ['20260102T030405Z-probe-2.log', '20260102T030405Z-probe-2.md',
                          '20260102T030405Z-probe.md'])
        self.assertEqual((out / '20260102T030405Z-probe.md').read_text(), 'taken\n')
        self.assertEqual((out / '20260102T030405Z-probe-2.md').read_text(), 'answer text\n')
        self.assertEqual((out / '20260102T030405Z-probe-2.log').read_text(), 'reasoning text\n')

    def test_ambiguity_reviews_the_cards_that_are_not_done(self):
        code, out, err = self.invoke('ambiguity')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        for card_id in ('L2', 'R1', 'E1', 'W1'):
            self.assertIn(f'- {card_id} (', brief)
        self.assertNotIn('L1', brief)
        self.assertIn('/data/references/', brief)
        self.assertIn(f'under `{self.root}/local/agents/`, or under '
                      f'`{self.root}/local/worktrees/` outside the worktree this brief names',
                      brief)
        self.assertIn('grep -r', brief)
        self.assertIn('Do not edit, create, or delete any file', brief)
        self.assertIn('Do not run any command that builds or tests code', brief)
        self.assertNotIn('go vet', brief)
        self.assertIn('TOTAL <n>', brief)
        argv = self.recorded('argv.txt')
        self.assertEqual(argv[0], '--read-only')
        self.assertEqual(argv[1], str(self.root))
        self.assertEqual(argv[2:], dispatch.WORKER_ROUTE)
        self.assertEqual(self.record_text('gowork.txt').strip(), '')
        answer, log = self.only_answer()
        self.assertTrue(answer.name.endswith('-ambiguity-all.md'))

    def test_ambiguity_with_ids_reviews_a_done_card(self):
        code, out, err = self.invoke('ambiguity', 'L1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn('- L1 (llmgw): Fake server', brief)
        self.assertNotIn('- L2 (', brief)
        answer, log = self.only_answer()
        self.assertTrue(answer.name.endswith('-ambiguity-L1.md'))

    def test_ambiguity_without_cards(self):
        for repo in GO_REPOS:
            tasks = self.root / repo / 'TASKS.md'
            tasks.write_text('\n'.join(
                line if not line.startswith('Status: ') else 'Status: done'
                for line in tasks.read_text().splitlines()) + '\n')
        code, out, err = self.invoke('ambiguity')
        self.assertEqual(code, 2)
        self.assertEqual(err, 'dispatch: no cards to review\n')
        self.assertEqual(self.runs(), 0)

    def test_ambiguity_lists_contract_files(self):
        (self.root / 'eval' / 'contract.go').write_text('// CONTRACT: do not edit\npackage eval\n')
        self.invoke('ambiguity')
        brief = self.record_text('stdin.txt')
        self.assertIn(f'`{self.root}/eval/contract.go`', brief)
        self.assertNotIn('contract files none', brief)

    def test_review(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        tree = wt / 'eval'
        (tree / 'impl.go').write_text('package eval\n\n// changed\n')
        commit(tree, 'implement E1')
        (tree / 'notes.txt').write_text('note\n')
        card = dispatch.find_card(self.root, 'E1')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn(card.text, brief)
        self.assertIn('Diff of each repository worktree since it left main '
                      "(`git diff $(git merge-base main HEAD)`: the card's commits and "
                      'uncommitted changes), headed by `### <repo>`:', brief)
        self.assertIn('### eval\n', brief)
        self.assertIn('diff --git a/impl.go b/impl.go', brief)
        self.assertIn('+// changed', brief)
        self.assertIn(f'- {tree}/notes.txt', brief)
        self.assertIn('exited 0', brief)
        self.assertIn(f'GOWORK={wt}/go.work make -C {wt}/eval check', brief)
        self.assertNotIn('You may run', brief)
        self.assertIn('gate exit 0\n', out)
        argv = self.recorded('argv.txt')
        self.assertEqual(argv[0], '--read-only')
        self.assertEqual(argv[1], str(tree))
        self.assertEqual(argv[2:], dispatch.REVIEW_ROUTE)
        self.assertEqual(self.record_text('gowork.txt').strip(), '')
        answer, log = self.only_answer()
        self.assertTrue(answer.name.endswith('-review-E1.md'))

    def test_review_lists_untracked_files_as_absolute_paths(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'notes.txt').write_text('note\n')
        (wt / 'learn' / 'other.txt').write_text('other\n')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn(f'the files in `{wt}` that the diff touches (any repository there)', brief)
        self.assertIn(f'- {wt}/eval/notes.txt', brief)
        self.assertIn(f'- {wt}/learn/other.txt', brief)

    def test_review_lists_a_non_ascii_untracked_file(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'メモ.txt').write_text('note\n')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        self.assertIn(f'- {wt}/eval/メモ.txt\n', self.record_text('stdin.txt'))

    def test_review_runs_the_gate_before_the_reviewer_even_when_it_fails(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        tree = wt / 'eval'
        (tree / 'Makefile').write_text('check:\n\t@printf "gate-marker\\n"\n\t@exit 3\n')
        (tree / 'impl.go').write_text('package eval\n')
        commit(tree, 'implement E1')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        argv = self.recorded('argv.txt')
        self.assertEqual(argv[0], '--read-only')
        self.assertEqual(argv[1], str(tree))
        self.assertEqual(argv[2:], dispatch.REVIEW_ROUTE)
        brief = self.record_text('stdin.txt')
        self.assertIn('exited 2', brief)
        self.assertIn('gate-marker', brief)
        self.assertIn('gate exit 2\n', out)

    def test_review_main(self):
        tree = self.root / 'rag'
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n')
        (tree / 'other.go').write_text('package rag\n')
        commit(tree, 'add contract and other')
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n\n// changed\n')
        (tree / 'other.go').write_text('package rag\n\n// unrelated\n')
        (tree / 'new.txt').write_text('new file\n')
        card = dispatch.find_card(self.root, 'R1')
        worker = self.worker(code=4)
        code, out, err = self.invoke('review', 'R1', '--main', 'contract.go', 'new.txt',
                                     worker=worker)
        self.assertEqual(code, 4)
        brief = self.record_text('stdin.txt')
        self.assertIn(card.text, brief)
        self.assertIn('diff --git a/contract.go b/contract.go', brief)
        self.assertIn('+// changed', brief)
        self.assertIn(f'- {self.root}/rag/new.txt', brief)
        self.assertIn('git diff HEAD', brief)
        self.assertIn('TOTAL <n>', brief)
        self.assertIn(never_text(self.root), brief)
        self.assertIn(f'make -C {self.root}/rag check', brief)
        self.assertIn('exited 0', brief)
        self.assertNotIn('You may run', brief)
        self.assertIn('gate exit 0\n', out)
        self.assertNotIn('other.go', brief)
        self.assertNotIn('+// unrelated', brief)
        argv = self.recorded('argv.txt')
        self.assertEqual(argv[0], '--read-only')
        self.assertEqual(argv[1], str(tree))
        self.assertEqual(argv[2:], dispatch.REVIEW_ROUTE)
        self.assertEqual(self.record_text('gowork.txt').strip(), str(self.root / 'go.work'))
        answer, log = self.only_answer()
        self.assertTrue(answer.name.endswith('-review-R1-main.md'))
        self.assertFalse((self.root / 'local/worktrees/R1').exists())

    def test_review_shows_every_changed_repository(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n\n// changed\n')
        commit(wt / 'eval', 'implement E1')
        (wt / 'rag' / 'ingest.go').write_text('package rag\n\n// rag change\n')
        commit(wt / 'rag', 'tweak rag')
        (wt / 'learn' / 'note.txt').write_text('note\n')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn('Diff of each repository worktree since it left main '
                      "(`git diff $(git merge-base main HEAD)`: the card's commits and "
                      'uncommitted changes), headed by `### <repo>`:', brief)
        self.assertIn('### eval\n', brief)
        self.assertIn('### rag\n', brief)
        self.assertLess(brief.index('### eval\n'), brief.index('### rag\n'))
        self.assertIn('+// rag change', brief)
        self.assertNotIn('### learn', brief)
        self.assertIn(f'- {wt}/learn/note.txt', brief)

    def test_review_ignores_commits_main_gained_after_the_dispatch(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'SPEC.md').write_text('# spec\n\nworktree-change\n')
        (self.root / 'rag' / 'SPEC.md').write_text('# spec\n\nrag-main-moved\n')
        commit(self.root / 'rag', 'move rag main')
        (self.root / 'eval' / 'moved.md').write_text('eval-main-moved\n')
        commit(self.root / 'eval', 'move eval main')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn('### eval\n', brief)
        self.assertIn('+worktree-change', brief)
        self.assertNotIn('rag-main-moved', brief)
        self.assertNotIn('eval-main-moved', brief)
        self.assertNotIn('### rag', brief)

    def test_review_shows_committed_card_changes(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'rag' / 'ingest.go').write_text('package rag\n\n// rag change\n')
        commit(wt / 'rag', 'tweak rag')
        (wt / 'eval' / 'SPEC.md').write_text('# spec\n\nworktree-change\n')
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn('### eval\n', brief)
        self.assertIn('### rag\n', brief)
        self.assertIn('+worktree-change', brief)
        self.assertIn('+// rag change', brief)

    def test_review_main_names_the_users(self):
        tree = self.root / 'rag'
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n')
        commit(tree, 'add contract')
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n\n// changed\n')
        code, out, err = self.invoke('review', 'R1', '--main', 'contract.go')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn(f'`{self.root}/rag`, `{self.root}/eval`, `{self.root}/learn`, '
                      f'`{self.root}/adopt`, `{self.root}/server`, `{self.root}/web`', brief)
        self.assertIn(f'GOWORK={self.root}/go.work make -C {self.root}/rag check && '
                      f'GOWORK={self.root}/go.work make -C {self.root}/eval check && '
                      f'GOWORK={self.root}/go.work make -C {self.root}/learn check && '
                      f'GOWORK={self.root}/go.work make -C {self.root}/adopt check && '
                      f'GOWORK={self.root}/go.work make -C {self.root}/server check && '
                      f'GOWORK={self.root}/go.work make -C {self.root}/web check', brief)

    def test_review_main_without_changes(self):
        code, out, err = self.invoke('review', 'R1', '--main', 'SPEC.md')
        self.assertEqual(code, 2)
        self.assertEqual(err, 'dispatch: no uncommitted changes in SPEC.md of rag\n')
        self.assertEqual(self.runs(), 0)

    def test_review_main_pins_gowork(self):
        tree = self.root / 'rag'
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n')
        commit(tree, 'add contract')
        (tree / 'contract.go').write_text('// CONTRACT: do not edit\npackage rag\n\n// changed\n')
        code, out, err = self.invoke('review', 'R1', '--main', 'contract.go')
        self.assertEqual(code, 0)
        brief = self.record_text('stdin.txt')
        self.assertIn(f'GOWORK={self.root}/go.work make -C {self.root}/rag check', brief)
        self.assertIn(f'GOWORK={self.root}/go.work make -C {self.root}/server check', brief)
        self.assertEqual(self.record_text('gowork.txt').strip(), str(self.root / 'go.work'))

    def test_review_without_main_still_needs_a_worktree(self):
        code, out, err = self.invoke('review', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('no worktree', err)
        self.assertEqual(self.runs(), 0)

    def test_land(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        tree = wt / 'eval'
        (tree / 'impl.go').write_text('package eval\n')
        commit(tree, 'implement E1')
        head = git('rev-parse', 'HEAD', cwd=tree).strip()
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 0)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), head)
        self.assertFalse(wt.exists())
        for repo in GO_REPOS:
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
            self.assertEqual(len(git('worktree', 'list', cwd=self.root / repo).splitlines()), 1)
        self.assertIn('landed eval ', out)

    def test_land_refuses_when_main_moved(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement E1')
        card_head = git('rev-parse', 'HEAD', cwd=wt / 'eval').strip()
        (self.root / 'eval' / 'moved.go').write_text('package eval\n')
        commit(self.root / 'eval', 'move main')
        eval_main = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('eval: main has moved since the dispatch', err)
        self.assertIn('then land again.', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), eval_main)
        self.assertEqual(git('rev-parse', 'card/E1', cwd=self.root / 'eval').strip(), card_head)
        for repo in EVAL_REPOS:
            self.assertTrue((wt / repo).is_dir())
            self.assertIn('card/E1', git('branch', '--list', 'card/E1', cwd=self.root / repo))

    def test_land_refuses_a_dirty_worktree(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'rag' / 'dirty.txt').write_text('dirty\n')
        eval_main = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('rag: worktree has uncommitted changes; commit or discard them first', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), eval_main)
        for repo in EVAL_REPOS:
            self.assertTrue((wt / repo).is_dir())
            self.assertIn('card/E1', git('branch', '--list', 'card/E1', cwd=self.root / repo))

    def test_land_skips_a_repository_without_commits(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement E1')
        head = git('rev-parse', 'HEAD', cwd=wt / 'eval').strip()
        (self.root / 'learn' / 'moved.go').write_text('package learn\n')
        commit(self.root / 'learn', 'move learn main')
        learn_main = git('rev-parse', 'main', cwd=self.root / 'learn').strip()
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 0)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), head)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'learn').strip(), learn_main)
        self.assertFalse(wt.exists())
        for repo in GO_REPOS:
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
            self.assertEqual(len(git('worktree', 'list', cwd=self.root / repo).splitlines()), 1)
        self.assertIn('unchanged learn\n', out)
        self.assertIn('landed eval ', out)

    def test_land_warns_when_a_user_moved(self):
        wt = self.root / 'local/worktrees/R1'
        self.invoke('card', 'R1', '--no-worker')
        (wt / 'rag' / 'ingest.go').write_text('package rag\n')
        commit(wt / 'rag', 'implement R1')
        head = git('rev-parse', 'HEAD', cwd=wt / 'rag').strip()
        for repo in ('eval', 'llmgw'):
            (self.root / repo / 'moved.go').write_text(f'package {repo}\n')
            commit(self.root / repo, 'move main')
        code, out, err = self.invoke('land', 'R1')
        self.assertEqual(code, 0)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'rag').strip(), head)
        self.assertIn('warning: eval main has moved since the dispatch, so the full gate ran '
                      'against an older eval\n', out)
        self.assertNotIn('llmgw main has moved', out)

    def test_land_refuses_when_main_moved_in_one_repository_but_another_is_fine(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement E1')
        card_head = git('rev-parse', 'HEAD', cwd=wt / 'eval').strip()
        moved = {}
        for repo in ('eval', 'learn'):
            (self.root / repo / 'moved.go').write_text(f'package {repo}\n')
            commit(self.root / repo, 'move main')
            moved[repo] = git('rev-parse', 'main', cwd=self.root / repo).strip()
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('eval: main has moved since the dispatch', err)
        for repo, head in moved.items():
            self.assertEqual(git('rev-parse', 'main', cwd=self.root / repo).strip(), head)
        self.assertEqual(git('rev-parse', 'card/E1', cwd=self.root / 'eval').strip(), card_head)
        for repo in EVAL_REPOS:
            self.assertTrue((wt / repo).is_dir())
            self.assertIn('card/E1', git('branch', '--list', 'card/E1', cwd=self.root / repo))

    def test_land_needs_a_worktree(self):
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('no worktree', err)

    def test_land_rolls_back_when_a_fast_forward_fails(self):
        wt = self.root / 'local/worktrees/R1'
        self.invoke('card', 'R1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement R1 in eval')
        (wt / 'rag' / 'ingest.go').write_text('package rag\n\n// card\n')
        commit(wt / 'rag', 'implement R1 in rag')
        mains = {repo: git('rev-parse', 'main', cwd=self.root / repo).strip() for repo in GO_REPOS}
        (self.root / 'rag' / 'ingest.go').write_text('lead edit\n')
        code, out, err = self.invoke('land', 'R1')
        self.assertEqual(code, 2)
        self.assertIn('rag: the fast-forward failed: ', err)
        self.assertIn('Nothing was landed; fix the main checkout and land again.', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), mains['eval'])
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'rag').strip(), mains['rag'])
        self.assertEqual((self.root / 'rag' / 'ingest.go').read_text(), 'lead edit\n')
        for repo in GO_REPOS:
            self.assertTrue((wt / repo).is_dir())
            self.assertIn('card/R1', git('branch', '--list', 'card/R1', cwd=self.root / repo))

    def test_land_rollback_keeps_another_commit(self):
        wt = self.root / 'local/worktrees/R1'
        self.invoke('card', 'R1', '--no-worker')
        for repo in ('eval', 'learn'):
            (wt / repo / 'impl.go').write_text(f'package {repo}\n\n// card\n')
            commit(wt / repo, f'implement R1 in {repo}')
        before = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
        after = git('rev-parse', 'card/R1', cwd=self.root / 'eval').strip()
        (self.root / 'learn' / 'impl.go').write_text('lead edit\n')
        moved = {}
        real_git = dispatch.git

        def patched(*args, cwd=None, allow_failure=False):
            done = real_git(*args, cwd=cwd, allow_failure=allow_failure)
            if args and args[0] == 'merge' and done.returncode and cwd == self.root / 'learn':
                (self.root / 'eval' / 'other.go').write_text('package eval\n')
                commit(self.root / 'eval', 'another agent lands')
                moved['now'] = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
            return done

        with mock.patch.object(dispatch, 'git', patched):
            code, out, err = self.invoke('land', 'R1')
        now = moved['now']
        self.assertEqual(code, 2)
        self.assertIn('learn: the fast-forward failed: ', err)
        self.assertIn('The rollback stopped at eval: main moved in another checkout during the '
                      'land. Check each repository:', err)
        self.assertIn(f'\n  eval before {before} after {after} now {now} not rolled back\n', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), now)
        self.assertEqual((self.root / 'eval' / 'other.go').read_text(), 'package eval\n')
        for repo in GO_REPOS:
            self.assertTrue((wt / repo).is_dir())
            self.assertIn('card/R1', git('branch', '--list', 'card/R1', cwd=self.root / repo))

    def test_land_rollback_keeps_staged_changes(self):
        wt = self.root / 'local/worktrees/R1'
        self.invoke('card', 'R1', '--no-worker')
        for repo in ('eval', 'learn'):
            (wt / repo / 'impl.go').write_text(f'package {repo}\n\n// card\n')
            commit(wt / repo, f'implement R1 in {repo}')
        before = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
        (self.root / 'learn' / 'impl.go').write_text('lead edit\n')
        real_git = dispatch.git

        def patched(*args, cwd=None, allow_failure=False):
            done = real_git(*args, cwd=cwd, allow_failure=allow_failure)
            if args and args[0] == 'merge' and done.returncode and cwd == self.root / 'learn':
                (self.root / 'eval' / 'SPEC.md').write_text('# spec\n\n// staged\n')
                git('add', 'SPEC.md', cwd=self.root / 'eval')
            return done

        with mock.patch.object(dispatch, 'git', patched):
            code, out, err = self.invoke('land', 'R1')
        self.assertEqual(code, 2)
        self.assertIn('Nothing was landed; fix the main checkout and land again.', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), before)
        self.assertFalse((self.root / 'eval' / 'impl.go').exists())
        staged = git('diff', '--cached', cwd=self.root / 'eval')
        self.assertIn('SPEC.md', staged)
        self.assertIn('+// staged', staged)

    def test_land_rollback_stops_when_the_checkout_left_main(self):
        wt = self.root / 'local/worktrees/R1'
        self.invoke('card', 'R1', '--no-worker')
        for repo in ('eval', 'learn'):
            (wt / repo / 'impl.go').write_text(f'package {repo}\n\n// card\n')
            commit(wt / repo, f'implement R1 in {repo}')
        after = git('rev-parse', 'card/R1', cwd=self.root / 'eval').strip()
        (self.root / 'learn' / 'impl.go').write_text('lead edit\n')
        real_git = dispatch.git

        def patched(*args, cwd=None, allow_failure=False):
            done = real_git(*args, cwd=cwd, allow_failure=allow_failure)
            if args and args[0] == 'merge' and done.returncode and cwd == self.root / 'learn':
                git('checkout', '-b', 'other', cwd=self.root / 'eval')
            return done

        with mock.patch.object(dispatch, 'git', patched):
            code, out, err = self.invoke('land', 'R1')
        self.assertEqual(code, 2)
        self.assertIn('The rollback stopped at eval: the main checkout is no longer on main.', err)
        self.assertIn('not rolled back', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), after)
        self.assertEqual(git('rev-parse', 'other', cwd=self.root / 'eval').strip(), after)

    def test_land_rollback_reports_partial_progress(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        repos = ('eval', 'learn', 'llmgw')
        for repo in repos:
            (wt / repo / 'impl.go').write_text(f'package {repo}\n')
            commit(wt / repo, f'implement E1 in {repo}')
        before = {repo: git('rev-parse', 'main', cwd=self.root / repo).strip() for repo in repos}
        after = {repo: git('rev-parse', 'card/E1', cwd=self.root / repo).strip() for repo in repos}
        (self.root / 'llmgw' / 'impl.go').write_text('lead edit\n')
        moved = {}
        real_git = dispatch.git

        def patched(*args, cwd=None, allow_failure=False):
            done = real_git(*args, cwd=cwd, allow_failure=allow_failure)
            if args and args[0] == 'merge' and done.returncode and cwd == self.root / 'llmgw':
                (self.root / 'eval' / 'other.go').write_text('package eval\n')
                commit(self.root / 'eval', 'another agent lands')
                moved['eval'] = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
            return done

        with mock.patch.object(dispatch, 'git', patched):
            code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('The rollback stopped at eval: main moved in another checkout during the '
                      'land.', err)
        self.assertIn(f'  eval before {before["eval"]} after {after["eval"]} '
                      f'now {moved["eval"]} not rolled back', err)
        self.assertIn(f'  learn before {before["learn"]} after {after["learn"]} '
                      f'now {before["learn"]} rolled back', err)
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'learn').strip(),
                         before['learn'])
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'llmgw').strip(),
                         before['llmgw'])

    def test_land_does_not_overwrite_an_ignored_file(self):
        (self.root / 'eval' / '.gitignore').write_text('ignored.txt\n')
        commit(self.root / 'eval', 'ignore ignored.txt')
        (self.root / 'eval' / 'ignored.txt').write_text('keep\n')
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        eval_main = git('rev-parse', 'main', cwd=self.root / 'eval').strip()
        (wt / 'eval' / 'ignored.txt').write_text('tracked now\n')
        git('add', '-f', 'ignored.txt', cwd=wt / 'eval')
        commit(wt / 'eval', 'track the ignored path')
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('eval: the fast-forward failed: ', err)
        self.assertIn('Nothing was landed; fix the main checkout and land again.', err)
        self.assertEqual((self.root / 'eval' / 'ignored.txt').read_text(), 'keep\n')
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), eval_main)

    def test_land_stops_on_a_detached_worktree(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'rag' / 'moved.go').write_text('package rag\n')
        commit(wt / 'rag', 'tweak rag')
        git('checkout', '--detach', cwd=wt / 'rag')
        mains = {repo: git('rev-parse', 'main', cwd=self.root / repo).strip() for repo in EVAL_REPOS}
        branches = {repo: git('rev-parse', 'card/E1', cwd=self.root / repo).strip()
                    for repo in EVAL_REPOS}
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 2)
        self.assertIn('rag: the worktree is not on card/E1; check out card/E1 and commit there',
                      err)
        for repo in EVAL_REPOS:
            self.assertEqual(git('rev-parse', 'main', cwd=self.root / repo).strip(), mains[repo])
            self.assertEqual(git('rev-parse', 'card/E1', cwd=self.root / repo).strip(),
                             branches[repo])
            self.assertTrue((wt / repo).is_dir())

    def test_land_ignores_the_branch_of_a_repository_without_commits(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement E1')
        head = git('rev-parse', 'HEAD', cwd=wt / 'eval').strip()
        git('checkout', '--orphan', 'scratch', cwd=self.root / 'learn')
        commit(self.root / 'learn', 'scratch root')
        code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), head)
        self.assertFalse(wt.exists())
        for repo in GO_REPOS:
            self.assertEqual(git('branch', '--list', 'card/E1', cwd=self.root / repo).strip(), '')
            self.assertEqual(len(git('worktree', 'list', cwd=self.root / repo).splitlines()), 1)
        self.assertIn('unchanged learn\n', out)
        self.assertIn('landed eval ', out)

    def test_land_keeps_a_branch_that_gained_commits(self):
        wt = self.root / 'local/worktrees/E1'
        self.invoke('card', 'E1', '--no-worker')
        (wt / 'eval' / 'impl.go').write_text('package eval\n')
        commit(wt / 'eval', 'implement E1')
        head = git('rev-parse', 'HEAD', cwd=wt / 'eval').strip()
        late = {}
        real_git = dispatch.git

        def patched(*args, cwd=None, allow_failure=False):
            done = real_git(*args, cwd=cwd, allow_failure=allow_failure)
            if (args[:2] == ('worktree', 'remove') and not done.returncode
                    and cwd == self.root / 'learn'):
                tree = git('rev-parse', 'card/E1^{tree}', cwd=self.root / 'learn').strip()
                parent = git('rev-parse', 'card/E1', cwd=self.root / 'learn').strip()
                fresh = git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit-tree', tree,
                            '-p', parent, '-m', 'late commit', cwd=self.root / 'learn').strip()
                git('update-ref', 'refs/heads/card/E1', fresh, parent, cwd=self.root / 'learn')
                late['learn'] = fresh
            return done

        with mock.patch.object(dispatch, 'git', patched):
            code, out, err = self.invoke('land', 'E1')
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        self.assertEqual(git('rev-parse', 'main', cwd=self.root / 'eval').strip(), head)
        self.assertIn('landed eval ', out)
        self.assertIn('kept learn card/E1: it gained commits during the land; '
                      'land again or delete it by hand\n', out)
        self.assertEqual(git('rev-parse', 'card/E1', cwd=self.root / 'learn').strip(),
                         late['learn'])
        self.assertFalse(wt.exists())


if __name__ == '__main__':
    unittest.main()
