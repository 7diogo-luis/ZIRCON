"""ZIRCON Router."""

from copy import deepcopy


def router(paths, signals, layout, m_OL, d_OL, s_OL, allow_logic_OL,
           viable_logic_OL, consider_swi_pnt_pk, point_pk_threshold):
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
        List of dictionaries, each relative to a possible itinerary.
    """
    raw_its = ITFinder(paths, signals, layout)
    raw_its_OL_OK = overlapTrimmer(raw_its, layout, m_OL, d_OL, s_OL)
    inc_its = antiITClones(raw_its_OL_OK)
    its_wo_logic_OL = addSwiAndTrans(inc_its, paths)
    unlbld_its = logicOL(its_wo_logic_OL, layout, allow_logic_OL,
                         viable_logic_OL, consider_swi_pnt_pk,
                         point_pk_threshold)
    its = ITLabeler(unlbld_its, layout)

    return its


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
        clones.
    """
    raw_its = []
    it = {'path_index': None,
          'direction': None,
          'origin': None,
          'destiny': None,
          'type': None,
          'route_secs': None,
          'possible_OL_path': None}

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
                                              prev_sec)]
                    .signal)

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
                            new_it['type'] = IT_type
                            new_it['route_secs'] = route_secs

                            last_route_sec_idx = sections.index(route_secs[-1])
                            possible_OL_path =\
                                sections[last_route_sec_idx + 1:]
                            new_it['possible_OL_path'] = possible_OL_path

                            raw_its.append(new_it)

                    candidates = []
                    route_secs = []
                    route_secs.append(section)

                    for sig in new_candidates:
                        candidates.append(sig)

    return raw_its


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
    effective_switches_candidates = []
    found_sec = False
    oposite_sign_nodes = 0

    for section in layout['sections']:

        if section['label'] == section_lbl:

            found_sec = True

            for node in section['nodes']:

                if node['index'][0] == transit[0]:
                    sign = node['index'][-1]
                    through_branch = True if node['switches'] else False
                    through_wk_nde = node['TJS_weak_nde']
                    entry_pk = node['pk']

                if node['index'][0] == transit[1]:
                    exit_pk = node['pk']

            for node in section['nodes']:

                if (node['index'][-1] != sign and
                        not (node['TJS_weak_nde'] and through_branch) and
                        not through_wk_nde):
                    oposite_sign_nodes += 1

        if oposite_sign_nodes > 1:

            for node in section['nodes']:

                if node['index'][-1] != sign and node['switches']:

                    for switch in node['switches']:
                        effective_switches_candidates.append(switch)

        if found_sec:
            break

    effective_switches = []

    for effective_switches_candidate in effective_switches_candidates:

        if (entry_pk < effective_switches_candidate['point_pk'] < exit_pk or
                exit_pk < effective_switches_candidate['point_pk'] < entry_pk):
            effective_switches.append(effective_switches_candidate)

    return effective_switches


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
    raw_its_OL_OK : list
        List of dictionaries, each relative to a possible itinerary, including
        clones. Overlaps processed (excep logic OL).
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    OL_corresp = {'Main': m_OL,
                  'DOS': d_OL,
                  'Shunt': s_OL}

    raw_its_OL_OK = deepcopy(raw_its)

    for it in raw_its_OL_OK:
        sig_data = getSignalData(it['destiny'], layout)

        if sig_data is None:
            it['OL_secs'] = []
            continue

        else:
            stop_pk = sig_data['pk']

        OL_secs = []

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

        it['OL_secs'] = OL_secs

    return raw_its_OL_OK


def addSwiAndTrans(inc_its, paths):
    """Include relevant transits and switch positions associated with each IT.

    Parameters
    ----------
    inc_its : list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (excep logic OL).
    paths : list
        List of all possible paths in the station.
    """
    its_wo_logic_OL = deepcopy(inc_its)

    for it in its_wo_logic_OL:
        route_transits = []
        route_switches = []
        OL_transits = []
        OL_switches = []
        path = paths[it['path_index']]

        for route_sec in it['route_secs']:

            index = path['path_secs'].index(route_sec)
            transit = path['path_transits'][index]
            route_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == route_sec:
                    route_switches.append(com_swi)

        for OL_sec in it['OL_secs']:

            index = path['path_secs'].index(OL_sec)
            transit = path['path_transits'][index]
            OL_transits.append(transit)

            for com_swi in path['switch_positions']:

                if com_swi['sec_lbl'] == OL_sec:
                    OL_switches.append(com_swi)

        it['route_transits'] = route_transits
        it['route_switches'] = route_switches
        it['OL_transits'] = OL_transits
        it['OL_switches'] = OL_switches

    return its_wo_logic_OL


