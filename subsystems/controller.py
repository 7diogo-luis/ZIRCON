"""ZIRCON Controller."""

from subsystems.CLI import CLI
from subsystems.inputLayer import inputLayer
from subsystems.core import core
from subsystems.outputLayer import outputLayer


def controller(persist):
    """Invoke relevant subsystems.

    Parameters
    ----------
    persist : dict
        Current main variables.

    Returns
    -------
    dict
        Updated main variables.
    """
    usr_request = CLI(persist['sw_version'], persist['loaded_layout'],
                      persist['processed_layout'])
    persist['usr_request'] = usr_request

    if persist['usr_request']['action'] == 'load':
        layout, parameters, aux_data, inputs = inputLayer(persist
                                                          ['usr_request']
                                                          ['modifier'], None)
        aux_data['sw_version'] = persist['sw_version']

        persist['layout'] = layout
        persist['aux_data'] = aux_data
        persist['inputs'] = inputs
        persist['loaded_layout'] = True

        return persist

    elif persist['usr_request']['action'] == 'process':
        layout, parameters, aux_data, inputs = inputLayer(None, persist
                                                          ['usr_request']
                                                          ['modifier'])
        persist['inputs']['zop'] = inputs['zop']

        persist['parameters'] = parameters
        signals, paths, raw_movements, movements, delays = core(persist
                                                                ['layout'],
                                                                persist
                                                                ['parameters'])
        persist['signals'] = signals
        persist['paths'] = paths
        persist['raw_movements'] = raw_movements
        persist['movements'] = movements
        persist['delays'] = delays
        persist['processed_layout'] = True

        return persist

    elif persist['usr_request']['action'] == 'export':
        interlocking_prog = outputLayer(persist['movements'],
                                        persist['delays'],
                                        persist['aux_data'],
                                        persist['inputs'],
                                        persist['layout'],
                                        persist['signals'],
                                        persist['usr_request']['modifier'])
        persist['interlocking_prog'] = interlocking_prog

        return persist

    else:
        return persist
