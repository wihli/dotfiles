# Forth foundations
<!-- keywords: gforth stack words definitions imports libraries require include ttester -->

`crumb` is the first local Gforth utility. Its source is
`$SRC_DIR/wihli-dotfiles/bin/.local/bin/crumb`.

## The working model

- A **word** is a named operation. `:` starts a definition and `;` ends it.
- Data flows through the stack from left to right: `2 3 +` leaves `5`.
- `( before -- after )` documents a word's stack effect.
- Build bottom-up: test small words interactively, then compose them into a
  high-level word that reads like the problem statement.
- Factor around meaningful, reusable behavior. Shortness is a target, not a
  reason to create names for arbitrary fragments.

Useful inspection words:

```forth
.s                  \ show the data stack
see collect-message \ decompile one word
words               \ list visible words
```

## Load code

`include` always loads a source file:

```forth
include path/to/file.fs
s" path/to/file.fs" included
```

`require` loads it only once and is the normal choice for libraries:

```forth
require string.fs
s" path/to/library.fs" required
```

A reusable source file should leave the stack exactly as it found it. Gforth's
`script?` flag lets a file expose definitions when loaded interactively while
still running its entrypoint when invoked as a script; `crumb` demonstrates
this at its end.

## Explore `crumb`

Load its definitions without executing the command:

```forth
s" bin/.local/bin/crumb" included
see crumb
```

Then try pure words directly:

```forth
s" alpha beta" bl contains? .
s" safe message" valid-message? .
time&date .s
```

Start a clean interpreter for each experiment if the stack gets confusing.
Gforth source can redefine a word, so an old broken definition otherwise stays
in the dictionary behind its replacement.

## Run tests

```sh
python3 -m unittest tests.test_crumb -v
```

Gforth also bundles `test/ttester.fs`. Its basic form compares the resulting
stack with an expected stack:

```forth
require test/ttester.fs
T{ 2 3 + -> 5 }T
```

Use it when `crumb` gains enough pure transformations to justify a native
Forth unit-test file. The current Python test intentionally exercises the CLI,
filesystem, exit status, and output as one black-box behavior.

## Structure rule

Keep the executable self-contained until a second program needs one of its
words. At that point, move the repeated, stack-neutral definitions into a
`.fs` library and load it with `require`; consider a separate wordlist only
when private implementation names actually collide with the public interface.

## References

- [Starting Forth](https://www.forth.com/starting-forth/0-starting-forth/)
- [Thinking Forth](https://www.forth.com/wp-content/uploads/2018/11/thinking-forth-color.pdf)
- [Gforth tutorial](https://gforth.org/manual/Tutorial.html)
- [Gforth source files and `require`](https://gforth.org/manual/Forth-source-files.html)
- [Gforth source repository](https://github.com/forthy42/gforth)
- [theForthNet package repository](https://theforth.net/packages)
