"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from modules.spatialEngine import impossibleTransits, requiredSwitches
from modules.router import effectiveSwitches
from copy import deepcopy


def flankProtection(raw_movements, layout, signals, paths,
                    shunt_sig_filters_fp, vital_fp_threshold,
                    sub_vital_fp_threshold, remote_fp_threshold):
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
    vital_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered vital.
    sub_vital_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered sub_vital.
    remote_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered remote.

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
                                                  shunt_sig_filters_fp,
                                                  movement)
        movement['aux']['FP_secs_trans'] = FP_secs_trans
        flankProtectionGeometricEngine(movement, layout, vital_fp_threshold,
                                       sub_vital_fp_threshold,
                                       remote_fp_threshold)
        addFPreqSwis(movement, layout, paths)
        proto_FP_data = purgeFPsections(movement, layout, paths)
        assembleFPdicts(movement, proto_FP_data, layout)

    return movements


def getSwitchSection(SWI_lbl, layout):
    """Get the label of the section where a specified switch lies.

    Parameters
    ----------
    SWI_lbl : str
        Label of the switch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Label of the section where a specified switch lies.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if switch['label'] == SWI_lbl:
                    return section['label']


def assembleFPdicts(mov, proto_FP_data, layout):
    """Transfer relevant FP data to the proper locations.

    Parameters
    ----------
    mov : dict
        Dictionary containing info relating to a specific movement.
    proto_FP_data : dict
        Dictionary containing FP data in an intermediate format.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Label of the section where a specified switch lies.
    """
    mov['sections']['flank_prot'] = {'route': {'vital': [],
                                               'sub_vital': [],
                                               'remote': []},
                                     'overlap': {'vital': [],
                                                 'sub_vital': [],
                                                 'remote': []}}

    mov['switches']['flank_prot'] = {'route': [],
                                     'overlap': []}

    for req_swi in proto_FP_data['req_swis']:

        if req_swi['type'] == 'route':
            temp = {'SWI_lbl': req_swi['label'],
                    'SWI_pos': req_swi['SWI_pos'],
                    'sec_lbl': getSwitchSection(req_swi['label'], layout)}
            mov['switches']['flank_prot']['route'].append(temp)

        else:
            temp = {'SWI_lbl': req_swi['label'],
                    'SWI_pos': req_swi['SWI_pos'],
                    'sec_lbl': getSwitchSection(req_swi['label'], layout)}
            mov['switches']['flank_prot']['overlap'].append(temp)

    for vital_req_sec in proto_FP_data['vital_req_secs']:

        if vital_req_sec['type'] == 'route':
            temp = vital_req_sec['sec_lbl']
            mov['sections']['flank_prot']['route']['vital'].append(temp)

        else:
            temp = vital_req_sec['sec_lbl']
            mov['sections']['flank_prot']['overlap']['vital'].append(temp)

    for sub_vital_req_sec in proto_FP_data['sub_vital_req_secs']:

        if sub_vital_req_sec['type'] == 'route':
            temp = sub_vital_req_sec['sec_lbl']
            mov['sections']['flank_prot']['route']['sub_vital'].append(temp)

        else:
            temp = sub_vital_req_sec['sec_lbl']
            mov['sections']['flank_prot']['overlap']['sub_vital'].append(temp)

    for remote_req_sec in proto_FP_data['remote_req_secs']:

        if remote_req_sec['type'] == 'route':
            temp = remote_req_sec['sec_lbl']
            mov['sections']['flank_prot']['route']['remote'].append(temp)

        else:
            temp = remote_req_sec['sec_lbl']
            mov['sections']['flank_prot']['overlap']['remote'].append(temp)


def getSectionDerailers(sec_lbl, layout):
    """Get all derailers in a specified section.

    Parameters
    ----------
    sec_lbl : string
        Label of the section to evaluate.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each corresponding to a derailer in the specified
        section.
    """
    derailers = []

    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        for switch in node['switches']:

            if switch['lr_pk'] is None:
                derailers.append(deepcopy(switch))

    return derailers


def lockDerailerInCrossedSection(movement, layout):
    """Lock not required derailers in crossed sections in the normal position.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specific movement.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each corresponding to a derailer that must be
        locked in the normal position, for flank protection, for the specified
        movement.
    """
    derailers_to_lock = []

    for key in ['route', 'overlap']:

        for section in movement['sections'][key]:
            derailers = getSectionDerailers(section, layout)
            idx = movement['sections'][key].index(section)
            transit = movement['transits'][key][idx]
            req_swis = requiredSwitches(layout, section, transit)

            for derailer in derailers:

                if derailer not in req_swis:
                    derailer['SWI_pos'] = '+'

                    if key == 'route':
                        derailer['type'] = key

                    else:
                        derailer['type'] = 'OL'

                    derailers_to_lock.append(derailer)

    return derailers_to_lock


def secsConByMed(sec_lbl_1, sec_lbl_2, mediator_sec_lbl, layout):
    """Know if two section are connected by a third (mediator) section.

    Parameters
    ----------
    sec_lbl_1 : str
        Label of the first section.
    sec_lbl_2 : str
        Label of the second section.
    mediator_sec_lbl : str
        Label of the mediator section.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the two specified sections are connected via the mediator
        section, False otherwise.
    """
    for section in layout['sections']:

        if section['label'] == mediator_sec_lbl:
            break

    sec_lbl_1_connected = False
    sec_lbl_2_connected = False

    for node in section['nodes']:

        if node['con_ele'] == sec_lbl_1:
            sec_lbl_1_connected = True

        elif node['con_ele'] == sec_lbl_2:
            sec_lbl_2_connected = True

    return sec_lbl_1_connected and sec_lbl_2_connected


def addFPreqSwis(movement, layout, paths):
    """Complement FP data with required switches that can add protection.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specific movement.
    layout : dict
        Description of the station's layout.
    paths : list
        List of all possible paths in the station.
    """
    for key in ['route', 'OL']:
        fp_lst = movement['aux']['FP_secs_trans'][key]

        for sec_to_protect in fp_lst:

            for v_nde in sec_to_protect['vulnerable_ndes']:

                for dang_sec in v_nde['dangerous_secs']:
                    req_swi = FPrequiredSwitch(dang_sec['sec_lbl'],
                                               dang_sec['dangerous_transits'],
                                               v_nde['collision_pnt'],
                                               layout,
                                               paths)

                    dang_sec['FP_req_swi'] = req_swi

    fp_lst = movement['aux']['FP_secs_trans']['OL']
    ol_req_swi_lbls = []

    for sec_to_protect in fp_lst:

        for v_nde in sec_to_protect['vulnerable_ndes']:

            for dang_sec in v_nde['dangerous_secs']:

                if dang_sec['FP_req_swi'] is None:
                    continue

                temp = dang_sec['FP_req_swi']['label']

                if dang_sec['FP_req_swi']['label'] in ol_req_swi_lbls:
                    dang_sec['FP_req_swi'] = None

                ol_req_swi_lbls.append(temp)

    fp_lst = movement['aux']['FP_secs_trans']['route']
    rt_req_swi_lbls = []
    rt_req_swi_sec2prt = []

    for sec_to_protect in fp_lst:

        for v_nde in sec_to_protect['vulnerable_ndes']:

            for dang_sec in v_nde['dangerous_secs']:

                if dang_sec['FP_req_swi'] is None:
                    continue

                temp1 = dang_sec['FP_req_swi']['label']
                temp2 = sec_to_protect['sec_to_protect']

                if dang_sec['FP_req_swi']['label'] in rt_req_swi_lbls:
                    idx = rt_req_swi_lbls.index(dang_sec['FP_req_swi']
                                                ['label'])
                    dang_sec['FP_req_swi'] = None

                    if secsConByMed(sec_to_protect['sec_to_protect'],
                                    rt_req_swi_sec2prt[idx],
                                    dang_sec['sec_lbl'],
                                    layout):

                        for sec_to_protect2 in fp_lst:

                            for v_nde2 in sec_to_protect2['vulnerable_ndes']:

                                for dang_sec2 in v_nde2['dangerous_secs']:

                                    if dang_sec2['FP_req_swi'] is None:
                                        continue

                                    if (dang_sec2['FP_req_swi']['label'] ==
                                            temp1):
                                        dang_sec2['FP_req_swi'] = None

                rt_req_swi_lbls.append(temp1)
                rt_req_swi_sec2prt.append(temp2)


def purgeFPsections(movement, layout, paths):
    """Generate selection of necessary FP sections and switches.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specific movement.
    layout : dict
        Description of the station's layout.
    paths : list
        List of all possible paths in the station.

    Returns
    -------
    dict
        Dictionary containing FP data in an intermediate format.
    """
    proto_FP_data = {'req_swis': [],
                     'vital_req_secs': [],
                     'sub_vital_req_secs': [],
                     'remote_req_secs': []}

    for key in ['route', 'OL']:
        fp_lst = movement['aux']['FP_secs_trans'][key]

        for sec_to_protect in fp_lst:

            for v_nde in sec_to_protect['vulnerable_ndes']:

                for dang_sec in v_nde['dangerous_secs']:

                    if dang_sec['FP_req_swi'] is not None:
                        req_swi = deepcopy(dang_sec['FP_req_swi'])
                        req_swi['type'] = key
                        proto_FP_data['req_swis'].append(req_swi)

                        if req_swi['lr_pk'] is not None:
                            break

                    req_sec = deepcopy(dang_sec)
                    req_sec['type'] = key

                    if req_sec['flag'] == 'vital':

                        if (req_sec['sec_lbl'] not in
                            [sec['sec_lbl'] for sec in proto_FP_data
                             ['vital_req_secs']]):
                            proto_FP_data['vital_req_secs'].append(req_sec)

                    elif req_sec['flag'] == 'sub_vital':

                        if (req_sec['sec_lbl'] not in
                            [sec['sec_lbl'] for sec in proto_FP_data
                             ['sub_vital_req_secs']]):
                            proto_FP_data['sub_vital_req_secs'].append(req_sec)

                    elif req_sec['flag'] == 'remote':

                        if (req_sec['sec_lbl'] not in
                            [sec['sec_lbl'] for sec in proto_FP_data
                             ['remote_req_secs']]):
                            proto_FP_data['remote_req_secs'].append(req_sec)

    for section in proto_FP_data['vital_req_secs']:

        if (section['sec_lbl'] in [sec['sec_lbl'] for sec in
                                   proto_FP_data['sub_vital_req_secs']]):
            to_remove = []

            for sec2 in proto_FP_data['sub_vital_req_secs']:

                if sec2['sec_lbl'] == section['sec_lbl']:
                    to_remove.append(sec2)

            for sec_to_remove in to_remove:
                proto_FP_data['sub_vital_req_secs'].remove(sec_to_remove)

        if (section['sec_lbl'] in [sec['sec_lbl'] for sec in
                                   proto_FP_data['remote_req_secs']]):
            to_remove = []

            for sec2 in proto_FP_data['remote_req_secs']:

                if sec2['sec_lbl'] == section['sec_lbl']:
                    to_remove.append(sec2)

            for sec_to_remove in to_remove:
                proto_FP_data['remote_req_secs'].remove(sec_to_remove)

    for section in proto_FP_data['sub_vital_req_secs']:

        if (section['sec_lbl'] in [sec['sec_lbl'] for sec in
                                   proto_FP_data['remote_req_secs']]):
            to_remove = []

            for sec2 in proto_FP_data['remote_req_secs']:

                if sec2['sec_lbl'] == section['sec_lbl']:
                    to_remove.append(sec2)

            for sec_to_remove in to_remove:
                proto_FP_data['remote_req_secs'].remove(sec_to_remove)

    derailers_to_lock = lockDerailerInCrossedSection(movement, layout)

    for derailer_to_lock in derailers_to_lock:
        proto_FP_data['req_swis'].append(derailer_to_lock)

    return proto_FP_data


def getSwitchPositions(sec_lbl, transit, paths):
    """Get the required switch positions for a transit at a given section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section crossed by the specified transit.
    transit : str
        Transit through the specified switch.
    paths : list
        List of all possible paths in the station.

    Returns
    -------
    dict
        Information on the required switches and their positions.
    """
    commanded_switches = []

    for path in paths:

        for section in path['path_secs']:

            if section == sec_lbl:
                idx = path['path_secs'].index(section)

                if path['path_transits'][idx] == transit:

                    for com_swi in path['switch_positions']:

                        if com_swi['sec_lbl'] == sec_lbl:
                            commanded_switches.append(com_swi)

                    return commanded_switches


def FPrequiredSwitch(sec_lbl, dangerous_transits, collision_pnt, layout,
                     paths):
    """Get required switch for flank protection if possible.

    Parameters
    ----------
    sec_lbl : str
        Label of the section where at least one dangerous transit exists.
    dangerous_transits : list
        List of dangerous transits in the specified section.
    collision_pnt : float
        LR PK of the switch on the section to protect.
    layout : dict
        Description of the station's layout.
    paths : list
        List of all possible paths in the station.

    Returns
    -------
    dict or None
        Information on the required switch for flank protection on the
        specified section. If there are no possible locked switch positions
        that ensure flank protection, None is returned.
    """
    FP_req_swi = None

    for dang_trans in dangerous_transits:
        eff_swis = effectiveSwitches(dang_trans, sec_lbl, layout)
        swi_pos = getSwitchPositions(sec_lbl, dang_trans, paths)

        for eff_swi in eff_swis:

            for com_swi in swi_pos:

                if com_swi['SWI_lbl'] == eff_swi['label']:

                    if com_swi['SWI_pos'] == '+':
                        eff_swi['SWI_pos'] = '-'

                    else:
                        eff_swi['SWI_pos'] = '+'

            if eff_swi['effective_direction'] == 'asc':

                if eff_swi['point_pk'] <= collision_pnt:

                    if FP_req_swi is None:
                        FP_req_swi = deepcopy(eff_swi)

                    else:

                        if (eff_swi['label'] == FP_req_swi['label'] and
                                eff_swi['SWI_pos'] != FP_req_swi
                                ['SWI_pos']):
                            return None

                        if eff_swi['point_pk'] > FP_req_swi['point_pk']:

                            FP_req_swi = deepcopy(eff_swi)
                            break

            else:

                if eff_swi['point_pk'] >= collision_pnt:

                    if FP_req_swi is None:
                        FP_req_swi = deepcopy(eff_swi)

                    else:

                        if (eff_swi['label'] == FP_req_swi['label'] and
                                eff_swi['SWI_pos'] != FP_req_swi
                                ['SWI_pos']):
                            return None

                        if eff_swi['point_pk'] < FP_req_swi['point_pk']:

                            FP_req_swi = deepcopy(eff_swi)
                            break

    return FP_req_swi


def getSwitchOrder(swi_lbl, sec_lbl, layout):
    """Find the order of a switch (# of nodes that require the switch at -).

    Parameters
    ----------
    swi_lbl : str
        Label of the switch.
    sec_lbl : str
        Label of the section where the switch is located.
    layout : dict
        Description of the station's layout.

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


def swisInBranch(sec_lbl, nde_idx, layout):
    """Return all switches (no derailers) in a section branch.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    nde_idx : str
        Index of the node of the branch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of switches (no derailers) in the specified section branch.
    """
    switches_in_branch = []

    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:

            for switch in node['switches']:

                if switch['lr_pk'] is not None:
                    switches_in_branch.append(switch)

            return switches_in_branch


def getNodeOrder(sec_lbl, nde_idx, layout):
    """Find the order of a node (# of switches that are required at -).

    Parameters
    ----------
    sec_lbl : str
        Label of the section where the node is located.
    nde_idx : str
        Index of the node to evaluate.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    int
        Order of the specified node, i.e. number of switches required at - for
        a transit to cross that node.
    """
    order = 0

    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['index'][0] == nde_idx:

            for switch in node['switches']:

                if switch['lr_pk'] is not None:
                    order += 1

            return order


def collisionPointAlgo(sec_lbl, transit, vuln_nde_idx, layout):
    """Fing the possible point of collision for a giver section/transit/v_node.

    Parameters
    ----------
    sec_lbl : str
        Label of the section crossed by the transit.
    transit : str
        Transit through the specified section.
    transit : str
        Index of the specified section's vulnerable node to consider.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    float
        PK of possible point of collision.
    """
    v_nde_branch_swis = swisInBranch(sec_lbl, vuln_nde_idx, layout)
    req_swis = requiredSwitches(layout, sec_lbl, transit)

    if v_nde_branch_swis:

        if len(v_nde_branch_swis) == 1:
            return v_nde_branch_swis[0]['lr_pk']

        else:

            for v_nde_branch_swi in v_nde_branch_swis:

                if v_nde_branch_swi in req_swis:
                    return v_nde_branch_swi['lr_pk']

    else:

        for section in layout['sections']:

            if section['label'] == sec_lbl:
                break

        for node in section['nodes']:

            if node['index'][0] == vuln_nde_idx:

                if node['index'][-1] == '+':
                    v_nde_pos = '+'

                else:
                    v_nde_pos = '-'

                break

        transit_ndes = [transit[0], transit[-1]]

        for transit_nde in transit_ndes:

            for node in section['nodes']:

                if (node['index'][0] == transit_nde and
                        node['index'][-1] == v_nde_pos):
                    relevant_transit_nde = deepcopy(node)
                    rel_trs_nde_order = getNodeOrder(sec_lbl,
                                                     transit_nde,
                                                     layout)

                    break

        cand_swis = []

        for switch in relevant_transit_nde['switches']:

            if switch['lr_pk'] is not None:
                cand_swis.append(switch)

        if len(cand_swis) == 1:
            return cand_swis[0]['lr_pk']

        else:
            v_nde_order = getNodeOrder(sec_lbl, vuln_nde_idx, layout)

            for switch in cand_swis:
                switch_order = getSwitchOrder(switch['label'],
                                              section['label'],
                                              layout)

                if switch_order == 1:

                    if (v_nde_order + rel_trs_nde_order) == 3:
                        return switch['lr_pk']

            for switch in cand_swis:
                switch_order = getSwitchOrder(switch['label'],
                                              section['label'],
                                              layout)

                if switch_order > 1:
                    return switch['lr_pk']


def getExitNdePKAndDirection(sec_lbl, transit, layout):
    """Get exit node PK and direction for a transit at a specified section.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to consider.
    transit : str
        Transit to consider at the specified section.
    layout : dict
        Description of the station's layout.

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


def getTransit(movement, sec_lbl):
    """Get exit node PK and direction for a transit at a specified section.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specific movement.
    sec_lbl : str
        Label of the section to be evaluated.

    Returns
    -------
    string
        Transit through the specified section, by the specified movement.
    """
    for key in ['route', 'overlap']:

        for section in movement['sections'][key]:

            if section == sec_lbl:
                idx = movement['sections'][key].index(section)
                return movement['transits'][key][idx]


def flankProtectionGeometricEngine(movement, layout, vital_fp_threshold,
                                   sub_vital_fp_threshold,
                                   remote_fp_threshold):
    """Add geometric considerations to the FP main dictionary.

    Parameters
    ----------
    movement : dict
        Dictionary containing info relating to a specific movement.
    layout : dict
        Description of the station's layout.
    vital_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered vital.
    sub_vital_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered sub_vital.
    remote_fp_threshold : float
        Threshold distance from exit node PK of a FP section to the collision
        point for the section to be considered remote.
    """
    for key in ['route', 'OL']:
        fp_lst = movement['aux']['FP_secs_trans'][key]

        for sec_to_protect_dict in fp_lst:

            for vulnerable_nde_dict in sec_to_protect_dict['vulnerable_ndes']:

                for dang_sec in vulnerable_nde_dict['dangerous_secs']:

                    for dang_trans in dang_sec['dangerous_transits']:
                        transit = getTransit(movement, sec_to_protect_dict
                                             ['sec_to_protect'])
                        collision_pnt = collisionPointAlgo(sec_to_protect_dict
                                                           ['sec_to_protect'],
                                                           transit,
                                                           vulnerable_nde_dict
                                                           ['nde_idx'],
                                                           layout)

                        vulnerable_nde_dict['collision_pnt'] = collision_pnt
                        min_dist = 1000000

                        exit_pk, direction = getExitNdePKAndDirection(
                            dang_sec['sec_lbl'], dang_trans, layout)

                        if direction == 'asc':
                            dist = collision_pnt - exit_pk

                        else:
                            dist = exit_pk - collision_pnt

                        if dist < min_dist:
                            min_dist = dist

                    flag = 'no_FP'

                    if dist <= remote_fp_threshold:
                        flag = 'remote'

                    if dist <= sub_vital_fp_threshold:
                        flag = 'sub_vital'

                    if dist <= vital_fp_threshold:
                        flag = 'vital'

                    dang_sec['flag'] = flag


def flankProtectionSecsAndTransO1(raw_movement, layout, signals,
                                  shunt_sig_filters_fp):
    """Find first order sections required for FP for a given movement.

    Parameters
    ----------
    raw_movement : dict
        Main dictionary containing data relative to a certain movement.
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
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.

    Returns
    -------
    str
        String containing the first letter of the movement types that can have
        the relevant signal as a destination. If there is no signal at the
        specified node, or the signal cannot be a destination of movements,
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
        Description of the station's layout.

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
                                  shunt_sig_filters_fp, movement):
    """Add FP sections of the immediately higher order.

    Parameters
    ----------
    FP_secs_trans_O1 : dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Only first order FP sections are computed, and
        distances to LR PKs are not considered.
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.
    movement : dict
        Dictionary containing info relating to a specific movement.
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
                if (new_dang_sec['sec_lbl'] not in
                    movement['sections']['route'] and new_dang_sec['sec_lbl']
                        not in movement['sections']['overlap']):
                    vuln_nde_O1['dangerous_secs'].append(new_dang_sec)


def higherLevelFPsecsAndTrans(FP_secs_trans_O1, layout, signals,
                              shunt_sig_filters_fp, movement):
    """Complete the FP_secs_trans_O1 dict, adding FP sections of higher order.

    Parameters
    ----------
    FP_secs_trans_O1 : dict
        Dictionary containing FP sections and other info for the raw movement's
        route and overlap. Only first order FP sections are computed, and
        distances to LR PKs are not considered.
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Signal table containing the possible movement types departing from
        and arriving to each signal.
    shunt_sig_filters_fp : bool
        True if a shunt only signal filters movements in flank protection
        considerations, False otherwise.
    movement : dict
        Dictionary containing info relating to a specific movement.

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
                                      signals, shunt_sig_filters_fp, movement)

        if ini_version == FP_secs_trans:
            break

    while True:
        ini_version = deepcopy(FP_secs_trans)
        higherLevelFPsecsAndTransAlgo(FP_secs_trans['OL'], layout, signals,
                                      shunt_sig_filters_fp, movement)

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
        List of dictionaries, each containing info on a vulnerable node, or an
        empty list if there are no vulnerable nodes.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    vulnerable_nodes = []

    for node in section['nodes']:

        if node['index'][0] not in transit:

            if node['con_ele'] is None:
                continue

            if node['signal'] is None:

                vulnerable_nodes.append(node)

            else:
                sig_poss_dest = (signals.loc[signals.signal == node['signal']
                                 ['label']].possible_destination
                                 .iloc[0])

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
        Description of the station's layout.

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
        Description of the station's layout.

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
        Description of the station's layout.

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
