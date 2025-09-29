"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from math import ceil, floor
from modules.router import getSignalData


def delayEngine(movements, layout, signals, OL_delay_dist_weight,
                OL_delay_dist_bias, ARC_delay_dist_weight,
                ERC_delay_circ_multiplier, ERC_delay_shunt_multiplier, m_OL,
                d_OL, s_OL, RC_min_delay, RC_max_delay, delay_round_multiple,
                delay_round_down_allowed):
    """Compute delay timings for the encoded station.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas DataFrame
        Table of signals and their respective properties.
    OL_delay_dist_weight : float
        Weight of the track length for calculation of overlap delays.
    OL_delay_dist_bias : float
        OL delay bias (value added to the overlap delay timing).
    ARC_delay_dist_weight : float
        Weight of the total distance for calculation of the ARC delay.
    ERC_delay_circ_multiplier : float
        Distance multiplier for curculation movements (ERC delay calculation).
    ERC_delay_shunt_multiplier : float
        Distance multiplier for shunt movements (ERC delay calculation).
    m_OL : float
        Overlap distance for main movements.
    d_OL : float
        Overlap distance for DOS movements.
    s_OL : float
        Overlap distance for shunt movements.
    RC_min_delay : float
        Minimum value for route cancellation delay timings.
    RC_max_delay : float
        Maximum value for route cancellation delay timings.
    delay_round_multiple : float
        Rounded delay timings will be a multiple of this number (after
        rounding).
    delay_round_down_allowed : bool
        True if delay timings can be rounded down, False otherwise.

    Returns
    -------
    dict
        Dictionary containing OL, ARC and ERC delay timings.
    """
    overlap_delays = overlapDelays(movements, layout, OL_delay_dist_weight,
                                   OL_delay_dist_bias, delay_round_multiple,
                                   delay_round_down_allowed)
    ARC_delays = ARCdelays(layout, signals, ARC_delay_dist_weight,
                           RC_min_delay, RC_max_delay, delay_round_multiple,
                           delay_round_down_allowed)
    ERC_delays = ERCdelays(movements, layout, ERC_delay_circ_multiplier,
                           ERC_delay_shunt_multiplier, m_OL, d_OL, s_OL,
                           RC_min_delay, RC_max_delay, delay_round_multiple,
                           delay_round_down_allowed, overlap_delays,
                           ARC_delays)
    delays = {'overlap': overlap_delays,
              'approach_rt_cncl': ARC_delays,
              'emerg_rt_cncl': ERC_delays}

    return delays


def extractNodePK(sec_lbl, nde_idx, layout):
    """Get PK of a specified node of a specified section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to consider.
    nde_idx : str
        Label of the node to consider.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    float
        PK of the specified node.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:
            return node['pk']


def extractNodeConEle(sec_lbl, nde_idx, layout):
    """Get the element connected to a specified node of a specified section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to consider.
    nde_idx : str
        Label of the node to consider.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    str
        Label of the element connected to the specified node.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:
            return node['con_ele']


