"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from copy import deepcopy
from modules.spatialEngine import requiredSwitches


def router(paths, signals, layout, m_OL, d_OL, s_OL, viable_logic_OL,
           consider_swi_pnt_pk_logic_OL, allow_distant_switch_OL_lock,
           derailer_alt_OL_allowed_types, derailer_margin):
    """Compute possible movements and basic info regarding each.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.
    layout : dict
        Description of the station's layout.
    m_OL : float
        Overlap distance for Main movements.
    d_OL : float
        Overlap distance for DOS movements.
    s_OL : float
        Overlap distance for Shunt movements.
    viable_logic_OL : list
        List containing the movement types for which logic OL is possible.
    consider_swi_pnt_pk_logic_OL : bool
        True if the existance of a effective switch in a OL section of a
        suitable movement does not invalidate logic OL, as long as the
        switch's point PK is at a threshhold distance from the destination
        signal.
    allow_distant_switch_OL_lock : bool
        True if switches in overlap sections that have the point PK's distance
        to the movement's destination signal greater than the overlap distance
        should be locked, False otherwise.
    derailer_alt_OL_allowed_types : list
        List containing strings, each corresponding to a movement type for
        which alternative ovelaps with normally set derailers are allowed.
    derailer_margin : float
        Limit distance (of section with derailer) that can be anterior to the
        derailer point, while still considering the derailer excludes the
        section from overlap.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement (without
        flank protection required sections and switches).
    """
    raw_movs_incomplete = movementFinder(paths, signals, layout)
    raw_movs = addSwiAndTrans(raw_movs_incomplete, paths)
    raw_movs_OL_secs_OK = overlapTrimmer(raw_movs, layout, m_OL, d_OL, s_OL)
    inc_OL_movs = antiMovClones(raw_movs_OL_secs_OK)

    if not allow_distant_switch_OL_lock:
        no_logic_OL_movs = antiDistantSwitchOL(inc_OL_movs, signals, layout,
                                               m_OL, d_OL, s_OL)

    else:
        no_logic_OL_movs = inc_OL_movs

    unlbld_movs_no_der_alt_OL = logicOL(no_logic_OL_movs, layout,
                                        viable_logic_OL,
                                        consider_swi_pnt_pk_logic_OL,
                                        m_OL, d_OL, s_OL)
    unlbld_movs = derailerAltOL(layout, unlbld_movs_no_der_alt_OL,
                                derailer_alt_OL_allowed_types, derailer_margin)
    unconsolidated_movs = movLabeler(unlbld_movs, layout, signals)
    raw_movements = movConsolidator(unconsolidated_movs)

    return raw_movements


def movementFinder(paths, signals, layout):
    """Find all possible movements in the station.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement, including
        clones. No info on transits or switch positions.
    """
    raw_movs_incomplete = []
    it = {'path_index': None,
          'direction': None,
          'origin': None,
          'destination': None,
          'origin_alias': None,
          'destination_alias': None,
          'type': None,
          'route_secs': None,
          'possible_OL_path': None}
    section_labels = [section['label'] for section in layout['sections']]
    block_labels = [block['label'] for block in layout['blocks']]
    NDZ_labels = [ndz['label'] for ndz in layout['NDZs']]

    for mov_type in ['Main', 'DOS', 'Shunt']:

        for i in range(len(paths)):
            sections = paths[i]['path_secs']
            direction = paths[i]['direction']
            candidates = []
            route_secs = []
            prev_sec = None

            for section in sections:

                possible_new_candidates = list(signals.loc[
                                             (signals.section == section) &
                                             (signals.direction ==
                                              direction) &
                                             (signals.prev_sec ==
                                              prev_sec)].signal)

                new_candidates = []

                if len(candidates) == 0:

                    for j in range(len(possible_new_candidates)):
                        possible_origin =\
                            signals.loc[signals.signal ==
                                        possible_new_candidates[j]].\
                            possible_origin.iloc[0]

                        if mov_type[0] in possible_origin:
                            new_candidates.append(possible_new_candidates[j])

                else:

                    for k in range(len(possible_new_candidates)):
                        possible_destination =\
                            signals.loc[signals.signal ==
                                        possible_new_candidates[k]].\
                            possible_destination.iloc[0]

                        if mov_type[0] in possible_destination:
                            new_candidates.append(possible_new_candidates[k])

                prev_sec = section

                if len(candidates) == 0 and len(new_candidates) != 0:

                    route_secs.append(section)

                    for sig in new_candidates:
                        candidates.append(sig)

                elif len(candidates) != 0 and len(new_candidates) == 0:

                    route_secs.append(section)

                elif len(candidates) != 0 and len(new_candidates) != 0:

                    for origin_sig in candidates:

                        for destination_sig in new_candidates:

                            new_mov = deepcopy(it)

                            new_mov['path_index'] = i
                            new_mov['direction'] = direction
                            new_mov['origin'] = origin_sig
                            new_mov['destination'] = destination_sig

                            if ('M_' in destination_sig or
                                (mov_type == 'Shunt' and 'M'
                                 not in destination_sig and destination_sig not
                                 in section_labels and destination_sig not in
                                 block_labels and destination_sig not in
                                 NDZ_labels)):
                                new_mov['destination_alias'] =\
                                    (signals.loc[signals.signal ==
                                                 destination_sig].prev_sec.iloc
                                     [0])

                            new_mov['type'] = mov_type
                            new_mov['route_secs'] = route_secs

                            last_route_sec_idx = sections.index(route_secs[-1])
                            possible_OL_path =\
                                sections[last_route_sec_idx + 1:]
                            new_mov['possible_OL_path'] = possible_OL_path

                            raw_movs_incomplete.append(new_mov)

                    candidates = []
                    route_secs = []
                    route_secs.append(section)

                    for sig in new_candidates:
                        candidates.append(sig)

    return raw_movs_incomplete


