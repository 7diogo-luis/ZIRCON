"""ZIRCON Core."""

from modules.signalProcessor import signalProcessor
from modules.spatialEngine import spatialEngine
from modules.router import router
#from modules.flankProtection import flankProtection


def core(layout, parameters, debug_mode):
    """Return results of processing.

    Parameters
    ----------
    layout : dict
        Station's layout with explicit node signs.
    parameters : dict
        Operational parameter variables as encoded in the .zop file.

    Returns
    -------
    itineraries : list
        List of dictionaries, each corresponding to a possible itinerary,
        containing relevant information.
    delays : dict
        Dictionary containing OL, ARI and AEI delays.
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
    # movements = flankProtection(raw_movements, layout, signals,
    #                             parameters['shunt_sig_filters_fp'])
    movements = None #TEMPORARY

    if debug_mode:
        return {'signals': signals,
                'paths': paths,
                'raw_movements': raw_movements,
                'movements': movements}
