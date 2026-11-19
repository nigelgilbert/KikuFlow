# Factory report: feature/reorder-log, run 1

Work file: `docs/plan-reorder-log.md`. Branch `feature/reorder-log`, cut from `main` at
`62d500d`. One review, adversary Sol.

## Work items

1. **Write new entries at the top.** Landed in `cbe767a`. `append` in
   `sidecar/src/slopr_sidecar/lifecycle.py` is now `prepend` and writes
   `[fold(text), *old][:keep]`, so the newest entry is first and the cap drops from the bottom.
   The order tests in `test_log.py` and `test_lifecycle.py` assert newest first; `test_server.py`
   only checks single entries and needed no change.
2. **Docs state the new order.** Landed in `f26f622`. `README.md` and `sidecar/README.md` say
   newest first for both files. `examples/README.md` states no order and is unchanged.

## Review 1: `62d500d..f26f622`

The reviewer found both acceptance criteria met and raised five candidates.

**Fix**: none.

**Nit**

1. **Whitespace-only text writes a blank top entry.** `sidecar/src/slopr_sidecar/lifecycle.py:109`.
   An `on_sent` hook returning `"  "` passes the empty check in `server.py`, `fold` turns it into
   `""`, and the file starts with a blank entry that takes a cap slot. The flaw predates the diff;
   the new order puts it at the top. Fix: fold first and return without writing when the result is
   empty; add a test that writes `"One."` then `"  "` and expects `"One."`. Confidence: high.
2. **Docstring says "first" where "newest" is meant.** `sidecar/src/slopr_sidecar/lifecycle.py:107`.
   Fix: `"""Put `text` first in the file at `path` as one line, keeping the newest `keep`."""`
   Confidence: medium.

**Wontfix**

- `lifecycle.py:109`, a file written oldest first before this change ends up mixed and loses its
  newest old entries first. The plan puts conversion out of scope; the file corrects itself once
  a cap's worth of new entries is written. See the open items.
- `lifecycle.py:109`, non-atomic write and concurrent `write_error`. Predates the diff, outside
  the plan, and both report sites run on the single-worker executor.
- `test_log.py:44`, no test prepends onto a full file. The filter mutated `[:keep]` to `[-keep:]`
  and two existing cap tests failed, since the 101st and 51st writes already prepend onto a full
  file.

**Split**: none.

Candidates 5, kept 2, adversary Sol, 1 exchange (on the docstring).