def addSwiAndTrans(raw_movs_incomplete, paths):
    """Include transits and switch positions associated with each movement.

    Parameters
    ----------
    raw_movs_incomplete : list
        List of dictionaries, each relative to a possible movement, including
        clones. No info on transits or switch positions.
    paths : list
        List of all possible paths in the station.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement, including
        clones.
    """
    raw_movs = deepcopy(raw_movs_incomplete)

    for mov in raw_movs:
        route_transits = []
        route_switches = []
        possible_OL_transits = []
        possible_OL_switches = []
        path = paths[mov['path_index']]

        for route_sec in mov['route_secs']:

            index = path['path_secs'].index(route_sec)
            transit = path['path_transits'][index]
            route_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == route_sec:
                    route_switches.append(com_swi)

        for possible_OL_sec in mov['possible_OL_path']:

            index = path['path_secs'].index(possible_OL_sec)
            transit = path['path_transits'][index]
            possible_OL_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == possible_OL_sec:
                    possible_OL_switches.append(com_swi)

        mov['route_transits'] = route_transits
        mov['route_switches'] = route_switches
        mov['possible_OL_transits'] = possible_OL_transits
        mov['possible_OL_switches'] = possible_OL_switches

    return raw_movs


def overlapTrimmer(raw_movs, layout, m_OL, d_OL, s_OL):
    """Compute real overlap for each raw movement.

    Parameters
    ----------
    raw_movs : list
        List of dictionaries, each relative to a possible movement, including
        clones.
    layout : dict
        Description of the station's layout.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement, including
        clones. Overlaps sections processed (except logic OL).
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}

    raw_movs_OL_secs_OK = deepcopy(raw_movs)

    for mov in raw_movs_OL_secs_OK:
        sig_data = getSignalData(mov['destination'], layout)

        if sig_data is None:
            mov['OL_secs'] = []
            mov['OL_transits'] = []
            mov['OL_switches'] = []
            continue

        else:
            stop_pk = sig_data['pk']

        OL_secs = []
        OL_transits = []
        OL_switches = []

        for i in range(len(mov['possible_OL_path'])):

            if i == 0:
                critical_point = getMediatorNodePK(mov['route_secs'][-1],
                                                   mov['possible_OL_path'][i],
                                                   layout)

            else:
                critical_point = getMediatorNodePK(mov['possible_OL_path']
                                                   [i-1],
                                                   mov['possible_OL_path'][i],
                                                   layout)

            distance = abs(critical_point - stop_pk)

            if distance < OL_corresp[mov['type']]:

                if (mov['possible_OL_path'][i] not in blocks and
                        mov['possible_OL_path'][i] not in NDZs):
                    OL_secs.append(mov['possible_OL_path'][i])
                    OL_transits.append(mov['possible_OL_transits'][i])

                    for possible_OL_switch in mov['possible_OL_switches']:

                        if mov['possible_OL_path'][i] ==\
                                possible_OL_switch['sec_lbl']:
                            OL_switches.append(possible_OL_switch)

        mov['OL_secs'] = OL_secs
        mov['OL_transits'] = OL_transits
        mov['OL_switches'] = OL_switches

    return raw_movs_OL_secs_OK


def derailerAltOL(layout, unlbld_movs_no_der_alt_OL,
                  derailer_alt_OL_allowed_types, derailer_margin):
    """Create movements that have derailers set to normal in the overlap.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    unlbld_movs_no_der_alt_OL : list
        List of dictionaries, each relative to a possible movement
        (unlabeled and without movement which have derailers set to normal
         in the overlap).
    derailer_alt_OL_allowed_types : list
        List containing strings, each corresponding to a movement type for
        which alternative ovelaps with normally set derailers are allowed.
    derailer_margin : float
        Limit distance (of section with derailer) that can be anterior to the
        derailer point, while still considering the derailer excludes the
        section from overlap.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    """
    unlbld_movs = deepcopy(unlbld_movs_no_der_alt_OL)

    for mov in unlbld_movs_no_der_alt_OL:

        if mov['type'] not in derailer_alt_OL_allowed_types:
            continue

        OL_derailers = []

        for switch in mov['OL_switches']:
            swi_data = deepcopy(getSwitchData(layout, switch['SWI_lbl']))

            if swi_data['lr_pk'] is None:
                swi_data['excluded_secs'] = []
                OL_derailers.append(swi_data)

        for OL_derailer in OL_derailers:

            for OL_sec in mov['OL_secs']:

                OL_sec_idx = mov['OL_secs'].index(OL_sec)
                entry_node = mov['OL_transits'][OL_sec_idx][0]
                critical_point = getNodePK(entry_node, OL_sec, layout)

                if mov['direction'] == 'asc':

                    if (OL_derailer['point_pk'] <=
                            critical_point + derailer_margin):
                        OL_derailer['excluded_secs'].append(OL_sec)

                else:

                    if (OL_derailer['point_pk'] >=
                            critical_point - derailer_margin):
                        OL_derailer['excluded_secs'].append(OL_sec)

        for OL_derailer in OL_derailers:

            if OL_derailer['excluded_secs']:
                new_mov = deepcopy(mov)

                for excluded_sec in OL_derailer['excluded_secs']:

                    exc_sec_idx = new_mov['OL_secs'].index(excluded_sec)
                    new_mov['OL_transits'].pop(exc_sec_idx)
                    new_mov['OL_secs'].remove(excluded_sec)

                    OL_swis_to_remove = []

                    for OL_swi in new_mov['OL_switches']:

                        if OL_swi['SWI_lbl'] == OL_derailer['label']:
                            OL_swi['SWI_pos'] = '+'

                        elif OL_swi['sec_lbl'] == excluded_sec:
                            OL_swis_to_remove.append(OL_swi)

                    for OL_swi_to_remove in OL_swis_to_remove:
                        new_mov['OL_switches'].remove(OL_swi_to_remove)

                it_idx = unlbld_movs.index(mov)
                unlbld_movs.insert(it_idx, new_mov)

    return unlbld_movs


def antiMovClones(raw_movs_OL_secs_OK):
    """Remove cloned movs. (due to different path sections downstream of OL).

    Parameters
    ----------
    raw_movs_OL_secs_OK : list
        List of dictionaries, each relative to a possible movement, including
        clones. Overlaps sections processed (excep logic OL).

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (movements with locked distant OL switches might be
        included) (logic OL not processed).
    """
    inc_OL_movs = deepcopy(raw_movs_OL_secs_OK)
    clones = []

    for i in range(len(inc_OL_movs)):

        for j in range(len(inc_OL_movs)):

            if i != j:

                if inc_OL_movs[i] not in clones:

                    if (inc_OL_movs[i]['origin'] == inc_OL_movs[j]['origin']
                            and inc_OL_movs[i]['destination'] ==
                            inc_OL_movs[j]['destination'] and
                            inc_OL_movs[i]['route_secs'] == inc_OL_movs[j]
                            ['route_secs'] and
                            inc_OL_movs[i]['OL_secs'] ==
                            inc_OL_movs[j]['OL_secs'] and
                            inc_OL_movs[i]['route_transits'] ==
                            inc_OL_movs[j]['route_transits'] and
                            inc_OL_movs[i]['OL_transits'] ==
                            inc_OL_movs[j]['OL_transits'] and
                            inc_OL_movs[i]['OL_switches'] ==
                            inc_OL_movs[j]['OL_switches'] and
                            inc_OL_movs[i]['type'] == inc_OL_movs[j]['type']
                            and inc_OL_movs[i]['direction'] == inc_OL_movs[j]
                            ['direction'] and
                            inc_OL_movs[i] != inc_OL_movs[j]):
                        clones.append(inc_OL_movs[j])

    for clone in clones:
        inc_OL_movs.remove(clone)

    return inc_OL_movs


def antiDistantSwitchOL(inc_OL_movs, signals, layout, m_OL, d_OL, s_OL):
    """Remove movements with alt OL on switches further than the OL distance.

    Parameters
    ----------
    inc_OL_movs : list
        List of dictionaries, each relative to a possible movement. Overlaps
        processed (movements with locked distant OL switches might be
        included) (logic OL not processed).
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.
    layout : dict
        Description of the station's layout.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement. Overlaps
        processed (except logic OL).
    """
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}
    movs_to_remove = []
    no_logic_OL_movs = deepcopy(inc_OL_movs)

    for mov in no_logic_OL_movs:
        virtual_destination = (signals.loc[signals.signal == mov
                                           ['destination']].virtual.iloc
                               [0].item())
        OL_secs = mov['OL_secs']

        if not virtual_destination and OL_secs:

            stop_point = getSignalData(mov['destination'], layout)['pk']
            last_OL_sec = mov['OL_secs'][-1]
            last_OL_sec_trans = mov['OL_transits'][-1]
            OL_distance = OL_corresp[mov['type']]
            last_OL_sec_swis = []

            eff_swis_at_last_OL_sec = effectiveSwitches(last_OL_sec_trans,
                                                        last_OL_sec, layout)

            for switch in mov['OL_switches']:

                if switch['sec_lbl'] == last_OL_sec:
                    last_OL_sec_swis.append(switch)

            for eff_swi in eff_swis_at_last_OL_sec:
                distance = distToSwiPoint(stop_point, eff_swi['label'], layout)

                for switch2 in last_OL_sec_swis:

                    if switch2['SWI_lbl'] == eff_swi['label']:
                        swi_pos = switch2['SWI_pos']

                if distance > OL_distance and swi_pos == '-':
                    movs_to_remove.append(mov)

    for mov_to_remove in movs_to_remove:
        no_logic_OL_movs.remove(mov_to_remove)

    partialLock(no_logic_OL_movs, layout, m_OL, d_OL, s_OL)

    return no_logic_OL_movs


def partialLock(no_logic_OL_movs, layout, m_OL, d_OL, s_OL):
    """Apply section locking without section switch locking on relevant cases.

    Parameters
    ----------
    no_logic_OL_movs : list
        List of dictionaries, each relative to a possible movement. Overlaps
        processed (excep logic OL).
    layout : dict
        Description of the station's layout.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.
    """
    corresp = {'Main': m_OL,
               'DOS': d_OL,
               'Shunt': s_OL}

    for mov in no_logic_OL_movs:

        if mov['OL_switches']:
            stop_point = getSignalData(mov['destination'], layout)['pk']
            switches_to_remove = []

            for OL_switch in mov['OL_switches']:
                distance = distToSwiPoint(stop_point,
                                          OL_switch['SWI_lbl'],
                                          layout)

                if distance > corresp[mov['type']]:
                    switches_to_remove.append(OL_switch)

            for switch_to_remove in switches_to_remove:
                mov['OL_switches'].remove(switch_to_remove)


def distToSwiPoint(anchor, switch_lbl, layout):
    """Get the distance from an anchor point to a switch's point PK.

    Parameters
    ----------
    anchor : float
        PK of the point from which to measure the distance.
    switch_lbl : str
        Label of the switch.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    float
        Distance from the specified anchor point to the specified switch's
        point PK.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if switch['label'] == switch_lbl:
                    point_pk = switch['point_pk']

    distance = abs(anchor - point_pk)

    return distance


