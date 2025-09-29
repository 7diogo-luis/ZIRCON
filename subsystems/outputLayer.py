"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from modules.exporter import exporter
from modules.outputAssembler import outputAssembler


def outputLayer(movements, delays, aux_data, inputs, layout, signals, mode):
    """Post-process data and export it to .xlsx or byte stream file.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    delays : dict
        Dictionary containing the delay timings for the station layout.
    aux_data : dict
        Dictionary containing the station's auxiliary data.
    inputs : dict
        Dictionary containing input data (.zlt, .zlg and .zop).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.
    mode : str
        "pickle" if the data is to be exported to a pickled file, "xlsx" if the
        data is to be exported to a .xlsx file.

    Returns
    -------
    dict
        Interlocking program.
    """
    interlocking_prog = outputAssembler(movements, delays, aux_data, inputs,
                                        layout, signals)
    exporter(interlocking_prog, mode)

    return interlocking_prog
