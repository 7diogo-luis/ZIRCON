"""ZIRCON Router."""

from copy import deepcopy
from modules.spatialEngine import requiredSwitches


def router(paths, signals, layout, m_OL, d_OL, s_OL, viable_logic_OL,
           consider_swi_pnt_pk_logic_OL, allow_distant_switch_OL_lock,
           derailer_alt_OL_allowed_types, derailer_margin):
    """Compute possible itineraries and basic info regarding each.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary (without
        flank protection sections).
    """
    raw_its_incomplete = ITFinder(paths, signals, layout)
    raw_its = addSwiAndTrans(raw_its_incomplete, paths)
    raw_its_OL_secs_OK = overlapTrimmer(raw_its, layout, m_OL, d_OL, s_OL)
    inc_OL_its = antiITClones(raw_its_OL_secs_OK)

    if not allow_distant_switch_OL_lock:
        no_logic_OL_its = antiDistantSwitchOL(inc_OL_its, signals, layout,
                                              m_OL, d_OL, s_OL)

    else:
        no_logic_OL_its = inc_OL_its

    unlbld_its_no_der_alt_OL = logicOL(no_logic_OL_its, layout,
                                       viable_logic_OL,
                                       consider_swi_pnt_pk_logic_OL,
                                       m_OL, d_OL, s_OL)
    unlbld_its = derailerAltOL(layout, unlbld_its_no_der_alt_OL,
                               derailer_alt_OL_allowed_types, derailer_margin)
    unconsolidated_its = ITLabeler(unlbld_its, layout, signals)
    raw_movements = ITConsolidator(unconsolidated_its)

    return raw_movements


def ITFinder(paths, signals, layout):
    """Find all possible itineraries in the station.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary, including
        clones. No info on transits or switch positions.
    """
    raw_its_incomplete = []
    it = {'path_index': None,
          'direction': None,
          'origin': None,
          'destiny': None,
          'origin_alias': None,
          'destiny_alias': None,
          'type': None,
          'route_secs': None,
          'possible_OL_path': None}
    section_labels = [section['label'] for section in layout['sections']]
    block_labels = [block['label'] for block in layout['blocks']]
    NDZ_labels = [ndz['label'] for ndz in layout['NDZs']]

    for IT_type in ['Main', 'DOS', 'Shunt']:

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

                        if IT_type[0] in possible_origin:
                            new_candidates.append(possible_new_candidates[j])

                else:

                    for k in range(len(possible_new_candidates)):
                        possible_destiny =\
                            signals.loc[signals.signal ==
                                        possible_new_candidates[k]].\
                            possible_destiny.iloc[0]

                        if IT_type[0] in possible_destiny:
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

                        for destiny_sig in new_candidates:

                            new_it = deepcopy(it)

                            new_it['path_index'] = i
                            new_it['direction'] = direction
                            new_it['origin'] = origin_sig
                            new_it['destiny'] = destiny_sig

                            if ('M_' in destiny_sig or
                                (IT_type == 'Shunt' and 'M'
                                 not in destiny_sig and destiny_sig not in
                                 section_labels and destiny_sig not in
                                 block_labels and destiny_sig not in
                                 NDZ_labels)):
                                new_it['destiny_alias'] =\
                                    signals.loc[signals.signal == destiny_sig]\
                                    .prev_sec.iloc[0]

                            new_it['type'] = IT_type
                            new_it['route_secs'] = route_secs

                            last_route_sec_idx = sections.index(route_secs[-1])
                            possible_OL_path =\
                                sections[last_route_sec_idx + 1:]
                            new_it['possible_OL_path'] = possible_OL_path

                            raw_its_incomplete.append(new_it)

                    candidates = []
                    route_secs = []
                    route_secs.append(section)

                    for sig in new_candidates:
                        candidates.append(sig)

    return raw_its_incomplete