def altOLlabeler(unlbld_its):
    """Include alternative OL info on each IT.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
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

                if len(alt_OL_lbl) > 0:
                    alt_OL_lbl += '/'

                alt_OL_lbl += switch['SWI_lbl']
                alt_OL_lbl += switch['SWI_pos']

            unlbld_its[index]['alt_OL'] = alt_OL_lbl

        else:
            unlbld_its[index]['alt_OL'] = None


def altRouteLabeler(unlbld_its):
    """Include alternative route info on each IT.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).
    """
    alt_route_its = []
    captured = []
    group_indices = []
    not_alt = []

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
                        unlbld_its[i]['route_switches'] != unlbld_its[j]
                        ['route_switches']):

                    if unlbld_its[i] not in alt_route_its:
                        alt_route_its.append(unlbld_its[i])
                        group_indices.append([i])

                    if unlbld_its[j] not in alt_route_its:
                        alt_route_its.append(unlbld_its[j])
                        group_indices[-1].append(j)

                    if i not in captured:
                        captured.append(i)

                    if j not in captured:
                        captured.append(j)

    for group in group_indices:
        rev_swi_counts = []

        for index in group:
            it = unlbld_its[index]
            count = 0

            for route_switch in it['route_switches']:

                if route_switch['SWI_pos'] == '-':
                    count += 1

            rev_swi_counts.append(count)

        not_alt.append(group[rev_swi_counts.index(max(rev_swi_counts))])

    for it in unlbld_its:
        index = unlbld_its.index(it)

        if it in alt_route_its and index not in not_alt:

            unlbld_its[index]['alt_route'] = True

        else:
            unlbld_its[index]['alt_route'] = False


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


def logicOL(its_wo_logic_OL, layout, allow_logic_OL, viable_logic_OL,
            consider_swi_pnt_pk, point_pk_threshold):
    """Determine if logic OL is possible and add that info to each IT.

    Parameters
    ----------
    its : list
        List of dictionaries, each relative to a possible itinerary.
    layout : dict
        Description of the station's layout.
    allow_logic_OL : bool
        True if logic OL is to be allowed, False otherwise.
    viable_logic_OL : list
        List containing the itinerary types for which logic OL is possible.
    consider_swi_pnt_pk : bool
        True if the existance of a effective switch in a OL section of a
        suitable IT is not to invalidate logic OL, as long as the switch's
        point pk is at athreshhold distance from the destination signal.
    point_pk_threshold : float
        In case consider_swi_pnt_pk is true, the threshold distance from the
        destination signal and the effective point pk (if the measured distance
        is smaller than the threshold, logic_OL is invalidated).
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    sections = [section['label'] for section in layout['sections']]
    unlbld_its = deepcopy(its_wo_logic_OL)

    for it in unlbld_its:
        it['logic_OL'] = False

        if (it['destiny'] not in blocks and it['destiny'] not in NDZs and
                it['destiny'] not in sections):
            destination_pk = getSignalData(it['destiny'], layout)['pk']

            if it['type'] in viable_logic_OL and allow_logic_OL:
                logic_OL_possible = True

                for i in range(len(it['OL_secs'])):
                    OL_sec = it['OL_secs'][i]
                    OL_trans = it['OL_transits'][i]
                    effective_switches = effectiveSwitches(OL_trans, OL_sec,
                                                           layout)

                    if effective_switches:
                        logic_OL_possible = False

                        if consider_swi_pnt_pk:
                            all_eff_swis_beyond_threshold = True

                            for effective_switch in effective_switches:
                                critical_pnt = effective_switch['point_pk']

                                if (abs(destination_pk - critical_pnt) <
                                        point_pk_threshold):
                                    all_eff_swis_beyond_threshold = False

                            if all_eff_swis_beyond_threshold:
                                logic_OL_possible = True

                if logic_OL_possible:
                    it['logic_OL'] = True

    return unlbld_its


def antiITClones(raw_its_OL_OK):
    """Remove cloned ITs (due to different path sections downstream of OL).

    Parameters
    ----------
    raw_its_OL_OK : list
        List of dictionaries, each relative to a possible itinerary, including
        clones. Overlaps processed (excep logic OL).

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary. Overlaps
        processed (excep logic OL).
    """
    inc_its = deepcopy(raw_its_OL_OK)
    clones = []

    for i in range(len(inc_its)):

        for j in range(len(inc_its)):

            if i != j:

                if inc_its[i] not in clones:

                    if (inc_its[i]['origin'] == inc_its[j]['origin'] and
                            inc_its[i]['destiny'] == inc_its[j]['destiny'] and
                            inc_its[i]['route_secs'] == inc_its[j]
                            ['route_secs'] and
                            inc_its[i]['possible_OL_path'] ==
                            inc_its[j]['possible_OL_path'] and
                            inc_its[i]['type'] == inc_its[j]['type'] and
                            inc_its[i]['direction'] == inc_its[j]
                            ['direction'] and inc_its[i] != inc_its[j]):
                        clones.append(inc_its[j])

    for clone in clones:
        inc_its.remove(clone)

    return inc_its


def ITLabeler(unlbld_its, layout):
    """Add labels to itinerary dictionaries.

    Parameters
    ----------
    unlbld_its : list
        List of dictionaries, each relative to a possible itinerary
        (unlabeled).

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary.
    """
    its = deepcopy(unlbld_its)

    altOLlabeler(its)
    altRouteLabeler(its)
    specialITLabeler(its, layout)

    return its