def getSwitchData(layout, switch_lbl):
    """Retrieve data referring to a specific switch.

    Parameters
    ----------
    switch_lbl : str
        Label of the switch.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    dict
        Dictionary containing the switch's data.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if switch['label'] == switch_lbl:

                    return switch


def getSignalData(sig_lbl, layout):
    """Retrieve data referring to a specific signal.

    Parameters
    ----------
    sig_lbl : str
        Label of the signal.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    dict
        Dictionary containing the signal's data.
    """
    for block in layout['blocks']:

        if block['signal'] is not None:

            if block['signal']['label'] == sig_lbl:

                return block['signal']

    for ndz in layout['NDZs']:

        if ndz['signal'] is not None:

            if ndz['signal']['label'] == sig_lbl:

                return ndz['signal']

    for section in layout['sections']:

        for node in section['nodes']:

            if node['signal'] is not None:

                if node['signal']['label'] == sig_lbl:

                    return node['signal']


def getNodePK(node_idx, section_lbl, layout):
    """Get PK of the specified node of a specified section.

    Parameters
    ----------
    node_idx : str
        Index of the node to be evaluated.
    section_lbl : str
        Label of the section to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    float
        PK of the specified node of a specified section.
    """
    for section in layout['sections']:

        if section['label'] == section_lbl:

            for node in section['nodes']:

                if node['index'][0] == node_idx:

                    return node['pk']


def getMediatorNodePK(element1, element2, layout):
    """Get PK of node between two sections.

    Parameters
    ----------
    element1 : str
        Label of the first element (can only be a section).
    element2 : str
        Label of the first element (can be section, block or NDZ).
    layout : dict
        Description of the station's layout.

    Returns
    -------
    float
        PK of the mediator node between the two specified elements.
    """
    for section in layout['sections']:

        if section['label'] == element1:

            for node in section['nodes']:

                if node['con_ele'] == element2:

                    return node['pk']


def effectiveSwitches(transit, section_lbl, layout):
    """Find effective (tip oriented) switches for a transit at a given section.

    Parameters
    ----------
    transit : str
        Transit to be considered.
    section_lbl : str
        Label of the section that is crossed by the specified transit.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of effective switches for the specified transit and section.
    """
    req_swis = requiredSwitches(layout, section_lbl, transit)

    for section in layout['sections']:

        if section['label'] == section_lbl:

            for node in section['nodes']:

                if node['index'][0] == transit[0]:

                    if node['index'][-1] == '-':
                        trans_dir = 'asc'
                        break

                    else:
                        trans_dir = 'desc'
                        break

            break

    effective_switches = []

    for req_swi in req_swis:

        if (req_swi['effective_direction'] == trans_dir or
                req_swi['effective_direction'] == 'bidirectional'):
            effective_switches.append(req_swi)

    return effective_switches


def altOLlabeler(unlbld_movs, layout):
    """Include alternative OL info in each movement.

    Parameters
    ----------
    unlbld_movs : list
        List of dictionaries, each relative to a possible movement
        (unlabeled).
    layout : dict
        Description of the station's layout.
    """
    alt_OL_movs = []
    captured = []

    for i in range(len(unlbld_movs)):

        if i in captured:
            continue

        for j in range(len(unlbld_movs)):

            if j in captured:
                continue

            if i != j:

                if (unlbld_movs[i]['origin'] == unlbld_movs[j]['origin'] and
                        unlbld_movs[i]['destination'] == unlbld_movs[j]
                        ['destination']
                        and unlbld_movs[i]['type'] == unlbld_movs[j]['type']
                        and unlbld_movs[i]['route_secs'] ==
                        unlbld_movs[j]['route_secs'] and
                        unlbld_movs[i]['OL_switches'] != unlbld_movs[j]
                        ['OL_switches']):

                    if unlbld_movs[i] not in alt_OL_movs:
                        alt_OL_movs.append(unlbld_movs[i])

                    if unlbld_movs[j] not in alt_OL_movs:
                        alt_OL_movs.append(unlbld_movs[j])

                    if i not in captured:
                        captured.append(i)

                    if j not in captured:
                        captured.append(j)

    for mov in unlbld_movs:
        index = unlbld_movs.index(mov)

        if mov in alt_OL_movs:
            alt_OL_lbl = ''

            for switch in mov['OL_switches']:
                swi_dta = getSwitchData(layout, switch['SWI_lbl'])

                if swi_dta['lr_pk'] is None and switch['SWI_pos'] == '+':

                    if len(alt_OL_lbl) > 0:
                        alt_OL_lbl += '/'

                    alt_OL_lbl += switch['SWI_lbl']
                    alt_OL_lbl += switch['SWI_pos']

                    continue

                swi_sec = switch['sec_lbl']
                OL_sec_index = mov['OL_secs'].index(swi_sec)
                OL_transit = mov['OL_transits'][OL_sec_index]

                effective_switches = effectiveSwitches(OL_transit,
                                                       swi_sec,
                                                       layout)
                effective_switches_labels = []

                for effective_switch in effective_switches:
                    effective_switches_labels.append(effective_switch['label'])

                if switch['SWI_lbl'] in effective_switches_labels:

                    if len(alt_OL_lbl) > 0:
                        alt_OL_lbl += '/'

                    alt_OL_lbl += switch['SWI_lbl']
                    alt_OL_lbl += switch['SWI_pos']

            unlbld_movs[index]['alt_OL'] = alt_OL_lbl

        else:
            unlbld_movs[index]['alt_OL'] = None


def altRouteLabeler(unlbld_movs, layout):
    """Include alternative route info in each movement.

    Parameters
    ----------
    unlbld_movs : list
        List of dictionaries, each relative to a possible movement
        (unlabeled).
    layout : dict
        Description of the station's layout.
    """
    for mov in unlbld_movs:
        mov['alt_route'] = None

    for i in range(len(unlbld_movs)):

        for j in range(len(unlbld_movs)):

            if (unlbld_movs[i]['origin'] == unlbld_movs[j]['origin'] and
                    unlbld_movs[i]['destination'] == unlbld_movs[j]
                    ['destination']
                    and unlbld_movs[i]['type'] == unlbld_movs[j]['type'] and
                    unlbld_movs[i]['route_switches'] != unlbld_movs[j]
                    ['route_switches']):

                switches_at_diff_pos =\
                    switchDifferences(unlbld_movs[j]['route_switches'],
                                      unlbld_movs[i]['route_switches'])
                unlbld_movs[j]['alt_route'] = switches_at_diff_pos

    for mov in unlbld_movs:

        if mov['alt_route'] is not None:

            for diff_swi in mov['alt_route']:

                for route_switch in mov['route_switches']:

                    if route_switch['SWI_lbl'] == diff_swi['SWI_lbl']:
                        section = route_switch['sec_lbl']

                trans = mov['route_transits'][mov['route_secs'].index(section)]
                effective_switches = effectiveSwitches(trans,
                                                       section,
                                                       layout)
                eff_swi_lbls = [swi['label'] for swi in effective_switches]

                if diff_swi['SWI_lbl'] not in eff_swi_lbls:
                    mov['alt_route'].remove(diff_swi)


def switchDifferences(swi_group_1, swi_group_2):
    """Return required switches common to both groups (at different positions).

    Parameters
    ----------
    swi_group_1 : list
        List of dictionaries, each relative to a required switch.
    swi_group_2 : list
        List of dictionaries, each relative to a required switch.

    Returns
    -------
    list
        List of dictionaries, each relative to a required switch that is common
        to both groups, but required at different positions in both groups.
    """
    switches_at_diff_pos = []

    for switch_1 in swi_group_1:

        for switch_2 in swi_group_2:

            if (switch_1['SWI_lbl'] == switch_2['SWI_lbl'] and
                    switch_1['SWI_pos'] != switch_2['SWI_pos']):

                switches_at_diff_pos.append(switch_1)

    return switches_at_diff_pos


def specialMovLabeler(unlbld_movs, layout):
    """Include special movement info on each movement's dictionary.

    Parameters
    ----------
    unlbld_movs : list
        List of dictionaries, each relative to a possible movement
        (unlabeled).
    layout : dict
        Description of the station's layout.
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]

    for mov in unlbld_movs:

        if (mov['destination'] in blocks and len(mov['destination']) == 4 and
                mov['type'] != 'Shunt'):
            blk_num = int(mov['destination'][-1])
            blk_num_even = True if blk_num % 2 == 0 else False

            if (mov['direction'] == 'asc' and blk_num_even or
                    mov['direction'] == 'desc' and not blk_num_even):
                mov['special'] = True

            else:
                mov['special'] = False

        elif mov['destination'] in NDZs and mov['type'] != 'Shunt':
            mov['special'] = True

        else:
            mov['special'] = False