def addSwiAndTrans(raw_its_incomplete, paths):
    """Include relevant transits and switch positions associated with each IT.

    Parameters
    ----------
    raw_its_incomplete : list
        List of dictionaries, each relative to a possible itinerary, including
        clones. No info on transits or switch positions.
    paths : list
        List of all possible paths in the station.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary, including
        clones.
    """
    raw_its = deepcopy(raw_its_incomplete)

    for it in raw_its:
        route_transits = []
        route_switches = []
        possible_OL_transits = []
        possible_OL_switches = []
        path = paths[it['path_index']]

        for route_sec in it['route_secs']:

            index = path['path_secs'].index(route_sec)
            transit = path['path_transits'][index]
            route_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == route_sec:
                    route_switches.append(com_swi)

        for possible_OL_sec in it['possible_OL_path']:

            index = path['path_secs'].index(possible_OL_sec)
            transit = path['path_transits'][index]
            possible_OL_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == possible_OL_sec:
                    possible_OL_switches.append(com_swi)

        it['route_transits'] = route_transits
        it['route_switches'] = route_switches
        it['possible_OL_transits'] = possible_OL_transits
        it['possible_OL_switches'] = possible_OL_switches

    return raw_its


def overlapTrimmer(raw_its, layout, m_OL, d_OL, s_OL):
    """Compute real overlap.

    Parameters
    ----------
    raw_its : list
        List of dictionaries, each relative to a possible itinerary, including
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
        List of dictionaries, each relative to a possible itinerary, including
        clones. Overlaps sections processed (excep logic OL).
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}

    raw_its_OL_secs_OK = deepcopy(raw_its)

    for it in raw_its_OL_secs_OK:
        sig_data = getSignalData(it['destiny'], layout)

        if sig_data is None:
            it['OL_secs'] = []
            it['OL_transits'] = []
            it['OL_switches'] = []
            continue

        else:
            stop_pk = sig_data['pk']

        OL_secs = []
        OL_transits = []
        OL_switches = []

        for i in range(len(it['possible_OL_path'])):

            if i == 0:
                critical_point = getMediatorNodePk(it['route_secs'][-1],
                                                   it['possible_OL_path'][i],
                                                   layout)

            else:
                critical_point = getMediatorNodePk(it['possible_OL_path'][i-1],
                                                   it['possible_OL_path'][i],
                                                   layout)

            distance = abs(critical_point - stop_pk)

            if distance < OL_corresp[it['type']]:

                if (it['possible_OL_path'][i] not in blocks and
                        it['possible_OL_path'][i] not in NDZs):
                    OL_secs.append(it['possible_OL_path'][i])
                    OL_transits.append(it['possible_OL_transits'][i])

                    for possible_OL_switch in it['possible_OL_switches']:

                        if it['possible_OL_path'][i] ==\
                                possible_OL_switch['sec_lbl']:
                            OL_switches.append(possible_OL_switch)

        it['OL_secs'] = OL_secs
        it['OL_transits'] = OL_transits
        it['OL_switches'] = OL_switches

    return raw_its_OL_secs_OK


def derailerAltOL(layout, unlbld_its_no_der_alt_OL,
                  derailer_alt_OL_allowed_types, derailer_margin):
    """Create movements that have normal derailers in overlap.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    unlbld_its_no_der_alt_OL : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled and without itineraries witch have derailers set to normal
         in the overlap).
    derailer_alt_OL_allowed_types : list
        List containing strings, each corresponding to a itinerary type for
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
    unlbld_its = deepcopy(unlbld_its_no_der_alt_OL)

    for it in unlbld_its_no_der_alt_OL:

        if it['type'] not in derailer_alt_OL_allowed_types:
            continue

        OL_derailers = []

        for switch in it['OL_switches']:
            swi_data = deepcopy(getSwitchData(layout, switch['SWI_lbl']))

            if swi_data['lr_pk'] is None:
                swi_data['excluded_secs'] = []
                OL_derailers.append(swi_data)

        for OL_derailer in OL_derailers:

            for OL_sec in it['OL_secs']:

                OL_sec_idx = it['OL_secs'].index(OL_sec)
                entry_node = it['OL_transits'][OL_sec_idx][0]
                critical_point = getNodePk(entry_node, OL_sec, layout)

                if it['direction'] == 'asc':

                    if (OL_derailer['point_pk'] <=
                            critical_point + derailer_margin):
                        OL_derailer['excluded_secs'].append(OL_sec)

                else:

                    if (OL_derailer['point_pk'] >=
                            critical_point - derailer_margin):
                        OL_derailer['excluded_secs'].append(OL_sec)

        for OL_derailer in OL_derailers:

            if OL_derailer['excluded_secs']:
                new_it = deepcopy(it)

                for excluded_sec in OL_derailer['excluded_secs']:

                    exc_sec_idx = new_it['OL_secs'].index(excluded_sec)
                    new_it['OL_transits'].pop(exc_sec_idx)
                    new_it['OL_secs'].remove(excluded_sec)

                    OL_swis_to_remove = []

                    for OL_swi in new_it['OL_switches']:

                        if OL_swi['SWI_lbl'] == OL_derailer['label']:
                            OL_swi['SWI_pos'] = '+'

                        elif OL_swi['sec_lbl'] == excluded_sec:
                            OL_swis_to_remove.append(OL_swi)

                    for OL_swi_to_remove in OL_swis_to_remove:
                        new_it['OL_switches'].remove(OL_swi_to_remove)

                it_idx = unlbld_its.index(it)
                unlbld_its.insert(it_idx, new_it)

    return unlbld_its


