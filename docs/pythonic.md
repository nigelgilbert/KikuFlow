# Python

- Readability counts; sparse is better than dense.
- Give each line one job. When an expression reads from the inside out, name the inner part.
- Add a name when it tells the reader something the expression does not.
- Name a function for what it does or returns: `strip_comments`, not `clean`.
- Annotate a parameter with the type its callers pass.
- Write a docstring to PEP 257: a one-line summary phrased as a command, such as `Return …`.
- It is easier to ask forgiveness than permission: try the operation and catch the specific exception, such as `except FileNotFoundError`.