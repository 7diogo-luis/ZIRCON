"""ZIRCON Main Loop."""

from subsystems.controller import controller

debug_mode = False

while True:
    output = controller(debug_mode)

    if output == 'exit' or type(output) is dict:
        break

    elif output == 'debug':
        debug_mode = True

    elif output == 'prod':
        debug_mode = False
