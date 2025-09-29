"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from modules.loader import loader
from modules.preProcessor import preProcessor


def inputLayer(station_label, parameters_label):
    """Return pre-processed inputs.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed.
    parameters_label : str
        Label of the parameter file to be considered.

    Returns
    -------
    layout : dict
        Description of the station's layout.
    parameters : dict
        Operational parameter variables as encoded in the .zop file.
    aux_data : dict
        Layout's auxiliary data.
    inputs : dict
        Inputs read from each file.
    """
    lt_top_raw, lt_geo, aux_data, parameters, inputs = loader(station_label,
                                                              parameters_label)

    if lt_top_raw is not None and lt_geo is not None:
        layout = preProcessor(lt_top_raw, lt_geo)

    else:
        layout = None

    return layout, parameters, aux_data, inputs