def antiITClones(raw_its_OL_secs_OK):
    """Remove cloned ITs (due to different path sections downstream of OL).

    Parameters
    ----------
    raw_its_OL_secs_OK : list
        List of dictionaries, each relative to a possible itinerary, including
        clones. Overlaps sections processed (excep logic OL).

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (itineraries with locked distant OL switches might be
        included) (logic OL not processed).
    """
    inc_OL_its = deepcopy(raw_its_OL_secs_OK)
    clones = []

    for i in range(len(inc_OL_its)):

        for j in range(len(inc_OL_its)):

            if i != j:

                if inc_OL_its[i] not in clones:

                    if (inc_OL_its[i]['origin'] == inc_OL_its[j]['origin'] and
                            inc_OL_its[i]['destiny'] ==
                            inc_OL_its[j]['destiny'] and
                            inc_OL_its[i]['route_secs'] == inc_OL_its[j]
                            ['route_secs'] and
                            inc_OL_its[i]['OL_secs'] ==
                            inc_OL_its[j]['OL_secs'] and
                            inc_OL_its[i]['route_transits'] ==
                            inc_OL_its[j]['route_transits'] and
                            inc_OL_its[i]['OL_transits'] ==
                            inc_OL_its[j]['OL_transits'] and
                            inc_OL_its[i]['OL_switches'] ==
                            inc_OL_its[j]['OL_switches'] and
                            inc_OL_its[i]['type'] == inc_OL_its[j]['type'] and
                            inc_OL_its[i]['direction'] == inc_OL_its[j]
                            ['direction'] and inc_OL_its[i] != inc_OL_its[j]):
                        clones.append(inc_OL_its[j])

    for clone in clones:
        inc_OL_its.remove(clone)

    return inc_OL_its


def antiDistantSwitchOL(inc_OL_its, signals, layout, m_OL, d_OL, s_OL):
    """Remove ITs with alt OLs on switches with point further than OL distance.

    Parameters
    ----------
    inc_OL_its : list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (itineraries with locked distant OL switches might be
        included) (logic OL not processed).
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    layout : dict
        Station's layout with explicit node signs.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (excep logic OL).
    """
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}
    its_to_remove = []
    no_logic_OL_its = deepcopy(inc_OL_its)

    for it in no_logic_OL_its:
        virtual_destiny = signals.loc[signals.signal == it['destiny']]\
            .virtual.iloc[0].item()
        OL_secs = it['OL_secs']

        if not virtual_destiny and OL_secs:

            stop_point = getSignalData(it['destiny'], layout)['pk']
            last_OL_sec = it['OL_secs'][-1]
            last_OL_sec_trans = it['OL_transits'][-1]
            OL_distance = OL_corresp[it['type']]
            last_OL_sec_swis = []

            eff_swis_at_last_OL_sec = effectiveSwitches(last_OL_sec_trans,
                                                        last_OL_sec, layout)

            for switch in it['OL_switches']:

                if switch['sec_lbl'] == last_OL_sec:
                    last_OL_sec_swis.append(switch)

            for eff_swi in eff_swis_at_last_OL_sec:
                distance = distToSwiPoint(stop_point, eff_swi['label'], layout)

                for switch2 in last_OL_sec_swis:

                    if switch2['SWI_lbl'] == eff_swi['label']:
                        swi_pos = switch2['SWI_pos']

                if distance > OL_distance and swi_pos == '-':
                    its_to_remove.append(it)

    for it_to_remove in its_to_remove:
        no_logic_OL_its.remove(it_to_remove)

    partialLock(no_logic_OL_its, layout, m_OL, d_OL, s_OL)

    return no_logic_OL_its


