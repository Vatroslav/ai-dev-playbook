#!/usr/bin/env bash
# Test suite for guard-rm.sh. ASK = expects the ask JSON, PASS = expects empty output.
# Run: bash hooks/test-guard-rm.sh   (optional argument: another copy of guard-rm.sh to test)
# Exit 0 = all passed; FAIL lines otherwise.
#
# Payloads are built with python json.dumps inside this file, so the delete word never appears in
# the command line you type to run the suite. If you pipe-test by hand instead, build the trigger
# string from parts (e.g. "r""m -rf build") - otherwise your own live guard fires on the test and
# the human sees a scary prompt with no context.
PY=$(command -v python || command -v python3)
H="${1:-$(dirname "$0")/guard-rm.sh}"
fail=0
pass_count=0
fail_count=0

payload() {  # payload <cwd or ""> <command>
  "$PY" -c "
import json, sys
d = {'tool_name': 'Bash', 'tool_input': {'command': sys.argv[2]}}
if sys.argv[1]:
    d['cwd'] = sys.argv[1]
print(json.dumps(d))" "$1" "$2"
}

result() {  # result <want> <got> <label> <output>
  if [ "$2" = "$1" ]; then
    echo "ok   [$1] $3"
    pass_count=$((pass_count + 1))
  else
    echo "FAIL [want $1, got $2] $3"
    [ -n "$4" ] && echo "     $4"
    fail=1
    fail_count=$((fail_count + 1))
  fi
}

checkc() {  # checkc <ASK|PASS> <cwd> <command>
  local out got=PASS
  out=$(payload "$2" "$3" | bash "$H")
  [ -n "$out" ] && got=ASK
  result "$1" "$got" "$3" "$out"
}

check() { checkc "$1" "" "$2"; }

# The base cases must not depend on which repo you run the suite from: switch the git-undo rule
# off here and test it separately in a throwaway repo below.
export GUARD_RM_GIT_UNDO=0

