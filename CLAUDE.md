@AGENTS.md

## Claude Code specifics

The shared rules for every agent are in AGENTS.md (imported above). This section adds only what is specific to Claude Code.

- **Skills** live in `.claude/skills/<name>/SKILL.md`. Codex reads the same files from `.agents/skills/`. Keep the two folders identical: edit in one place, then copy.
- **Subagents** live in `.claude/agents/`. Where you can, run review agents on a different model from the one that wrote the code, because self-review confirms what the author meant, not what is there. Claude Code picks up edited agent files automatically; restart only after creating the first file in a new `.claude/agents/` folder.
- **Hooks** are registered in the committed `.claude/settings.json`, not in `settings.local.json`, so the whole team and every worktree gets them. A hook block or warning is a hard stop: fix the cause, never work around it. Edits to hooks in settings files are normally picked up automatically; if a change doesn't seem to apply, restart the session, and always pipe-test a new hook (see `hooks/README.md`).
- **Plan first** for any change that touches more than a couple of files. Agree the plan, then implement.
- **Parallel sessions:** give each session its own git worktree. Run git with `git -C <worktree>` rather than `cd` into another checkout.
- **Personal, uncommitted instructions** go in `CLAUDE.local.md` (gitignored). Keep team rules in AGENTS.md.
