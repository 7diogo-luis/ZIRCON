"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from subsystems.controller import controller

persist = {'sw_version': 'v0.24.3',
           'loaded_layout': False,
           'processed_layout': False,
           'usr_request': None,
           'station_label': None,
           'layout': None,
           'parameters': None,
           'aux_data': None,
           'inputs': None,
           'signals': None,
           'paths': None,
           'movements': None,
           'delays': None,
           'interlocking_prog': None}

while True:
    persist = controller(persist)

    if persist['usr_request']['action'] == 'exit':
        break

for key, data in persist.items():
    locals()[key] = data

