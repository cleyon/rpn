'''
#############################################################################
#
#       M A I N
#
#############################################################################
'''

import inspect
import os
import sys
import traceback
from rpn import app
from rpn import exception


def main(argv):
    rpndir = os.path.dirname(inspect.getsourcefile(app))
    try:
        if app.initialize(rpndir, argv):
            app.main_loop()
    except exception.EndProgram:
        pass
    except exception.FatalErr as e:
        if len(str(e)) > 0:
            print("Fatal error: {}".format(e)) # OK
        print()
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)
    except exception.RuntimeErr as err_main:
        print("Uncaught exception: {} ({})".format(err_main.code, str(err_main))) # OK
        print()
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)

    app.end_program()


if __name__ == '__main__':
    main(sys.argv[1:])
    sys.exit(0)