def overlapDelays(movements, layout, weight, bias, round_multiple,
                  round_down_allowed):
    """Compute overlap delays for every section where a train can park.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    layout : dict
        Station's layout with explicit node signs.
    weight : float
        Weight of the track length for calculation purposes.
    bias : float
        Bias (value added to the delay timing).
    round_multiple : float
        Rounded delay timings will be a multiple of this number (after
        rounding).
    round_down_allowed : bool
        True if delay timings can be rounded down, False otherwise.

    Returns
    -------
    list
        List containig OL delay timings and their respective sections.
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [NDZ['label'] for NDZ in layout['NDZs']]
    raw_overlap_delays = {'tracks': [],
                          'delays': []}

    for movement in movements:

        park_section = movement['sections']['route'][-1]
        park_transit = movement['transits']['route'][-1]

        park_sec_con_ele = extractNodeConEle(park_section,
                                             park_transit[-1],
                                             layout)

        if (park_sec_con_ele is None or park_sec_con_ele in blocks or
                park_sec_con_ele in NDZs):
            continue

        entry_pk = extractNodePK(park_section, park_transit[0], layout)
        exit_pk = extractNodePK(park_section, park_transit[-1], layout)

        delay = abs(entry_pk - exit_pk) * weight + bias

        rnd_delay = roundTiming(delay, round_multiple, round_down_allowed)

        if park_section in raw_overlap_delays['tracks']:
            index = raw_overlap_delays['tracks'].index(park_section)

            if rnd_delay > raw_overlap_delays['delays'][index]:
                raw_overlap_delays['delays'][index] = rnd_delay

        else:
            raw_overlap_delays['tracks'].append(park_section)
            raw_overlap_delays['delays'].append(rnd_delay)

    overlap_delays = []

    for i in range(len(raw_overlap_delays['tracks'])):
        overlap_delays.append({'track': raw_overlap_delays['tracks'][i],
                               'delay': raw_overlap_delays['delays'][i]})

    return overlap_delays


def ARCdelays(layout, signals, weight, minimum, maximum, round_multiple,
              round_down_allowed):
    """Compute ARC delays for every signal that has an approach zone.

    Parameters
    ----------
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas DataFrame
        Table of signals and their respective properties.
    weight : float
        Weight of the total distance for calculation purposes.
    minimum : float
        Minimum value for the delay timing.
    maximum : float
        Maximum value for the delay timing.
    round_multiple : float
        Rounded delay timings will be a multiple of this number (after
        rounding).
    round_down_allowed : bool
        True if delay timings can be rounded down, False otherwise.

    Returns
    -------
    list
        List containig ARC delay timings and their respective signals.
    """
    ARC_delays = []

    for index, row in signals.iterrows():

        if row.zap_origin_pk == '':
            continue

        zap_origin_pk = row.zap_origin_pk
        zap_origin_sft_fac = row.zap_origin_sft_fac
        signal_pole_pk = getSignalData(row.signal, layout)['pk']

        delay = ((abs(zap_origin_pk - signal_pole_pk) + zap_origin_sft_fac) *
                 weight)

        if delay < minimum:
            delay = minimum

        elif delay > maximum:
            delay = maximum

        rnd_delay = roundTiming(delay, round_multiple, round_down_allowed)

        ARC_delays.append({'signal': row.signal,
                           'delay': rnd_delay})

    return ARC_delays


def secHasSwis(sec_lbl, layout):
    """Know if a section has switches (inc. derailers).

    Parameters
    ----------
    sec_lbl : str
        Label of the section to consider.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    bool
        True if the section has switches (inc. derailers), False otherwise.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['switches']:
            return True

    return False