def partialLock(no_logic_OL_its, layout, m_OL, d_OL, s_OL):
    """Remove ITs with alt OLs on switches with point further than OL distance.

    Parameters
    ----------
    no_logic_OL_its : list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (excep logic OL).
    layout : dict
        Station's layout with explicit node signs.
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

    for it in no_logic_OL_its:

        if it['OL_switches']:
            stop_point = getSignalData(it['destiny'], layout)['pk']
            switches_to_remove = []

            for OL_switch in it['OL_switches']:
                distance = distToSwiPoint(stop_point,
                                          OL_switch['SWI_lbl'],
                                          layout)

                if distance > corresp[it['type']]:
                    switches_to_remove.append(OL_switch)

            for switch_to_remove in switches_to_remove:
                it['OL_switches'].remove(switch_to_remove)


def distToSwiPoint(anchor, switch_lbl, layout):
    """Get the distance from an anchor pointo to a switch's point.

    Parameters
    ----------
    anchor : float
        Pk of the point from which to measure the distance.
    switch_lbl : str
        Label of the switch.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    float
        Distance from the specified anchor point to the specified switch's
        point.
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


def getNodePk(node_idx, section_lbl, layout):
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


def getMediatorNodePk(element1, element2, layout):
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


def altOLlabeler(unlbld_its, layout):
    """Include alternative OL info in each IT.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    layout : dict
        Description of the station's layout.
    """
    alt_OL_its = []
    captured = []

    for i in range(len(unlbld_its)):

        if i in captured:
            continue

        for j in range(len(unlbld_its)):

            if j in captured:
                continue

            if i != j:

                if (unlbld_its[i]['origin'] == unlbld_its[j]['origin'] and
                        unlbld_its[i]['destiny'] == unlbld_its[j]['destiny']
                        and unlbld_its[i]['type'] == unlbld_its[j]['type'] and
                        unlbld_its[i]['route_secs'] ==
                        unlbld_its[j]['route_secs'] and
                        unlbld_its[i]['OL_switches'] != unlbld_its[j]
                        ['OL_switches']):

                    if unlbld_its[i] not in alt_OL_its:
                        alt_OL_its.append(unlbld_its[i])

                    if unlbld_its[j] not in alt_OL_its:
                        alt_OL_its.append(unlbld_its[j])

                    if i not in captured:
                        captured.append(i)

                    if j not in captured:
                        captured.append(j)

    for it in unlbld_its:
        index = unlbld_its.index(it)

        if it in alt_OL_its:
            alt_OL_lbl = ''

            for switch in it['OL_switches']:
                swi_dta = getSwitchData(layout, switch['SWI_lbl'])

                if swi_dta['lr_pk'] is None and switch['SWI_pos'] == '+':

                    if len(alt_OL_lbl) > 0:
                        alt_OL_lbl += '/'

                    alt_OL_lbl += switch['SWI_lbl']
                    alt_OL_lbl += switch['SWI_pos']

                    continue

                swi_sec = switch['sec_lbl']
                OL_sec_index = it['OL_secs'].index(swi_sec)
                OL_transit = it['OL_transits'][OL_sec_index]

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

            unlbld_its[index]['alt_OL'] = alt_OL_lbl

        else:
            unlbld_its[index]['alt_OL'] = None


def altRouteLabeler(unlbld_its, layout):
    """Include alternative route info in each IT.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    layout : dict
        Description of the station's layout.
    """
    for it in unlbld_its:
        it['alt_route'] = None

    for i in range(len(unlbld_its)):

        for j in range(len(unlbld_its)):

            if (unlbld_its[i]['origin'] == unlbld_its[j]['origin'] and
                    unlbld_its[i]['destiny'] == unlbld_its[j]['destiny']
                    and unlbld_its[i]['type'] == unlbld_its[j]['type'] and
                    unlbld_its[i]['route_switches'] != unlbld_its[j]
                    ['route_switches']):

                switches_at_diff_pos =\
                    switchDifferences(unlbld_its[j]['route_switches'],
                                      unlbld_its[i]['route_switches'])
                unlbld_its[j]['alt_route'] = switches_at_diff_pos

    for it in unlbld_its:

        if it['alt_route'] is not None:

            for diff_swi in it['alt_route']:

                for route_switch in it['route_switches']:

                    if route_switch['SWI_lbl'] == diff_swi['SWI_lbl']:
                        section = route_switch['sec_lbl']

                transit = it['route_transits'][it['route_secs'].index(section)]
                effective_switches = effectiveSwitches(transit,
                                                       section,
                                                       layout)
                eff_swi_lbls = [swi['label'] for swi in effective_switches]

                if diff_swi['SWI_lbl'] not in eff_swi_lbls:
                    it['alt_route'].remove(diff_swi)


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