# --- false positives (PASS) ---
check PASS 'grep -n -i "rm" docs/notes.md | head -40'
check PASS 'cat ~/.claude/settings.json; echo ---; grep -n -i "rm" file.md'
check PASS 'echo rm'
check PASS 'git rm --cached foo.txt'
check PASS 'diff ~/.claude/hooks/guard-rm.sh /tmp/x'
check PASS 'Get-ChildItem -Recurse'
check PASS 'ls -la | grep del'
check PASS 'python -c "print(1)" && rd_something'
# --- temp targets (PASS) ---
check PASS 'rm tmp.py'
check PASS 'rm -f ./tmp_check.py'
check PASS 'rm -rf tmp_build'
check PASS 'rm -rf tmp/'
check PASS 'rm tmp/*'
check PASS 'rm -f out.tmp data.temp'
check PASS 'rm -f /tmp/example-flag'
check PASS 'rm -rf /tmp/foo_bar'
check PASS 'rm -f "$TMPDIR/x.json"'
check PASS 'rm -f ${TEMP}/x.json'
check PASS 'rm -f temp-out.json tmp-1.txt'
check PASS 'rm -f report_tmp.csv'
check PASS 'rm tmp.py 2>/dev/null'
check PASS 'rm -f tmp.py > log.txt'
check PASS 'rm -rf /var/folders/ab/cd1234/T/scratch'
check PASS 'Remove-Item -Recurse -Force tmp_build'
check PASS 'Remove-Item -Path tmp.py -ErrorAction SilentlyContinue'
check PASS 'Remove-Item D:\Users\dev\AppData\Local\Temp\x.json'
check PASS 'del tmp.py'
check PASS 'Remove-Item "$env:TEMP\foo.txt"'
check PASS 'del %TEMP%\foo.txt'
check PASS 'Remove-Item tmp.py,temp.py'
check PASS 'find . -name "*.tmp" -delete'
check PASS 'find . -name "tmp_*" -exec rm {} \;'
# --- real deletes (ASK) ---
check ASK 'rm -rf build/'
check ASK 'rm foo.py'
check ASK 'rm -rf /tmp'
check ASK 'rm -rf /var/folders/ab/cd1234/T'
check ASK 'rm -rf ~'
check ASK 'rm -rf .'
check ASK 'rm -rf *'
check ASK 'rm -rf /'
check ASK 'rm'
check ASK 'rm tmp.py real.py'
check ASK 'rm -f "$f"'
check ASK 'rm template.md'
check ASK 'rm temporary.txt'
check ASK 'ls | xargs rm -f'
check ASK 'cd foo && rm -rf dist'
check ASK 'echo hi; rm x.txt'
check ASK 'sudo rm -rf /var/lib/foo'
check ASK 'Remove-Item -Recurse -Force node_modules'
check ASK 'Remove-Item -Path src\main.py'
check ASK 'del *.py'
check ASK 'rd /s build'
check ASK 'ri foo.txt'
check ASK 'erase foo.txt'
check ASK 'Remove-Item D:\Users\dev\AppData\Local\Temp'
check ASK 'find . -name "*.pyc" -delete'
check ASK 'find src -exec rm {} \;'
check ASK 'for f in *.log; do rm "$f"; done'
check ASK 'x=$(rm foo)'
check ASK 'rm -- -weird'
# --- .NET method deletes ---
check ASK '[IO.File]::Delete("D:\Users\dev\x.txt")'
check ASK '[IO.Directory]::Delete("build", $true)'
check ASK '[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($f, "OnlyErrorDialogs", "SendToRecycleBin")'
check ASK '(Get-Item foo.txt).Delete()'
check ASK '$x.Delete()'
check PASS '[IO.File]::Delete("/tmp/x")'
check PASS '$list.Remove(1)'
# --- nested shell / eval ---
check ASK 'bash -c "rm -rf build"'
check ASK 'cmd /c del build.txt'
check ASK 'powershell -Command "Remove-Item -Recurse dist"'
check ASK "eval 'rm -rf build'"
check PASS 'bash -c "rm -rf tmp_x"'
check PASS 'eval "$(ssh-agent -s)"'
check PASS 'grep -c "rm" file.md'
# --- multi-line ---
check ASK $'echo a\nrm -rf build\necho b'
check PASS $'echo a\nrm -rf tmp_x\necho b'
# --- heredoc: a body consumed by an interpreter/tool is not shell ---
check PASS $'cd x && PYTHONIOENCODING=utf-8 python - <<\'EOF\'\nrows.append({\n    "rd": row.get("rd"), "rm": row.get("rm"),\n})\nEOF'
check PASS $'python - <<\'EOF\'\nd = {"a": 1}\ndel d["a"]\nEOF'
check PASS $'python - <<-EOF\n\tdel x\n\tEOF'
check PASS $'git commit -F- <<\'EOF\'\nrm -rf build no longer fires\nEOF'
check PASS $'git commit -m "$(cat <<\'EOF\'\nrm -rf build was removed\nEOF\n)"'
check PASS $'cat > notes.md <<\'EOF\'\nrm -rf build\nEOF'
check PASS $'cat <<\'EOF\' | python -\nrd = 1\nEOF'
check ASK $'bash <<\'EOF\'\nrm -rf build\nEOF'
check ASK $'cat <<\'EOF\' | sh\nrm -rf build\nEOF'
check ASK $'ssh host <<\'EOF\'\nrm -rf build\nEOF'
check ASK $'cat <<EOF\n$(rm -rf build)\nEOF'
check ASK $'python - <<\'EOF\'\nrm -rf build'
check ASK $'python - <<\'EOF\'\nx = 1\nEOF\nrm -rf build'
check ASK $'python - <<\'EOF\'\nimport os\nos.system("cmd /c del build.txt")\nEOF'
# --- deletes from Python/Node code the command executes ---
check ASK $'python - <<\'EOF\'\nimport shutil\nshutil.rmtree("build")\nEOF'
check ASK 'python -c "import os; os.remove('"'"'data.json'"'"')"'
check ASK $'python - <<\'EOF\'\nfrom pathlib import Path\nPath("out/report.md").unlink()\nEOF'
check ASK $'python - <<\'EOF\'\nimport os\nfor f in files:\n    os.remove(f)\nEOF'
check ASK $'python - <<\'EOF\'\nimport subprocess\nsubprocess.run(["rm", "-rf", "build"])\nEOF'
check ASK $'python - <<\'EOF\'\nimport os\nos.system("rm -rf build")\nEOF'
check ASK 'node -e "require('"'"'fs'"'"').rmSync('"'"'dist'"'"', {recursive: true})"'
check ASK $'cat <<\'EOF\' | python -\nimport shutil\nshutil.rmtree("build")\nEOF'
check ASK $'python -c @\'\nimport shutil\nshutil.rmtree("build")\n\'@'
check PASS $'python - <<\'EOF\'\nimport os\nos.remove("tmp_out.json")\nEOF'
check PASS 'python -c "import shutil; shutil.rmtree('"'"'/tmp/x'"'"')"'
check PASS $'python - <<\'EOF\'\nitems.remove(x)\ns = s.removeprefix("a")\nsubprocess.run(["git", "status"])\nEOF'
check PASS $'cat > cleanup.py <<\'EOF\'\nimport shutil\nshutil.rmtree("build")\nEOF'
check PASS 'grep -n "shutil.rmtree(" scripts/*.py'
check PASS $'git commit -F- <<\'EOF\'\nguard now catches os.remove("x")\nEOF'
check PASS 'node -e "const re = /a/; re.exec('"'"'rm x'"'"')"'

