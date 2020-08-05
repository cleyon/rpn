# rpn

RPN calculator and interpreter

## Requirements

- Python 3

- numpy

``` shell
pip3 install --user numpy
```

- scipy

``` shell
pip3 install --user scipy
```

- PLY

``` shell
pip3 install --user ply
```

## Enhancements

- TVM
- More math categories (plot, root solve, integrate)

## Bugs

- HMS+ et al don't work well with negative times.  Avoid them for now.

- p_case() does not create a scope for caseval variable:

``` forth
: sum2
  doc:"sum  ( ... -- sum )  Sum all numbers on the stack"

  depth case
    0 of 0 endof
    1 of endof
    otherwise @caseval 0 do + loop
  endcase
;
```
