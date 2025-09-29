"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""
#INCOMPLETE

from modules.spatialEngine import impossibleTransits
from modules.router import getSwitchData
from copy import deepcopy


def flankProtection(raw_movements, layout, signals, shunt_sig_filters_fp):
    """Find sections and switches required for flank protection of movements.

    Parameters
    ----------
    raw_movements : list
        List of dictionaries, each relative to a possible movement (without
        flank protection required sections and switches).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement.
    """
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


def flankProtectionPROTO(raw_movements, layout, signals, shunt_sig_filters_fp,
                         vital_FP_threshold, sub_vital_FP_threshold,
                         remote_FP_threshold):
    """Find sections and switches required for flank protection of movements.

    Parameters
    ----------
    raw_movements : list
        List of dictionaries, each relative to a possible movement (without
        flank protection required sections and switches).
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible movement.
    """
    movements = deepcopy(raw_movements)

    for movement in movements:

        FP_secs_trans_O1 = flankProtectionSecsAndTransO1(movement,
                                                         layout,
                                                         signals,
                                                         shunt_sig_filters_fp)
        FP_secs_trans = higherLevelFPsecsAndTrans(FP_secs_trans_O1,
                                                  layout,
                                                  signals,
                                                  shunt_sig_filters_fp)
        movement['aux']['FP_secs_trans'] = FP_secs_trans
        flankProtectionGeometricEngine(movement, layout, vital_FP_threshold,
                                       sub_vital_FP_threshold,
                                       remote_FP_threshold)

    return movements


def getSwitchOrder(swi_lbl, sec_lbl, layout):
    """Find the order of a switch (# of nodes thar require the switch at -).

    Parameters
    ----------
    swi_lbl : str
        Label of the switch.
    sec_lbl : str
        Label of the section where the switch is located.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    int
        Order of the specified switch.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    order = 0

    for node in section['nodes']:
        switches = [switch['label'] for switch in node['switches']]

        if swi_lbl in switches:
            order += 1

    return order


def collisionPointAlgo(sec_lbl, req_swis, eval_req_swi, vuln_nde_idx, layout):
    """Find the point of collision for a switch/vulnerable node pair.

    Parameters
    ----------
    sec_lbl : str
        Label of the section where the switch is located.
    req_swis : list
        Required switches for the associated transit.
    eval_req_swi : dict
        Required switch to be evaluated.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    float, None
        PK of the collision point or None if there is no association between
        the specified vulnerable node and the specified switch.
    """
    nested_sec = False

    for section in layout['sections']:

        if section['label'] == sec_lbl:

            if section['special_type'] == 'nested':
                nested_sec = True

    vuln_nde = getNdeInfo(sec_lbl, vuln_nde_idx, layout)

    if eval_req_swi['SWI_pos'] == '+':

        for switch in vuln_nde['switches']:

            if switch['label'] == eval_req_swi['SWI_lbl']:
                return getSwitchData(layout, switch['label'])['lr_pk']

        return

    else:
        reverse_req_swis = []

        for req_swi in req_swis:

            if req_swi['SWI_pos'] == '-':
                reverse_req_swis.append(req_swi)

        reverse_req_swis_lbls = [switch['SWI_lbl'] for switch in
                                 reverse_req_swis]

        for switch in vuln_nde['switches']:

            if switch['label'] not in reverse_req_swis_lbls:
                return

        if eval_req_swi['SWI_lbl'] in [switch['label'] for switch in
                                       vuln_nde['switches']]:
            return

        eval_req_swi_order = getSwitchOrder(eval_req_swi['SWI_lbl'],
                                            sec_lbl,
                                            layout)

        if nested_sec:
            if (eval_req_swi_order != len(vuln_nde['switches']) and
                    eval_req_swi_order + len(vuln_nde['switches']) != 2):
                return

        return getSwitchData(layout, eval_req_swi['SWI_lbl'])['lr_pk']


def syntheticRequiredSwitches(sec_lbl, layout):
    """Create list containing dicts for every switch at a section, at + and -.

    Parameters
    ----------
    sec_lbl : str
        Label of the section where the switches are located.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    list
        List of dictionaries, each relative pair relative to a switch in the
        specified section. One of the dicts corresponds to the normal position
        and the other to the reverse position.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    synthetic_req_swis = []

    for node in section['nodes']:

        for switch in node['switches']:
            synthetic_req_swis.append({'SWI_lbl': switch['label'],
                                       'SWI_pos': '+',
                                       'sec_lbl': sec_lbl})
            synthetic_req_swis.append({'SWI_lbl': switch['label'],
                                       'SWI_pos': '-',
                                       'sec_lbl': sec_lbl})

    return synthetic_req_swis


