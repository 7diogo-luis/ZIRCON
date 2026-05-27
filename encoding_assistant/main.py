"""Entry point: `python encoding_assistant/main.py` from the repo root.

Copyright (c) 2026-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

import os
import sys


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))))
    from encoding_assistant.app import run
    run()