def specialITLabeler(unlbld_its, layout):
    """Include special IT info on each IT.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    layout : dict
        Station's layout with explicit node signs.
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]

    for it in unlbld_its:

        if (it['destiny'] in blocks and len(it['destiny']) == 4 and
                it['type'] != 'Shunt'):
            blk_num = int(it['destiny'][-1])
            blk_num_even = True if blk_num % 2 == 0 else False

            if (it['direction'] == 'asc' and blk_num_even or
                    it['direction'] == 'desc' and not blk_num_even):
                it['special'] = True

            else:
                it['special'] = False

        elif it['destiny'] in NDZs and it['type'] != 'Shunt':
            it['special'] = True

        else:
            it['special'] = False


def logicOL(no_logic_OL_its, layout, viable_logic_OL,
            consider_swi_pnt_pk_logic_OL, m_OL, d_OL, s_OL):
    """Determine if logic OL is possible and add that info to each IT.

    Parameters
    ----------
    no_logic_OL_its : list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (excep logic OL).
    layout : dict
        Description of the station's layout.
    viable_logic_OL : list
        List containing the itinerary types for which logic OL is possible.
    consider_swi_pnt_pk_logic_OL : bool
        True if the existance of a effective switch in a OL section of a
        suitable IT is not to invalidate logic OL, as long as the switch's
        point pk is at a threshhold distance from the destination signal.
    m_OL : float
        Overlap distance for Main itineraries.
    d_OL : float
        Overlap distance for DOS itineraries.
    s_OL : float
        Overlap distance for Shunt itineraries.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled and without itineraries witch have derailers set to normal
         in the overlap).
    """
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    sections = [section['label'] for section in layout['sections']]
    unlbld_its_no_der_alt_OL = deepcopy(no_logic_OL_its)

    for it in unlbld_its_no_der_alt_OL:
        it['logic_OL'] = False
        OL_distance = OL_corresp[it['type']]

        if (it['destiny'] not in blocks and it['destiny'] not in NDZs and
                it['destiny'] not in sections):
            destination_pk = getSignalData(it['destiny'], layout)['pk']

            if it['type'] in viable_logic_OL:
                logic_OL_possible = True

                for i in range(len(it['OL_secs'])):
                    OL_sec = it['OL_secs'][i]
                    OL_trans = it['OL_transits'][i]
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
                    it['logic_OL'] = True

    return unlbld_its_no_der_alt_OL


def aggregatedLabel(unlbld_its):
    """Generate aggregated label for easy IT identification.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    """
    for it in unlbld_its:

        if it['alt_route'] is None or it['alt_route'] == []:
            alt_route_lbl_raw = None

        else:

            alt_route_lbl_raw = ''

            for diff_swi in it['alt_route']:

                if len(alt_route_lbl_raw) > 0:
                    alt_route_lbl_raw += '/'

                alt_route_lbl_raw += diff_swi['SWI_lbl']
                alt_route_lbl_raw += diff_swi['SWI_pos']

        if it['destiny_alias'] is None:
            destiny_lbl = it['destiny']

        else:
            destiny_lbl = it['destiny_alias']

        if it['origin_alias'] is None:
            origin_lbl = it['origin']

        else:
            origin_lbl = it['origin_alias']

        route_lbl = origin_lbl + '-' + destiny_lbl
        alt_route_lbl = '(Alt_Rt: ' + alt_route_lbl_raw + ')'\
            if alt_route_lbl_raw is not None else ''
        alt_OL_lbl = '(Alt_OL: ' + it['alt_OL'] + ')'\
            if it['alt_OL'] is not None else ''
        type_lbl = it['type']
        special_lbl = 'IE' if it['special'] else ''

        labels = [type_lbl, special_lbl, alt_route_lbl, alt_OL_lbl]
        aggregated_label = route_lbl + ' '

        for label in labels:

            if aggregated_label[-1] != ' ' and label != '':
                aggregated_label += ' '

            aggregated_label += label

        it['label'] = aggregated_label


def ITLabeler(unlbld_its, layout, signals):
    """Add labels to itinerary dictionaries.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary.
        Unconsolidated structure.
    """
    unconsolidated_its = deepcopy(unlbld_its)
    altOLlabeler(unconsolidated_its, layout)
    altRouteLabeler(unconsolidated_its, layout)
    specialITLabeler(unconsolidated_its, layout)
    altOrigOrDest(signals, unconsolidated_its, layout)
    aggregatedLabel(unconsolidated_its)

    return unconsolidated_its


def ITConsolidator(unconsolidated_its, keep_aux_data=False):
    """Rearange the IT dictionaries, prioritizing the most relevant info.

    Parameters
    ----------
    unconsolidated_its : list
        List of dictionaries, each relative to a possible itinerary.
        Unconsolidated structure.
    keep_aux_data : bool
        True if auxiliary data is to be kepk on the movements dictionary,
        else False.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary (without
        flank protection sections).
    """
    raw_movements = []

    for it in unconsolidated_its:
        it_dict = {}
        it_dict['label'] = it['label']
        it_dict['origin'] = {'literal': it['origin'],
                             'alias': it['origin_alias']}
        it_dict['destination'] = {'literal': it['destiny'],
                                  'alias': it['destiny_alias']}
        it_dict['type'] = it['type']
        it_dict['direction'] = it['direction']
        it_dict['logic_overlap'] = it['logic_OL']
        it_dict['sections'] = {'route': it['route_secs'],
                               'overlap': it['OL_secs']}
        it_dict['transits'] = {'route': it['route_transits'],
                               'overlap': it['OL_transits']}
        it_dict['switches'] = {'route': it['route_switches'],
                               'overlap': it['OL_switches']}

        if keep_aux_data:
            it_dict['aux'] = {'path_index': it['path_index'],
                              'possible_OL_path': it['possible_OL_path'],
                              'possible_OL_transits':
                                  it['possible_OL_transits'],
                              'possible_OL_switches':
                                  it['possible_OL_switches'],
                              'alt_OL': it['alt_OL'],
                              'alt_route':
                                  it['alt_route'] if it['alt_route']
                                  != [] else None,
                              'special': it['special']}

        raw_movements.append(deepcopy(it_dict))

    return raw_movements


def getConnectedSection(section_lbl, node_idx, layout):
    """Return element connected to section by a certain node.

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


