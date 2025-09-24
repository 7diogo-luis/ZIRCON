"""ZIRCON Output Layer."""

from modules.exporter import exporter
from modules.outputAssembler import outputAssembler


def outputLayer(movements, delays, aux_data, inputs, layout, signals):
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
    """
    PEE = outputAssembler(movements, delays, aux_data, inputs, layout, signals)
    exporter(PEE)

    return PEE
