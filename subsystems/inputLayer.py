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
    lt_top_raw, lt_geo, aux_data, parameters, inputs = loader(station_label,
                                                              parameters_label)

    if lt_top_raw is not None and lt_geo is not None:
        layout = preProcessor(lt_top_raw, lt_geo)

    else:
        layout = None

    return layout, parameters, aux_data, inputs