def logicOL(no_logic_OL_movs, layout, viable_logic_OL,
            consider_swi_pnt_pk_logic_OL, m_OL, d_OL, s_OL):
    """Determine if logic OL is possible and add that info to each movement.

    Parameters
    ----------
    no_logic_OL_movs : list
        List of dictionaries, each relative to a possible movement. Overlaps
        processed (except logic OL).
    layout : dict
        Description of the station's layout.
    viable_logic_OL : list
        List containing the movement types for which logic OL is possible.
    consider_swi_pnt_pk_logic_OL : bool
        True if the existence of a effective switch in a OL section of a
        suitable movement does not invalidate logic OL, as long as the switch's
        point PK is at a threshold distance from the destination signal.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement
        (unlabeled and without movements which have derailers set to normal in
         the overlap).
    """
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    sections = [section['label'] for section in layout['sections']]
    unlbld_movs_no_der_alt_OL = deepcopy(no_logic_OL_movs)

    for mov in unlbld_movs_no_der_alt_OL:
        mov['logic_OL'] = False
        OL_distance = OL_corresp[mov['type']]

        if (mov['destination'] not in blocks and mov['destination'] not in NDZs
                and mov['destination'] not in sections):
            destination_pk = getSignalData(mov['destination'], layout)['pk']

            if mov['type'] in viable_logic_OL:
                logic_OL_possible = True

                for i in range(len(mov['OL_secs'])):
                    OL_sec = mov['OL_secs'][i]
                    OL_trans = mov['OL_transits'][i]
                    effective_switches = effectiveSwitches(OL_trans, OL_sec,
                                                           layout)

                    if effective_switches:
                        logic_OL_possible = False

                        if consider_swi_pnt_pk_logic_OL:
                            all_eff_swis_beyond_threshold = True

                            for effective_switch in effective_switches:
                                critical_pnt = effective_switch['point_pk']

                                if (abs(destination_pk - critical_pnt) <
                                        OL_distance):
                                    all_eff_swis_beyond_threshold = False

                            if all_eff_swis_beyond_threshold:
                                logic_OL_possible = True

                if logic_OL_possible:
                    mov['logic_OL'] = True

    return unlbld_movs_no_der_alt_OL


