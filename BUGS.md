# BUGS

- HMS+ et al don't work well with negative times.  Avoid them for now.

- ENG has weirdness if the number of significant digits to too small compared
  to the magnitude of the number.  For example, "103.6 1 eng" displays as
  "10e+00" rather than "100e+00".  And "0 eng" crashes the program because
  it tries to take a logarithm of zero.

- `[3 2 1] 3 *` crashes

- Another quick way to crash:
  variable foo
  undef foo
  @foo
