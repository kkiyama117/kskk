# Issues

One file per issue: `NNNN-<slug>.md`, numbered after the highest file here.

```markdown
# NNNN: <one-line summary>

- Labels: cause:<harness|skills|project|memory|one-off>[, needs-human]
- Status: open | fixed in <commit or link> | won't fix (<reason>)
- Opened: YYYY-MM-DD by <agent>

## Symptom

What was observed, with evidence (paths, commit hashes, the gate's last lines).

## First wrong step

The earliest step that went wrong, and why.

## Fix

The change that prevents it, in which repository. A check or a script is better than one more sentence in a brief.
```

Cause labels: `cause:harness` (Claude Code, DSH, herdr, tokens, permissions), `cause:skills` (kstack or project skills, briefs), `cause:project` (project structure, rules, checks), `cause:memory` (agent memory), `cause:one-off`. Add `needs-human` when only the owner can act.