def aggregatedLabel(unlbld_movs):
    """Generate aggregated label for easy movement identification.

    Parameters
    ----------
    unlbld_movs : list
        List of dictionaries, each relative to a possible movement (unlabeled).
    """
    for mov in unlbld_movs:

        if mov['alt_route'] is None or mov['alt_route'] == []:
            alt_route_lbl_raw = None

        else:

            alt_route_lbl_raw = ''

            for diff_swi in mov['alt_route']:

                if len(alt_route_lbl_raw) > 0:
                    alt_route_lbl_raw += '/'

                alt_route_lbl_raw += diff_swi['SWI_lbl']
                alt_route_lbl_raw += diff_swi['SWI_pos']

        if mov['destination_alias'] is None:
            destination_lbl = mov['destination']

        else:
            destination_lbl = mov['destination_alias']

        if mov['origin_alias'] is None:
            origin_lbl = mov['origin']

        else:
            origin_lbl = mov['origin_alias']

        route_lbl = origin_lbl + '-' + destination_lbl
        alt_route_lbl = '(Alt_Rt: ' + alt_route_lbl_raw + ')'\
            if alt_route_lbl_raw is not None else ''
        alt_OL_lbl = '(Alt_OL: ' + mov['alt_OL'] + ')'\
            if mov['alt_OL'] is not None else ''
        type_lbl = mov['type']
        special_lbl = 'IE' if mov['special'] else ''

        labels = [type_lbl, special_lbl, alt_route_lbl, alt_OL_lbl]
        aggregated_label = route_lbl + ' '

        for label in labels:

            if aggregated_label[-1] != ' ' and label != '':
                aggregated_label += ' '

            aggregated_label += label

        mov['label'] = aggregated_label


