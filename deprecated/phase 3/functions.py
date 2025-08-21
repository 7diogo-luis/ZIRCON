""" Discontinued code."""


def isDerailer(label, layout):
    """Find if a switch is a derailer.

    Parameters
    ----------
    label : str
        Label of the switch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the switch is a derailer, False if not.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if label == switch['label'] and switch['lr_pk'] is None:

                    return True

    return False


def getSwitchSection(label, layout):
    """Get the section where a switch (inc. derailer) lies.

    Parameters
    ----------
    label : str
        Label of the switch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Label of the section where the evaluated switch lies.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if label == switch['label']:

                    return section['label']


def consecSwitch(path, switch_pos, layout, adjacency_data, no_derailer=True):
    """Find if a path crosses more than one switch at a certain position.

    Parameters
    ----------
    path : dict
        Dictionary containing the sections crossed by a given path, as well
           as the respective transits.
    switch_pos : str
        Relevant switch position.
    layout : dict
        Description of the station's layout.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.
    no_derailer : bool
        True if derailers are to be ignored, False otherwise

    Returns
    -------
    list
        List of lists, each representing a streak of crossed sections where a
        point commanded in the relevant position exists.
    """
    consec = []
    temp = []

    for com_swi in path['switch_positions']:

        if not (isDerailer(com_swi['SWI_lbl'], layout) and no_derailer):
            nxt_sec = getSwitchSection(com_swi['SWI_lbl'], layout)

            if com_swi['SWI_pos'] == switch_pos:

                if temp:

                    if isContiguous(temp[-1], nxt_sec, adjacency_data):
                        temp.append(nxt_sec)

                    elif temp[-1] == nxt_sec:
                        pass

                    else:

                        if len(temp) > 1:
                            consec.append(temp)
                        temp = []
                        temp.append(nxt_sec)

                else:
                    temp.append(nxt_sec)

            else:

                if temp:

                    if temp[-1] == nxt_sec:
                        pass

                    elif len(temp) > 1:
                        consec.append(temp)

                temp = []

    if len(temp) > 1:
        consec.append(temp)

    return consec


def ITSortingMetrics(it, layout, signals):
    
    blocks = [block['label'] for block in layout['blocks']]
    blocks.sort()
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    NDZs.sort()
    sections = [section['label'] for section in layout['sections']]
    sections.sort()
    blocks_NDZs_sections = blocks + NDZs + sections
    blocks_NDZs_sections.sort()
    ILMs = []

    for sig in list(signals['signal']):

        if 'M_' in sig:
            ILMs.append(sig)

    ILMs.sort()

    if it['type'] == 'Shunt':
        regime = 0
        opposite_track = None
        it['opposite_track'] = None
        entrance = None
        it['entrance'] = None
        ori_sig = extractSigNum(it['origin'], 'shunt')

        if 'M_' in it['destiny']:
            retrograde = 1
            it['retrograde'] = False
            dest_sig = ILMs.index(it['destiny'])

        else:
            retrograde = 0
            it['retrograde'] = True
            dest_sig = extractSigNum(it['destiny'], 'shunt')

    else:
        regime = 1
        retrograde = None
        it['retrograde'] = None
        ori_sig = extractSigNum(it['origin'], 'circ')

        if ((it['special'] and it['destiny'] not in NDZs) or
                'SC' in it['destiny'] or
                'SC' in it['origin']):
            opposite_track = 0
            it['opposite_track'] = True

        else:
            opposite_track = 1
            it['opposite_track'] = False

        if (it['destiny'] in blocks_NDZs_sections or
                'STA' in it['destiny'] or
                'STD' in it['destiny']):

            if it['destiny'] not in sections:
                entrance = 0
                it['entrance'] = False

            else:
                entrance = 1
                it['entrance'] = True

            try:
                dest_sig = blocks_NDZs_sections.index(it['destiny'])

            except ValueError:
                dest_sig = 0

        else:
            entrance = 1
            it['entrance'] = True
            dest_sig = blocks_NDZs_sections.index(it['destiny'])

    if it['alt_route']:
        alt = 0

    else:
        alt = 1

    if it['type'] == 'DOS':
        dos = 0

    else:
        dos = 1

    if it['alt_OL'] is not None:

        if '-' in it['alt_OL']:
            alt_ol = 0
        else:
            alt_ol = 1

    else:
        alt_ol = 1

    if it['direction'] == 'desc':
        direction = 0

    else:
        direction = 1

    return {'regime': regime,
            'opposite_track': opposite_track,
            'retrograde': retrograde,
            'entrance': entrance,
            'direction': direction,
            'alt': alt,
            'dos': dos,
            'alt_ol': alt_ol,
            'ori_sig': ori_sig,
            'dest_sig': dest_sig}


def ITSorter(its, layout, signals):
    
    rank = 0
    sorted_its = deepcopy(its)

    for it in sorted_its:
        metrics = ITSortingMetrics(it, layout, signals)
        
        if it['type'] != 'Shunt':
            rank += metrics['opposite_track'] * 1000000
            rank += metrics['entrance'] * 100000
            rank += metrics['direction'] * 10000
            

        it['rank'] = rank

    sorted_its = sorted(sorted_its, key=lambda sorted_its: sorted_its['rank'])
    sorted_its = sorted_its[::-1]

    return sorted_its


m = []
d = []
s = []
for it in its:
    if it['direction'] == 'asc':
        if it['type'] == 'Main':
            m.append(it['lbl'])
        elif it['type'] == 'DOS':
            d.append(it['lbl'])
        elif it['type'] == 'Shunt':
            s.append(it['lbl'])
for it in its:
    if it['direction'] == 'desc':
        if it['type'] == 'Main':
            m.append(it['lbl'])
        elif it['type'] == 'DOS':
            d.append(it['lbl'])
        elif it['type'] == 'Shunt':
            s.append(it['lbl'])


def extractSigNum(sig_lbl, regime):
    """Extract number associated with signal from label.

    Parameters
    ----------
    sig_lbl : str
        Label of the signal.
    regime : str
        Relevant regime ('circ'' (circulation) or 'shunt'').

    Returns
    -------
    int
        Number associated with the specified signal and regime.
    """
    corresp = {'circ': 'C' if 'SC' in sig_lbl else 'S',
               'shunt': 'M'}

    extracted = ''
    read = False

    for char in sig_lbl:

        try:
            int(char)

        except ValueError:
            read = False

        if read:
            extracted += char

        if char == corresp[regime]:
            read = True

    return int(extracted)