def altOrigOrDest(signals, unconsolidated_its, layout):
    """Process its departing from or arriving to signals with origin indicator.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    """
    for it in unconsolidated_its:

        alt_orig_or_dest = False
        dest_sig = it['destiny']
        final_park_sec = it['route_secs'][-1]
        dest_sig_data = signals.loc[signals.signal == dest_sig]\
            .loc[signals.prev_sec == final_park_sec]

        if bool(dest_sig_data.alt_origin.iloc[0]):
            alt_orig_or_dest = True
            dest_alias = dest_sig + '(' + final_park_sec + ')'
            it['destiny_alias'] = dest_alias

        orig_sig = it['origin']
        init_park_sec = getConnectedSection(it['route_secs'][0],
                                            it['route_transits'][0][0],
                                            layout)
        orig_sig_data = signals.loc[signals.signal == orig_sig]\
            .loc[signals.prev_sec == init_park_sec]

        if bool(orig_sig_data.alt_origin.iloc[0]):
            alt_orig_or_dest = True
            orig_alias = orig_sig + '(' + init_park_sec + ')'
            it['origin_alias'] = orig_alias

        if alt_orig_or_dest:
            rt_secs_w_swi = deepcopy(it['route_secs'])
            to_remove = []

            for rt_sec_w_swi in rt_secs_w_swi:

                if not secHasSwis(rt_sec_w_swi, layout):
                    to_remove.append(rt_sec_w_swi)

            for sec_to_remove in to_remove:
                rt_secs_w_swi.remove(sec_to_remove)

            alt_rt_swis_to_remove = []

            for alt_rt_swi in it['alt_route']:

                if (alt_rt_swi['SWI_lbl'] != rt_secs_w_swi[0] and
                        alt_rt_swi['SWI_lbl'] != rt_secs_w_swi[-1]):
                    alt_rt_swis_to_remove.append(alt_rt_swi)

            for alt_rt_swi in it['alt_route']:

                if alt_rt_swi in alt_rt_swis_to_remove:
                    it['alt_route'].remove(alt_rt_swi)