def movLabeler(unlbld_movs, layout, signals):
    """Add labels to movement dictionaries.

    Parameters
    ----------
    unlbld_movs : list
        List of dictionaries, each relative to a possible movement (unlabeled).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement.
        Unconsolidated structure.
    """
    unconsolidated_movs = deepcopy(unlbld_movs)
    altOLlabeler(unconsolidated_movs, layout)
    altRouteLabeler(unconsolidated_movs, layout)
    specialMovLabeler(unconsolidated_movs, layout)
    altOrigOrDest(signals, unconsolidated_movs, layout)
    aggregatedLabel(unconsolidated_movs)

    return unconsolidated_movs


def movConsolidator(unconsolidated_movs, keep_aux_data=True):
    """Rearange the movement dictionaries, prioritizing the most relevant info.

    Parameters
    ----------
    unconsolidated_movs : list
        List of dictionaries, each relative to a possible movement.
        Unconsolidated structure.
    keep_aux_data : bool
        True if auxiliary data is to be kepk on the movements dictionary,
        False otherwise.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement (without
        flank protection sections and switches).
    """
    raw_movements = []

    for mov in unconsolidated_movs:
        it_dict = {}
        it_dict['label'] = mov['label']
        it_dict['origin'] = {'literal': mov['origin'],
                             'alias': mov['origin_alias']}
        it_dict['destination'] = {'literal': mov['destination'],
                                  'alias': mov['destination_alias']}
        it_dict['type'] = mov['type']
        it_dict['direction'] = mov['direction']
        it_dict['logic_overlap'] = mov['logic_OL']
        it_dict['special'] = mov['special']
        it_dict['sections'] = {'route': mov['route_secs'],
                               'overlap': mov['OL_secs']}
        it_dict['transits'] = {'route': mov['route_transits'],
                               'overlap': mov['OL_transits']}
        it_dict['switches'] = {'route': mov['route_switches'],
                               'overlap': mov['OL_switches']}

        if keep_aux_data:
            it_dict['aux'] = {'path_index': mov['path_index'],
                              'possible_OL_path': mov['possible_OL_path'],
                              'possible_OL_transits':
                                  mov['possible_OL_transits'],
                              'possible_OL_switches':
                                  mov['possible_OL_switches'],
                              'alt_OL': mov['alt_OL'],
                              'alt_route':
                                  mov['alt_route'] if mov['alt_route']
                                  != [] else None}

        raw_movements.append(deepcopy(it_dict))

    return raw_movements


