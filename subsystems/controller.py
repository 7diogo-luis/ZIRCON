"""ZIRCON Controller."""

from subsystems.cli import cli
from subsystems.inputLayer import inputLayer
from subsystems.core import core


def controller(debug_mode):
    """Invoke relevant subsystems.

    Parameters
    ----------
    debug_mode : bool
        True if internal variables are to be returned after execution stops,
        False otherwise.

    Returns
    -------
    bool or str or None
        String if user commands exit, dictionary with internal variables if
        debug mode is set, None if another call to the controller is required.
    """
    commands = cli()

    if commands is None:
        return

    elif commands == 'exit':
        return commands

    elif commands == 'debug' or commands == 'prod':
        return commands

    else:
        station_label = commands['station_label']
        parameters_label = commands['parameters_label']

        layout, parameters = inputLayer(station_label, parameters_label)

    if debug_mode:
        core_debug_data = core(layout, parameters, debug_mode)

        return {'inputLayer': {'layout': layout, 'parameters': parameters},
                'core': core_debug_data}

    else:
        itineraries, delays = core(layout, parameters, debug_mode)
