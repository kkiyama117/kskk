# Rules for card implementers

These rules apply in every repository under `/data/softwares/skk/`: the child repositories (`jisyo/`, `conformance/`, and later ones) and the parent repository's `bin/`. Read this file in full before any work. Then read the repository's `SPEC.md`, if it has one, and the one card you were given from its `TASKS.md`. The cards of the parent repository are in `bin/TASKS.md`.

## Scope

1. Do exactly one card. Do not start the next card, even if it looks easy.
2. Touch only the files the card's `Files:` line lists. If you need another file, stop and report why. A card's `Needs:` line names cards that must be committed first; if their code is missing, stop and report.
3. Do not edit a file whose first line is `// CONTRACT: do not edit`. If the contract looks wrong or incomplete, stop and report. Do not work around it.
4. Never edit `Cargo.toml`, `Cargo.lock`, `Makefile`, `rust-toolchain.toml`, `.cargo/config.toml`, or `.gitignore`. Never run `cargo add`, `cargo update`, `cargo install`, `cargo fetch`, or `cargo generate-lockfile`. Use only the dependencies already in `Cargo.toml`, which the lead owns. The build runs offline (`CARGO_NET_OFFLINE=true`); a missing crate means stop and report.
5. If the card is ambiguous, do not guess. Write the question in your report and stop.

## Data safety

6. Never open, read, list, or copy anything under `/data/references/`, under `/data/softwares/skk/local/agents/`, or under `/data/softwares/skk/local/worktrees/` outside the worktree you were given. Never read credentials (API keys, tokens, `.env` files, DSH or provider configuration).
7. Never open, read, list, copy, or pass to any tool the owner's real dictionaries or IME files: `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, `~/.skk-jisyo`, any CorvusSKK `userdict.txt`, and anything else under `~/.local/share/fcitx5/`, `~/.config/fcitx5/`, `~/.config/ibus/`, or `~/.config/nvim/`. Never write to them. Code you ship must not name these paths as defaults.
8. Search only the paths your card and brief name. Never run `grep -r`, `rg`, `find`, or another recursive search from `/data/softwares/skk`, from a worktree root, from a repository root, or from your home directory.
9. Tests write only into temporary directories: in Rust, a directory with a unique name under `std::env::temp_dir()`, or the `tempfile` crate when `Cargo.toml` lists it; in Python, `tempfile.TemporaryDirectory()`. Tests use synthetic data that the test writes itself, or files committed under the repository's `testdata/`. Tests never use the network.
10. Code you ship never prints, logs, or puts in an error message a dictionary entry, a candidate, or text the user typed. Report counts, line numbers, byte offsets, and error codes only. A test's own failure message may show the test's synthetic data.

## Rust code

11. Errors that leave a crate use the error types and codes in `SPEC.md`. Do not invent new ones. If you need one, stop and report.
12. Test behavior through the public API. Unit tests go in a `#[cfg(test)] mod tests` of the file the card lists; integration tests go in `tests/`, and only in files the card lists. Name tests exactly as the card says. Where a card shows a table, write one test function per row unless the card says to loop over the table.
13. No `unsafe` unless the card says so. No `unwrap()` or `expect()` outside tests, except where the card allows one with its reason. No global mutable state (`static mut`, a `static` with interior mutability, `lazy_static` that is written).
14. Time and randomness come from the parameters or traits the spec defines. Do not call `SystemTime::now()`, `Instant::now()`, or a random source directly in logic.
15. Comments only for a non-obvious reason. No comments that narrate steps. Keep functions under about 60 lines.
16. Run `cargo fmt` on the files you change. `make check` runs `cargo fmt --check`, `cargo clippy` with warnings as errors, and `cargo test`; all three must pass.

## Python code

17. Use the Python 3 standard library only. Tests use `unittest`. Name tests exactly as the card says.
    - In `bin/` of the parent repository, tests go in `bin/test_<module>.py`. They build every git repository they need in a `tempfile.TemporaryDirectory()` and never touch `/data/softwares/skk` itself.
    - In `conformance/`, tests go in `conformance/runner/test_<module>.py` and use only temporary directories and files under `conformance/testdata/`.
18. Tests never start a real worker, engine, or container.
    - In `bin/`, tests pass a fake worker script, as the existing tests do.
    - In `conformance/`, tests use a fake adapter under `conformance/testdata/`.

Rules for code in other languages (C, Emacs Lisp, TypeScript) are in the card that asks for it.

## Done

19. Run the gate the brief names, in the directory it names, until it exits 0: `make check` for a child repository, `python3 -m unittest discover -s bin -p 'test_*.py'` for the parent repository. The card is done only when it exits 0.
20. Do not commit. Do not create, switch, or delete branches. The lead commits.
21. Your final report has four parts: files changed; the last 20 lines of the gate's output; anything in the card you could not do; open questions.
