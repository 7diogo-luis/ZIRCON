"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from modules.signalProcessor import signalProcessor
from modules.spatialEngine import spatialEngine
from modules.router import router
from modules.flankProtection import flankProtection
from modules.delayEngine import delayEngine


def core(layout, parameters):
    """Handle processing of the loaded layout.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    parameters : dict
        Operational parameter variables as encoded in the .zop file.

    Returns
    -------
    signals : Pandas DataFrame
        Table of signals and their respective properties.
    paths : list
        List of all possible paths in the station.
    movements : list
        List of dictionaries, each relative to a possible movement (without
        flank protection required sections and switches).
    delays : dict
        Dictionary containing OL, ARC and ERC delays.
    """
    signals = signalProcessor(layout,
                              parameters['terminal_branches_are_destinations'],
                              parameters['regimes_to_block'],
                              parameters['regimes_to_NDZ'],
                              parameters['regimes_to_terminal'],
                              parameters['allow_shunt_to_circ_sig'])
    paths = spatialEngine(layout, parameters['overlap_to_terminal_branch'],
                          parameters['horse_neck_possible'])
    raw_movements = router(paths, signals, layout,
                           parameters['main_ol_distance'],
                           parameters['dos_ol_distance'],
                           parameters['shunt_ol_distance'],
                           parameters['logic_ol_possible_regimes'],
                           parameters['logic_ol_switch_point_dependant'],
                           parameters['allow_distant_switch_OL_lock'],
                           parameters['derailer_alt_OL_allowed_types'],
                           parameters['derailer_margin'])
    movements = flankProtection(raw_movements, layout, signals,
                                parameters['shunt_sig_filters_fp'])
    delays = delayEngine(movements, layout, signals,
                         parameters['OL_delay_dist_weight'],
                         parameters['OL_delay_dist_bias'],
                         parameters['ARC_delay_dist_weight'],
                         parameters['ERC_delay_circ_multiplier'],
                         parameters['ERC_delay_shunt_multiplier'],
                         parameters['main_ol_distance'],
                         parameters['dos_ol_distance'],
                         parameters['shunt_ol_distance'],
                         parameters['RC_min_delay'],
                         parameters['RC_max_delay'],
                         parameters['delay_round_multiple'],
                         parameters['delay_round_down_allowed'])

    return signals, paths, movements, delays
