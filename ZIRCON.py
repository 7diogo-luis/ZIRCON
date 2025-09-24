"""ZIRCON Main Loop."""

from subsystems.controller import controller

sw_version = 'v0.20.0'
debug_mode = False

while True:
    output = controller(debug_mode, sw_version)

    if output == 'exit':
        break

    elif type(output) is dict:
        layout = output['inputLayer']['layout']
        aux_data = output['inputLayer']['aux_data']
        parameters = output['inputLayer']['parameters']
        signals = output['core']['signals']
        paths = output['core']['paths']
        raw_movements = output['core']['raw_movements']
        movements = output['core']['movements']
        delays = output['core']['delays']
        break

    elif output == 'debug':
        debug_mode = True

    elif output == 'prod':
        debug_mode = False
