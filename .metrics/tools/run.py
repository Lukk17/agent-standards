"""Start the quality loop wrapper. `run` and `run.cmd` call this file with Python 3.11 or newer."""

import sys

from quality_loop.cli import main

if __name__ == "__main__":
    sys.exit(main())