def getConnectedSection(section_lbl, node_idx, layout):
    """Return element connected to a section by a certain node.

    Parameters
    ----------
    section_lbl : str
        Label of the section to be evaluated.
    node_idx : str
        Index of the node to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Label of the element connected to the specified section at the
        specified node.
    """
    for section in layout['sections']:

        if section['label'] == section_lbl:

            for node in section['nodes']:

                if node['index'][0] == node_idx:

                    return node['con_ele']


def secHasSwis(sec_lbl, layout):
    """Know if a section has at least one switch (inc. derailer).

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the section has at least one switch, False otherwise.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:

            for node in section['nodes']:

                if node['switches']:

                    return True

            return False


def altOrigOrDest(signals, unconsolidated_movs, layout):
    """Process movements departing/arriving to signals with origin indicator.

    Parameters
    ----------
    unconsolidated_movs : list
        List of dictionaries, each relative to a possible movement.
        Unconsolidated structure.
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.
    """
    for mov in unconsolidated_movs:

        alt_orig_or_dest = False
        dest_sig = mov['destination']
        final_park_sec = mov['route_secs'][-1]
        dest_sig_data = signals.loc[signals.signal == dest_sig]\
            .loc[signals.prev_sec == final_park_sec]

        if bool(dest_sig_data.alt_origin.iloc[0]):
            alt_orig_or_dest = True
            dest_alias = dest_sig + '(' + final_park_sec + ')'
            mov['destination_alias'] = dest_alias

        orig_sig = mov['origin']
        init_park_sec = getConnectedSection(mov['route_secs'][0],
                                            mov['route_transits'][0][0],
                                            layout)
        orig_sig_data = signals.loc[signals.signal == orig_sig]\
            .loc[signals.prev_sec == init_park_sec]

        if bool(orig_sig_data.alt_origin.iloc[0]):
            alt_orig_or_dest = True
            orig_alias = orig_sig + '(' + init_park_sec + ')'
            mov['origin_alias'] = orig_alias

        if alt_orig_or_dest:
            rt_secs_w_swi = deepcopy(mov['route_secs'])
            to_remove = []

            for rt_sec_w_swi in rt_secs_w_swi:

                if not secHasSwis(rt_sec_w_swi, layout):
                    to_remove.append(rt_sec_w_swi)

            for sec_to_remove in to_remove:
                rt_secs_w_swi.remove(sec_to_remove)

            alt_rt_swis_to_remove = []

            for alt_rt_swi in mov['alt_route']:

                if (alt_rt_swi['SWI_lbl'] != rt_secs_w_swi[0] and
                        alt_rt_swi['SWI_lbl'] != rt_secs_w_swi[-1]):
                    alt_rt_swis_to_remove.append(alt_rt_swi)

            for alt_rt_swi in mov['alt_route']:

                if alt_rt_swi in alt_rt_swis_to_remove:
                    mov['alt_route'].remove(alt_rt_swi)
