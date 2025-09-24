"""ZIRCON Output Layer."""

from modules.exporter import exporter
from modules.outputAssembler import outputAssembler


def outputLayer(movements, delays, aux_data, inputs, layout, signals, mode):
    """Create .xlsx file containing the interlocking program data.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible itinerary.
    delays : dict
        Dictionary containing the delay timings for the station layout.
    aux_data : dict
        Dictionary containing the station's auxiliary data.
    inputs : dict
        Dictionary containing input data (.zlt, .zlg and .zop).
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