# --- git is the undo: clean tracked files pass, anything git cannot restore asks ---
export GUARD_RM_GIT_UNDO=1
TMPROOT=$(mktemp -d)
REPO="$TMPROOT/repo"
mkdir -p "$REPO/src/lib"
git -C "$REPO" init -q
git -C "$REPO" config user.email test@example.com
git -C "$REPO" config user.name test
printf 'a\n' > "$REPO/src/a.ts"
printf 'b\n' > "$REPO/src/lib/b.ts"
printf 'node_modules/\n*.local\n' > "$REPO/.gitignore"
git -C "$REPO" add src/a.ts src/lib/b.ts .gitignore
git -C "$REPO" commit -q -m init -- src/a.ts src/lib/b.ts .gitignore
checkc PASS "$REPO" 'rm src/a.ts'
checkc PASS "$REPO" 'rm -rf src/lib'
checkc PASS "$REPO" 'rm -rf src'
checkc PASS "$REPO" 'Remove-Item -Recurse -Force src\lib'
checkc PASS "$REPO" "rm $REPO/src/a.ts"
checkc PASS "$REPO" $'python - <<\'EOF\'\nimport os\nos.remove("src/a.ts")\nEOF'
checkc ASK "$REPO" 'rm src/*.ts'
checkc ASK "$REPO" 'cd src && rm a.ts'
checkc ASK "$REPO" 'rm -rf .git'
checkc ASK "$REPO" 'rm -rf .'
checkc ASK "$REPO" 'rm src/missing.ts'
checkc ASK "$TMPROOT" 'rm -rf repo'
printf 'changed\n' > "$REPO/src/a.ts"
checkc ASK "$REPO" 'rm src/a.ts'
checkc ASK "$REPO" 'rm -rf src'
checkc PASS "$REPO" 'rm src/lib/b.ts'
git -C "$REPO" checkout -q -- src/a.ts
printf 'new\n' > "$REPO/src/lib/new.ts"
checkc ASK "$REPO" 'rm -rf src/lib'
checkc ASK "$REPO" 'rm src/lib/new.ts'
mv "$REPO/src/lib/new.ts" "$REPO/src/lib/key.local"
checkc ASK "$REPO" 'rm -rf src/lib'
checkc PASS "$REPO" 'rm src/lib/b.ts'
GUARD_RM_GIT_UNDO=0 checkc ASK "$REPO" 'rm src/lib/b.ts'
rm -rf "$TMPROOT"
export GUARD_RM_GIT_UNDO=0

# --- Codex dialect: ask is not supported there, so the guard blocks with exit 2 ---
ERRF=$(mktemp)
out=$(payload "" 'rm -rf build' | bash "$H" --codex 2>"$ERRF"); code=$?
err=$(cat "$ERRF")
got=PASS; [ "$code" = 2 ] && [ -z "$out" ] && [ -n "$err" ] && got=BLOCK
result BLOCK "$got" "--codex: real delete is blocked (exit 2, reason on stderr)" "exit $code; $err"
out=$(payload "" 'rm tmp.py' | bash "$H" --codex 2>"$ERRF"); code=$?
got=BLOCK; [ "$code" = 0 ] && [ -z "$out" ] && got=PASS
result PASS "$got" "--codex: temp delete passes silently" "exit $code; $out"
rm -f "$ERRF"

echo; echo "--- example prompt text:"
payload "" 'cd foo && rm -rf dist tmp.py 2>/dev/null' | bash "$H"
echo

# --- fallbacks: a broken parser or reason script must still ask ---
out=$(payload "" 'rm tmp.py' | GUARD_RM_REASON_PY=/nonexistent/x.py bash "$H")
got=PASS; [ -n "$out" ] && got=ASK
result ASK "$got" "fallback: reason script unavailable -> blunt grep asks" "$out"
out=$(printf '%s' '{"tool_name":"Bash","tool_input":{"command":"rm -rf build"' | bash "$H")
got=PASS; [ -n "$out" ] && got=ASK
result ASK "$got" "fallback: unparseable hook JSON -> raw text is scanned and asks" "$out"

echo; echo "passed: $pass_count, failed: $fail_count"
exit $fail