def getExitNdePKAndDirection(sec_lbl, transit, layout):
    """Get exit node PK and direction for a transit at a specified section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to consider.
    transit : str
        Transit to consider at the specified section.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    float, string
        PK of the transit exit node and string "asc" if the transit goes in the
        increasing PK direction, "desc" otherwise.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == transit[0]:
            entry_pk = node['pk']

        elif node['index'][0] == transit[-1]:
            exit_pk = node['pk']

    direction = 'asc' if exit_pk > entry_pk else 'desc'

    return exit_pk, direction


def flankProtectionGeometricEngine(movement, layout, vital_FP_threshold,
                                   sub_vital_FP_threshold,
                                   remote_FP_threshold):
    """Add geometric considerations to the FP main dictionary.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specifi movement.
    layout : dict
        Station's layout with explicit node signs.
    vital_FP_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered vital.
    sub_vital_FP_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered sub_vital.
    remote_FP_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered remote.
    """
    for key in ['route', 'OL']:
        fp_dict = movement['aux']['FP_secs_trans'][key]

        for sec_to_protect_dict in fp_dict:
            req_swis = syntheticRequiredSwitches(sec_to_protect_dict
                                                 ['sec_to_protect'],
                                                 layout)

            for vulnerable_nde_dict in sec_to_protect_dict['vulnerable_ndes']:
                collision_pnt = None

                for req_swi in req_swis:
                    collision_pnt_cand = collisionPointAlgo(sec_to_protect_dict
                                                            ['sec_to_protect'],
                                                            req_swis,
                                                            req_swi,
                                                            vulnerable_nde_dict
                                                            ['nde_idx'],
                                                            layout)

                    if collision_pnt_cand is not None:
                        collision_pnt = collision_pnt_cand

                vulnerable_nde_dict['collision_pnt'] = collision_pnt

                for dang_sec in vulnerable_nde_dict['dangerous_secs']:
                    min_dist = 1000000

                    for dang_trans in dang_sec['dangerous_transits']:
                        exit_pk, direction = getExitNdePKAndDirection(
                            dang_sec['sec_lbl'], dang_trans, layout)

                        if direction == 'asc':
                            dist = collision_pnt - exit_pk

                        else:
                            dist = exit_pk - collision_pnt

                        if dist < min_dist:
                            min_dist = dist

                    flag = 'no_FP'

                    if dist <= remote_FP_threshold:
                        flag = 'remote'

                    if dist <= sub_vital_FP_threshold:
                        flag = 'sub_vital'

                    if dist <= vital_FP_threshold:
                        flag = 'vital'

                    dang_sec['flag'] = flag


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
        Signal table containing the possible movement types departing from
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


def getNodeSignalPossDest(sec_lbl, nde_idx, layout, signals):
    """Get movement types that can have a signal at a node as destination.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    nde_idx : str
        Index of the node where a relevant signal might exist.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.

    Returns
    -------
    str
        String containing the first letter of the movement types that can have
        the relevant signal as a destination. If there is no signal at the
        specified node, or the signal can not be a destination of movements,
        the returned string is empty.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:
            break

    if node['signal'] is None:
        return ''

    else:
        sig_data = signals.loc[signals.signal == node['signal']['label']]
        return sig_data.possible_destination.iloc[0]


def getNdeInfo(sec_lbl, nde_idx, layout):
    """Get the main dictionary relative to a specified node.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    nde_idx : str
        Index of the node where a relevant signal might exist.
    layout : dict
        Station's layout with explicit node signs.

    Returns
    -------
    dict
        Dictionary containing relevant info on the specified node.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:
            return node


def higherLevelFPsecsAndTransAlgo(FP_secs_trans_O1, layout, signals,
                                  shunt_sig_filters_fp):
    """Add FP sections of the immediately higher order.

    Parameters
    ----------
    FP_secs_trans_O1 : dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Only first order FP sections are computed, and
        distances to LR PKs are not considered.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.
    """
    for sec_to_prot in FP_secs_trans_O1:

        for vuln_nde_O1 in sec_to_prot['vulnerable_ndes']:

            for dang_sec_O1 in vuln_nde_O1['dangerous_secs']:
                sec_lbl = dang_sec_O1['sec_lbl']
                pot_vuln_ndes = [dang_trans[0] for dang_trans in
                                 dang_sec_O1['dangerous_transits']]
                new_dang_secs = []

                for pot_vuln_nde in pot_vuln_ndes:
                    nde_sig_poss_dest = getNodeSignalPossDest(sec_lbl,
                                                              pot_vuln_nde,
                                                              layout,
                                                              signals)

                    if (nde_sig_poss_dest == '' or (nde_sig_poss_dest == 'S'
                                                    and not
                                                    shunt_sig_filters_fp)):
                        node_info = getNdeInfo(sec_lbl, pot_vuln_nde, layout)
                        new_dang_sec = getDangerousSection(sec_lbl,
                                                           node_info,
                                                           layout)
                        new_dang_secs.append(new_dang_sec)

            for new_dang_sec in new_dang_secs:
                vuln_nde_O1['dangerous_secs'].append(new_dang_sec)


def higherLevelFPsecsAndTrans(FP_secs_trans_O1, layout, signals,
                              shunt_sig_filters_fp):
    """Complete the FP_secs_trans_O1 dict, adding FP sections of higher order.

    Parameters
    ----------
    FP_secs_trans_O1 : dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Only first order FP sections are computed, and
        distances to LR PKs are not considered.
    layout : dict
        Station's layout with explicit node signs.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.

    Returns
    -------
    dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Distances to LR PKs are not considered.
    """
    FP_secs_trans = deepcopy(FP_secs_trans_O1)

    while True:
        ini_version = deepcopy(FP_secs_trans)
        higherLevelFPsecsAndTransAlgo(FP_secs_trans['route'], layout,
                                      signals, shunt_sig_filters_fp)

        if ini_version == FP_secs_trans:
            break

    while True:
        ini_version = deepcopy(FP_secs_trans)
        higherLevelFPsecsAndTransAlgo(FP_secs_trans['OL'], layout, signals,
                                      shunt_sig_filters_fp)

        if ini_version == FP_secs_trans:
            return FP_secs_trans


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
        Signal table containing the possible movement types departing from
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
                                            ['label']].possible_destination.iloc[0]

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
