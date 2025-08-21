"""ZIRCON Input Layer."""

from modules.loader import loader
from modules.preProcessor import preProcessor


def inputLayer(station_label, parameters_label):
    """Return inputs for processing.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed (<STATION_LABEL>.zlt).
    parameters_label : str
        Label of the parameter file to be considered (<PARAMETERS_LABEL>.zop).

    Returns
    -------
    layout : dict
        Station's layout with explicit node signs.
    parameters : dict
        Operational parameter variables as encoded in the .zop file.
    """
    lt_top_raw, lt_geo, parameters = loader(station_label, parameters_label)

    layout = preProcessor(lt_top_raw, lt_geo)

    return layout, parameters
