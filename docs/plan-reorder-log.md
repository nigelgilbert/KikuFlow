# Plan: newest log and error entries first

`log.txt` and `errors.txt` are written by `append` in `sidecar/src/slopr_sidecar/lifecycle.py`.
Today each new entry goes at the bottom, and the cap (100 for the log, 50 for errors) drops the
oldest entries from the top. This branch starts from `main` and targets `main`.

## Items

1. **Write new entries at the top.** `append` puts the new entry first, above the existing
   entries, still separated by one blank line. The cap drops entries from the bottom, so the file
   keeps the newest `keep` entries, newest first. The entry format is unchanged: one line each,
   the time in front for errors, UTF-8, no blank entry from an empty file or a trailing newline.
   Rename `append` to fit what it now does if the name misleads.

   Accepted when: after writing A, B, C the log reads `C\n\nB\n\nA`; writing 101 texts keeps the
   newest 100 with the newest on top and the first text dropped; errors behave the same with a cap
   of 50; the tests in `sidecar/tests/` that state the order (`test_log.py` and any in
   `test_lifecycle.py` or `test_server.py`) assert the new order.

2. **Docs state the new order.** The README's Log section says "oldest first"; it says newest
   first. Any other doc that states the order or which entries the cap drops (`sidecar/README.md`,
   `examples/README.md`) matches.

   Accepted when: no doc says oldest first or implies new entries go at the bottom.

## Out of scope

- Converting existing `log.txt` or `errors.txt` files written oldest first. They are read as they
  are; the user can delete them.
- The Swift app: it only opens the files.
