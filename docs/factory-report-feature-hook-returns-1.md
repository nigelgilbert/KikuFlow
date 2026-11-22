# Factory report: every hook returns a string

- Work file: `docs/hook-returns-plan.md`
- Branch: `feature/hook-returns`, cut from `chore/pythonic-meditations-1` at `6b942e3`
- Reviews: 1. Adversary: sol.

## Where the plan and the repo differed

- The plan says to delete the drafts `hook_message_2` and `report_2`. Neither exists in `lifecycle.py`, so there was nothing to delete.
- The plan says the files in `examples/` need no change. Five of them returned `None` on some paths, so fixing them was added as work item 4.

## Review 1: trimmed list (`6b942e3..d231ef6`)

### Fix

None.

### Nit

1. **`terminal.py` docstrings say "shell", the code matches "terminal"**
   - Where: `examples/terminal.py:1` and `:19`.
   - Problem: both docstrings tell the user to start with "shell", but `PREFIX` matches `terminal\b` and `examples/README.md` says "Terminal, ...". It predates this diff, in a file the diff touches.
   - Fix: change "shell" to "terminal" in both docstrings.
   - Confidence: high.

2. **Nested call in `fire_error` breaks the one-job-per-line rule**
   - Where: `sidecar/src/kiku_sidecar/lifecycle.py:123`.
   - Problem: `message = one_line(call("on_error", path, hook, e, message))` reads from the inside out, against `docs/pythonic.md`. The line is verbatim from the plan's sketch; the repo rule outranks the sketch.
   - Fix: inside the `try`, `returned = call("on_error", path, hook, e, message)`, then `message = one_line(returned)`.
   - Confidence: high.

3. **`test_on_done_returning_empty_stops_the_later_on_done` cannot tell a stop from a failure**
   - Where: `sidecar/tests/test_server.py:417`.
   - Problem: it asserts only that the last recorded call is `on_sent`, which would also pass if `on_done` raised.
   - Fix: keep the response and assert status 200, that log.txt holds the text, and `errors(tmp_path) == []`.
   - Confidence: high.

### Wontfix

- **An `on_error` hook that does `raise e` adds its note to the shared exception, so later `on_error` hooks see `on_error in a.py:2` as the last note.** The base commit behaved the same way, the plan's criterion (the reported message is unchanged) is met and tested, and a working fix adds a special case to a function the plan wants simple.
- **Whitespace-only text stops `after_reply` but not `fire` or `process`.** It predates the diff, the line is untouched, and the plan's rule is `""`.
- **No upgrade note in the docs.** The plan lists no upgrade section; "release notes" means the GitHub release text. Kept as an open item below.
- **No test that every recipe returns a str on every path.** The recipes do return a str on every path. Calling them from tests would write to `~/Documents/Dictations.txt` and open a network connection unless mocked, and one sample would not cover every path.
- **Split `Hook` into `TextHook` and `ErrorHook`.** The plan asks for `Callable[..., str]`.

### Split

None.

### Counts

8 candidates, 3 kept (0 fix, 3 nit). Adversary: sol. One exchange, covering four candidates; sol backed the filter agent's verdict on all four.