def ERCdelays(movements, layout, circ_multiplier, shunt_multiplier, m_OL, d_OL,
              s_OL, minimum, maximum, round_multiple, round_down_allowed,
              overlap_delays, ARC_delays):
    """Compute ERC delays for every possible movement destination.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    layout : dict
        Station's layout with explicit node signs.
    circ_multiplier : float
        Distance multiplier for curculation movements.
    shunt_multiplier : float
        Distance multiplier for shunt movements.
    m_OL : float
        Overlap distance for main movements.
    d_OL : float
        Overlap distance for DOS movements.
    s_OL : float
        Overlap distance for shunt movements.
    minimum : float
        Minimum value for the delay timing.
    maximum : float
        Maximum value for the delay timing.
    round_multiple : float
        Rounded delay timings will be a multiple of this number (after
        rounding).
    round_down_allowed : bool
        True if delay timings can be rounded down, False otherwise.
    overlap_delays : list
        List containig OL delay timings and their respective sections.
    ARC_delays : list
        List containig ARC delay timings and their respective signals.

    Returns
    -------
    list
        List containig ERC delay timings and their respective destinations.
    """
    raw_ERC_delays = {'destinations': [],
                      'delays': []}

    for movement in movements:
        park_sec = movement['sections']['route'][-1]
        start_sig = getSignalData(movement['origin']
                                  ['literal'], layout)
        start_point = start_sig['pk']
        destination = getSignalData(movement['destination']
                                    ['literal'], layout)

        if destination is None:
            end_point = extractNodePK(movement['sections']['route'][-1],
                                      movement['transits']['route'][-1][-1],
                                      layout)
            no_OL = True

        else:
            end_point = destination['pk']
            no_OL = False

        if movement['type'] == 'Main':

            if not no_OL:
                dist = abs(end_point - start_point) + m_OL

            else:
                dist = abs(end_point - start_point)

            delay = dist * circ_multiplier

        elif movement['type'] == 'DOS':

            if not no_OL:
                dist = abs(end_point - start_point) + d_OL

            else:
                dist = abs(end_point - start_point)

            delay = dist * circ_multiplier

        else:
            park_sec_has_swis = secHasSwis(movement['sections']['route'][-1],
                                           layout)

            if not movement['logic_overlap'] or park_sec_has_swis:

                if movement['logic_overlap']:
                    delay = abs(end_point - start_point) * shunt_multiplier

                else:
                    delay = ((abs(end_point - start_point) + s_OL) *
                             shunt_multiplier)

            else:
                park_trans = movement['transits']['route'][-1]
                park_entry_pk = extractNodePK(park_sec, park_trans[0], layout)
                delay = abs(park_entry_pk - start_point) * shunt_multiplier

        if delay < minimum:
            delay = minimum

        elif delay > maximum:
            delay = maximum

        for overlap_delay in overlap_delays:

            if overlap_delay['track'] == park_sec:

                if delay < overlap_delay['delay']:
                    delay = overlap_delay['delay']

        for ARC_delay in ARC_delays:

            if ARC_delay['signal'] == start_sig['label']:

                if delay < ARC_delay['delay']:
                    delay = ARC_delay['delay']

        rnd_delay = roundTiming(delay, round_multiple, round_down_allowed)

        if destination is None:

            if 'M_' in movement['destination']['literal']:
                dest_lbl = movement['destination']['alias']

            else:
                dest_lbl = movement['destination']['literal']

        else:

            if 'M_' in movement['destination']['literal']:
                dest_lbl = movement['destination']['alias']

            else:
                dest_lbl = destination['label']

        if dest_lbl in raw_ERC_delays['destinations']:
            index = raw_ERC_delays['destinations'].index(dest_lbl)

            if rnd_delay > raw_ERC_delays['delays'][index]:
                raw_ERC_delays['delays'][index] = rnd_delay

        else:
            raw_ERC_delays['destinations'].append(dest_lbl)
            raw_ERC_delays['delays'].append(rnd_delay)

    ERC_delays = []

    for i in range(len(raw_ERC_delays['destinations'])):
        ERC_delays.append({'destination': raw_ERC_delays['destinations'][i],
                           'delay': raw_ERC_delays['delays'][i]})

    return ERC_delays


def roundTiming(delay, round_multiple, round_down_allowed):
    """Round delay timings.

    Parameters
    ----------
    delay : float
        Delay timing value, not rounded.
    round_multiple : float
        Rounded delay timings will be a multiple of this number (after
        rounding).
    round_down_allowed : bool
        True if delay timings can be rounded down, False otherwise.

    Returns
    -------
    float
        Delay timing value, rounded.
    """
    rounded_down_delay = delay

    while True:

        delay = ceil(delay)
        mod = delay % round_multiple

        if mod == 0:
            return delay

        else:
            delay += 1

        if round_down_allowed:
            rounded_down_delay = floor(rounded_down_delay)
            mod = rounded_down_delay % round_multiple

            if mod == 0:
                return rounded_down_delay

            else:
                rounded_down_delay -= 1
