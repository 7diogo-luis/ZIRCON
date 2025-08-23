"""ZIRCON Main Loop."""

from subsystems.controller import controller

debug_mode = False

while True:
    output = controller(debug_mode)

    if output == 'exit':
        break

    elif type(output) is dict:
        layout = output['inputLayer']['layout']
        parameters = output['inputLayer']['parameters']
        signals = output['core']['signals']
        paths = output['core']['paths']
        its = output['core']['its']
        break

    elif output == 'debug':
        debug_mode = True

    elif output == 'prod':
        debug_mode = False
