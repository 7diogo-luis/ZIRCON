"""ZIRCON Flank Protection Engine."""
#INCOMPLETE

from modules.spatialEngine import impossibleTransits
from copy import deepcopy


def flankProtection(raw_movements, layout, signals, shunt_sig_filters_fp):
    
    movements = deepcopy(raw_movements)

    for movement in movements:

        movement['sections']['flank_prot'] = {'route': {'vital': [],
                                                        'sub_vital': [],
                                                        'remote': []},
                                              'overlap': {'vital': [],
                                                          'sub_vital': [],
                                                          'remote': []}}

        movement['switches']['flank_prot'] = {'route': [],
                                              'overlap': []}

    return movements


def flankProtectionSecsAndTransO1(raw_movement, layout, signals,
                                  shunt_sig_filters_fp):
    """Find sections required for FP for a given movement.

    Parameters
    ----------
    raw_movement : dict
        Main dictionary containing data relative to a certain movement.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.

    Returns
    -------
    dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Only first order FP sections are computed, and
        distances to LR PKs are not considered.
    """
    fp_route_secs = []
    fp_OL_secs = []

    for i in range(len(raw_movement['sections']['route'])):
        sec_lbl = raw_movement['sections']['route'][i]
        transit = raw_movement['transits']['route'][i]
        vulnerable_nodes = vulnerableNodes(sec_lbl, transit, layout,
                                           signals, shunt_sig_filters_fp)

        if not vulnerable_nodes:
            continue

        vulnerable_ndes = []

        for vulnerable_node in vulnerable_nodes:

            dangerous_secs = [getDangerousSection(sec_lbl,
                                                  vulnerable_node,
                                                  layout)]
            vul_nde_dict = {'nde_idx': vulnerable_node['index'][0],
                            'dangerous_secs': dangerous_secs}
            vulnerable_ndes.append(vul_nde_dict)

            fp_sec = {'sec_to_protect': sec_lbl,
                      'vulnerable_ndes': vulnerable_ndes}

        fp_route_secs.append(fp_sec)

    for i in range(len(raw_movement['sections']['overlap'])):
        sec_lbl = raw_movement['sections']['overlap'][i]
        transit = raw_movement['transits']['overlap'][i]
        vulnerable_nodes = vulnerableNodes(sec_lbl, transit, layout,
                                           signals, shunt_sig_filters_fp)

        if not vulnerable_nodes:
            continue

        vulnerable_ndes = []

        for vulnerable_node in vulnerable_nodes:

            dangerous_secs = [getDangerousSection(sec_lbl,
                                                  vulnerable_node,
                                                  layout)]
            vul_nde_dict = {'nde_idx': vulnerable_node['index'][0],
                            'dangerous_secs': dangerous_secs}
            vulnerable_ndes.append(vul_nde_dict)

            fp_sec = {'sec_to_protect': sec_lbl,
                      'vulnerable_ndes': vulnerable_ndes}

        fp_OL_secs.append(fp_sec)

    return {'route': fp_route_secs,
            'OL': fp_OL_secs}


def vulnerableNodes(sec_lbl, transit, layout, signals, shunt_sig_filters_fp):
    """Find vulnerable nodes for a transit in a certain section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    transit : str
        Transit on the evaluated section.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.

    Returns
    -------
    list
        List of dictionaries, each containing info on a vulnerable node, or an
        empty list if there are no vulnerable nodes.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    vulnerable_nodes = []

    for node in section['nodes']:

        if node['index'][0] not in transit:

            if node['signal'] is None and node['con_ele'] is not None:

                vulnerable_nodes.append(node)

            else:
                sig_poss_dest = signals.loc[signals.signal == node['signal']
                                            ['label']].possible_destiny.iloc[0]

                if (sig_poss_dest == '' or (sig_poss_dest == 'S' and not
                                            shunt_sig_filters_fp)):
                    vulnerable_nodes.append(node)

    return vulnerable_nodes


def getDangerousSection(sec_lbl, vulnerable_node, layout):
    """Find a dangerous section for a certain section with a vulnerable node.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    vulnerable_node : dict
        Node info relative to the evaluated section's vulnerable node.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    dict
        Dictionary containing the label of the dangerous section and the
        corresponding dangerous transits.
    """
    block_labels = [block['label'] for block in layout['blocks']]
    NDZ_labels = [ndz['label'] for ndz in layout['NDZs']]

    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    nde_idx = section['nodes'].index(vulnerable_node)
    con_ele = section['nodes'][nde_idx]['con_ele']

    if con_ele not in block_labels and con_ele not in NDZ_labels:

        mediator_node = mediatorNode(con_ele, section['label'], layout)
        dangerous_transits = possibleTransitsToNode(con_ele,
                                                    mediator_node['index']
                                                    [0], layout)

    return {'sec_lbl': con_ele,
            'dangerous_transits': dangerous_transits}


def mediatorNode(section_1, section_2, layout):
    """Find the node of section_1 that connects to section_2.

    Parameters
    ----------
    section_1 : str
        Section of which the node will be extracted.
    section_2 : str
        Section connected to section_1.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    list
        Node of section_1 that connects to section_2.
    """
    for section in layout['sections']:

        if section['label'] == section_1:
            break

    for node in section['nodes']:

        if node['con_ele'] == section_2:
            return node


def possibleTransitsToNode(sec_lbl, nde_idx, layout):
    """Find possible transits to a node of a section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    nde_idx : str
        Index of the node to which relevant transits can exist.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    list
        List of strings, each being a possible transit on the specified
        section, to the specified node.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    imp_trans = impossibleTransits(layout)

    for node in section['nodes']:

        if node['index'][0] == nde_idx:
            nde_sign = node['index'][-1]
            break

    pos_trans_to_nde = []

    for node in section['nodes']:

        if node['index'][-1] != nde_sign:
            impossible = False
            candidate_transit = node['index'][0] + nde_idx

            for imp_trans_case in imp_trans:

                if (imp_trans_case['section'] == sec_lbl and
                        candidate_transit in imp_trans_case['imp_trans']):
                    impossible = True

            if not impossible:
                pos_trans_to_nde.append(candidate_transit)

    return pos_trans_to_nde
