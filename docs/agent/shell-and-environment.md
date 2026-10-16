# Shell and environment

Purpose: Shell and platform traps that make an agent produce silently wrong results, with the fixes that work on Windows (Git Bash and PowerShell side by side), macOS and Linux.
Read when: writing commit messages or scripts, running commands for the agent or handing them to a teammate, working on Windows, or when output looks subtly wrong.

Most items here fail silently: the command succeeds and the result is wrong. That is why they are worth knowing in advance.

## Know which shell you are in

- **Match the syntax to the shell actually running the command.** Heredocs are bash; PowerShell uses here-strings (`@'...'@`), and the closing `'@` must be at column 0. Agent tools on Windows often offer both shells, so don't carry habits from one into the other.
  ```bash
  # bash: quoted delimiter = no expansion inside
  cat > notes.txt <<'EOF'
  Price is $5, run `make`.
  EOF
  ```
  ```powershell
  # PowerShell: single-quoted here-string = literal, closing '@ at column 0
  $msg = @'
  Price is $5, run `make`.
  '@
  ```
- **Don't assume the agent's shell sees the same machine state as the human's.** Agent shells can run sandboxed, in a different user profile, with packaged-app path redirection, without the human's aliases or TTY wrappers, or with a PATH that predates a recent install (on Windows, PATH isn't refreshed for running processes after `winget install`). If the two disagree about whether a file or tool exists, believe the human's shell. Why: `ls` in the agent's environment can give convincing but wrong evidence, and the agent then reports a tool as installed or missing when it isn't.
- **Don't rely on shell state carrying over between agent tool calls.** Some harnesses keep the working directory between calls, some reset it; environment variables usually don't persist. Use absolute paths and `git -C <path> ...` instead of `cd <path> && ...`. Why: a `cd` that carries over (or doesn't) puts commits in the wrong checkout.
- **Commands handed to humans carry their own context:** which shell, which account, which folder, with `cd` as the first line of the block. See [Collaboration](collaboration.md).

## Commit messages and quoting

- **Never put backticks inside a double-quoted `git commit -m "..."` in bash.** Bash runs them as command substitution and silently deletes the words (or runs a command). Use single quotes, or no backticks.
  ```bash
  git commit -m 'fix: handle `null` ids in export' -- src/export.ts
  ```
- **Get commit messages right the first time.** Fixing pushed history needs a force push, which the team should treat as forbidden, so a mangled message stays forever.
- **If a hook needs to read the commit message, pass it as a literal `-m`.** Hooks that inspect the command before it runs (version guards, conventional-commit checks) usually can't parse a heredoc, `-F -` or `$(cat msg.txt)`. Use `-m 'subject' -m 'body paragraph'` for multi-line messages. See [Git workflow](git-workflow.md) and [Versioning](versioning.md).
- **Keep helper scripts in files rather than inline in a command.** Why: guards that scan command text also fire on commands that merely mention `git commit` or `rm`.

## Escape sequences and invisible bytes

- **Write code that contains backslash escapes with the file-edit tool, not through a shell heredoc.** Depending on the tool layer, `\b`, `\n`, `\t` or `\0` in a heredoc body can arrive in the file as raw control bytes, even with a quoted delimiter. Why: one NUL byte makes git treat the whole file as binary, which hides it from diff and code review, so the change can land without anyone reading it.
- **Verify bytes, not appearances.** Control characters are invisible in `cat` and `grep` output. Check with Python:
  ```bash
  python -c "import sys; d=open(sys.argv[1],'rb').read(); print('NUL:', d.count(bytes([0])), 'ctrl:', sorted({b for b in d if b < 9 or 13 < b < 32}))" path/to/file
  ```
  For a single string literal in code, print its `repr()` or inspect the compiled constants, not the source text.
- **Watch for `Bin` in `git diff --stat`.** A text file showing as binary has control bytes in it.
- **In prose and docs, describe control characters in words** ("a NUL byte", "a literal backslash-n") rather than typing the escape, which a later tool may convert.

## Windows specifics

- **Git Bash (MSYS) rewrites arguments that look like `/flag` into Windows paths.** `tasklist /FI "PID eq 1234"` turns `/FI` into `C:/Program Files/Git/FI`. Run such Windows tools from PowerShell, or disable conversion for one command:
  ```bash
  MSYS_NO_PATHCONV=1 tasklist /FI "PID eq 1234"
  ```
  To get the exit code of a GUI executable, use PowerShell's `Start-Process <exe> -Wait -PassThru` and read `.ExitCode`.
- **Never write `>nul` in Git Bash.** It creates a real file named `nul` that is hard to delete. Use `>/dev/null` in bash and `> $null` (or `| Out-Null`) in PowerShell.
- **Force UTF-8 for Python on a Windows console.** Python writes the legacy code page by default and crashes or garbles output on non-ASCII text. Set it inline instead of switching to temp files:
  ```bash
  PYTHONIOENCODING=utf-8 python script.py      # Git Bash
  python -X utf8 script.py                     # any shell
  ```
  In scripts you own, call `sys.stdout.reconfigure(encoding="utf-8")` at startup.
- **`python` vs `python3`.** On Windows, `python3` is often the Microsoft Store stub that opens the Store instead of running; macOS ships only `python3`. In scripts and hooks, pick the first interpreter that actually runs:
  ```bash
  for c in python python3; do "$c" -c 'import sys' 2>/dev/null && PY=$c && break; done
  "$PY" script.py
  ```
- **Force LF line endings for shell scripts.** CRLF makes bash fail with `bad interpreter` or `$'\r': command not found`. Add to `.gitattributes`:
  ```
  *.sh text eol=lf
  ```
  and set the executable bit in git itself: `git update-index --chmod=+x scripts/deploy.sh`.
- **Long paths break worktree removal.** `git worktree remove` can fail with "Filename too long" on deep `node_modules` trees; the worktree is usually unregistered anyway. Run `git worktree prune`, then delete the leftover folder separately. `git config --global core.longpaths true` prevents most of these errors.
- **From a subprocess on Windows, call Git Bash by its full path.** A bare `bash` may resolve to WSL, which has a different filesystem view and different tools.
- **A "permission denied" when binding a port can mean the port is reserved by Windows.** List excluded ranges with `netsh interface ipv4 show excludedportrange protocol=tcp` and pick a port outside them.

## Processes and ports

- **Kill your own background processes by matching their command line, never by interpreter name.** Why: killing every `python`, `node` or `bash` process takes down teammates' tools, editors and other agent sessions on the same machine.
  ```bash
  pkill -f 'dev_server.py --port 3999'
  ```
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object CommandLine -like '*dev_server.py --port 3999*' |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
  ```
  Make sure the pattern can't also match the shell running the kill (for example a `bash -c "..."` wrapper whose own command line contains the pattern).
- **Smoke-test a local server on a non-default port with a temporary database,** and confirm your instance actually bound (its listening log line, no `EADDRINUSE`) before sending any request that changes data. Treat any database you didn't create in this session as holding real data. Why: an orphaned server still holding the default port can answer the smoke test instead of yours, and the test then changes rows in a database that holds real data.
- **Write reserved ports down in the project instructions and avoid them** (a local Postgres on 5432, a tool's fixed port). Make the dev server honour the `PORT` environment variable, so preview tools can assign one. Why: otherwise the dev server grabs its default port and the preview shows nothing, or another project's server.
- **Put timeouts on every network call inside a loop:**
  ```bash
  for i in $(seq 1 30); do curl -s -m 2 http://127.0.0.1:3999/health && break; sleep 1; done
  ```
- **For "tell me when CI finishes", use a blocking command in a background shell,** such as `gh run watch <run-id> --exit-status` or `gh pr checks <pr> --watch`, not a polling monitor that can fail silently. Never swallow CLI errors into empty defaults (`|| echo "[]"`). Why: an empty default looks exactly like "nothing to report".
- **Don't run code with unknown side effects locally,** such as a script that imports the full application runtime or monkeypatches globals. Verify with static checks plus logs from a branch or preview deploy. Why: such code can freeze the machine or change local state in ways that are hard to undo.

## Interactive commands hang the agent

The agent cannot type into a prompt. A command that asks a question, opens an editor or pipes into a pager waits forever, and the tool call times out.

- **Pre-answer prompts with flags:** `--yes`, `--non-interactive`, `--no-input`, `CI=1`, `git merge --no-edit`, `GIT_EDITOR=true git rebase --continue`. Avoid `-i` interactive modes (`git rebase -i`, `git add -i`) entirely.
- **Disable pagers:** `git --no-pager log`, `GIT_PAGER=cat`, `PAGER=cat`, `GH_PAGER=cat`.
- **Collect a non-secret value in chat and pipe it in with `printf '%s'`, not `echo`,** which adds a trailing newline that ends up inside the value:
  ```bash
  printf '%s' "$VALUE" | some-cli config set api-url --stdin
  ```
  Secret values never go through the agent; the human runs the command that needs them (see [Security](security.md)).
- **Watch for tools that read stdin when given no file argument,** such as `python -m json.tool`; always pass the file.
- **Swap out lint or setup scripts that launch a first-run wizard** with a non-interactive gate (the build or the typecheck).
- **Run tools headless where possible,** with flags that avoid opening dialogs or windows on a teammate's screen.

## Big output and permission-friendly commands

- **Read large JSON or log dumps with the agent's file read and search tools,** not with shell gymnastics (PowerShell `ConvertFrom-Json` chains, long `jq` pipelines) that trigger permission prompts and truncate. Send huge output to a file, then read or search the file.
- **Hide huge generated or raw files from the agent's searches** with a `.ignore` file (respected by ripgrep-based search), while keeping them in git if needed.
- **Send allowlisted commands exactly as they are allowlisted,** without a `cd ... &&` prefix or extra pipe segments; one unallowlisted segment makes the whole command prompt. Pipe output directly instead of writing a temp file and deleting it. Permission setup is covered in [Agent setup](agent-setup.md).

## The embedded browser

Agent tools with a built-in browser pane are useful but unreliable for visual checks: screenshots can hang (background tabs throttle `requestAnimationFrame`), and coordinate clicks can miss small targets while reporting success.

- **Verify through the DOM and JavaScript instead of pixels:** computed styles, element counts, text content, bounding boxes, canvas `getImageData` deltas.
- **Click by dispatching a native bubbling event** when coordinate clicks are unreliable, and re-query nodes after every re-render:
  ```js
  el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  ```
- **Test pure logic outside the browser:** bundle it for Node (`npx esbuild src/rules.ts --bundle --platform=node --format=esm --outfile=/tmp/rules.mjs`) and run it there. Keep scratch files outside `src/`, so the dev server doesn't pick them up.
- **Run `node --check` on generated JavaScript before sending it,** and execute it against a DOM stub if it renders anything. Why: one syntax error renders a silent, empty widget.
- **Expect `confirm()` and `alert()` to be suppressed** (they return false). See [Debugging](debugging.md).
- **For auth-gated UI, use a temporary unauthenticated probe page with fake data,** and delete it before committing. Revert temporary launch-config edits before committing too.
- **Say explicitly that pixels were not seen.** "Layout verified through computed styles; the visual judgement is yours." Why: a numeric check is not a design review.
