"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""


def outputAssembler(movements, delays, aux_data, inputs, layout, signals):
    """Post process and prepare output information for printing/serialization.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    delays : dict
        Dictionary containing the delay timings for the station layout.
    aux_data : dict
        Dictionary containing the station's auxiliary data.
    inputs : dict
        Dictionary containing input data (.zlt, .zlg, .zad and .zop).
    layout : dict
        Description of the station's layout.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.

    Returns
    -------
    dict
        Aggregation of processing outputs, ready for printing/serialization
    """
    circulation = {'normal_entry': [],
                   'normal_exit': [],
                   'reverse_entry': [],
                   'reverse_exit': []}
    shunt = {'forward': [],
             'backward': []}
    sorted_movements = sortMovements(movements, signals)
    block_labels = [block['label'] for block in layout['blocks']]
    NDZ_labels = [NDZ['label'] for NDZ in layout['NDZs']]

    for movement in sorted_movements:
        orig_loc, dest_loc = locFinder(movement, signals)

        if movement['origin']['alias'] is None:
            origin_sig = movement['origin']['literal']

        else:
            origin_sig = movement['origin']['alias']

        if 'M_' in movement['destination']['literal']:
            destination_sig = 'SLI'

        elif movement['destination']['literal'] in block_labels:
            destination_sig = 'Block'

        elif movement['destination']['literal'] in NDZ_labels:
            destination_sig = 'NDZ'

        elif bool(signals.loc[signals.signal == movement['destination']
                              ['literal']].virtual.iloc[0]):
            destination_sig = 'Terminal'

        else:
            destination_sig = movement['destination']['literal']

        if movement['aux']['alt_OL'] is None:
            alt_ol = ''

        else:
            alt_ol = movement['aux']['alt_OL']

        if movement['aux']['alt_route'] is None:
            alt_rt = ''

        else:
            alt_rt = ''

            for diff_swi in movement['aux']['alt_route']:

                if len(alt_rt) > 0:
                    alt_rt += '/'

                alt_rt += diff_swi['SWI_lbl']
                alt_rt += diff_swi['SWI_pos']

        switches = refactorSwiDict(movement['switches'],
                                   movement['logic_overlap'])
        sections = refactorSecDict(movement['sections'],
                                   movement['type'],
                                   movement['logic_overlap'],
                                   layout)
        blocks = getBlockDir(movement, layout)

        distilled_mov = {'rt_ID': None,
                         'origin_loc': orig_loc,
                         'origin_sig': origin_sig,
                         'destination_loc': dest_loc,
                         'destination_sig': destination_sig,
                         'regime': movement['type'],
                         'alt_ol': alt_ol,
                         'alt_rt': alt_rt,
                         'obs': 'Special' if movement['special'] else '',
                         'switches': switches,
                         'sections': sections,
                         'blocks': blocks}

        if movement['type'] != 'Shunt':
            rev_mov = reverseMovement(movement, layout)
            entry_exit = entryExit(orig_loc, dest_loc, layout)

            if not rev_mov:

                if entry_exit == 'entry':
                    circulation['normal_entry'].append(distilled_mov)

                else:
                    circulation['normal_exit'].append(distilled_mov)

            else:

                if entry_exit == 'entry':
                    circulation['reverse_entry'].append(distilled_mov)

                else:
                    circulation['reverse_exit'].append(distilled_mov)

        else:
            for_back = forwardBackward(movement, layout)

            if for_back == 'forward':
                shunt['forward'].append(distilled_mov)

            else:
                shunt['backward'].append(distilled_mov)

    counter = 0

    for mov in circulation['normal_entry']:
        counter += 1
        mov['rt_ID'] = counter

    for mov in circulation['normal_exit']:
        counter += 1
        mov['rt_ID'] = counter

    for mov in circulation['reverse_entry']:
        counter += 1
        mov['rt_ID'] = counter

    for mov in circulation['reverse_exit']:
        counter += 1
        mov['rt_ID'] = counter

    for mov in shunt['forward']:
        counter += 1
        mov['rt_ID'] = counter

    for mov in shunt['backward']:
        counter += 1
        mov['rt_ID'] = counter

    IP = {'COVER': aux_data,
          'CIRCULATION': circulation,
          'SHUNT': shunt,
          'DELAYS': delays,
          'INPUTS': inputs}

    return IP


def sortSigLabels(sig_labels_raw, signals):
    """Sort a list of signal labels.

    Parameters
    ----------
    sig_labels_raw : list
        List of strings, each being a signal label.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.

    Returns
    -------
    dict
        Sorted list of strings, each being a signal label.
    """
    sig_labels_pre_sort_rev = [sig_lbl[::-1] for sig_lbl in sig_labels_raw]
    sig_labels_pre_sort_rev.sort()
    sig_labels = [sig_lbl[::-1] for sig_lbl in sig_labels_pre_sort_rev]

    M_asc = []
    M_desc = []
    SLI_asc = []
    SLI_desc = []
    SM_asc = []
    SM_desc = []
    SC_asc = []
    SC_desc = []

    for sig_lbl in sig_labels:
        sig_dir = signals.loc[signals.signal == sig_lbl].direction.iloc[0]

        if 'M' in sig_lbl and 'S' not in sig_lbl:

            if sig_dir == 'asc':
                M_asc.append(sig_lbl)

            else:
                M_desc.append(sig_lbl)

        elif 'M_' in sig_lbl:

            if sig_dir == 'asc':
                SLI_asc.append(sig_lbl)

            else:
                SLI_desc.append(sig_lbl)

        elif 'SC' in sig_lbl:

            if sig_dir == 'asc':
                SC_asc.append(sig_lbl)

            else:
                SC_desc.append(sig_lbl)

        else:

            if sig_dir == 'asc':
                SM_asc.append(sig_lbl)

            else:
                SM_desc.append(sig_lbl)

    return (SM_asc + SM_desc + SC_asc + SC_desc + M_asc + M_desc + SLI_asc +
            SLI_desc)


def sortMovements(movements, signals):
    """Sort movements.

    Parameters
    ----------
    movements : list
        List of dictionaries, each relative to a possible movement.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.

    Returns
    -------
    dict
        Sorted list of dictionaries, each relative to a possible movement.
    """
    circ = []
    shunt = []

    for movement in movements:

        if movement['type'] == 'Shunt':
            shunt.append(movement)

        else:
            circ.append(movement)

    asc_circ = []
    desc_circ = []
    asc_shunt = []
    desc_shunt = []

    for movement in circ:

        if movement['direction'] == 'asc':
            asc_circ.append(movement)

        else:
            desc_circ.append(movement)

    for movement in shunt:

        if movement['direction'] == 'asc':
            asc_shunt.append(movement)

        else:
            desc_shunt.append(movement)

    origins_pre_sort = []
    destinations_pre_sort = []

    for movement in asc_circ:

        if movement['origin']['literal'] not in origins_pre_sort:
            origins_pre_sort.append(movement['origin']['literal'])

        if movement['destination']['literal'] not in destinations_pre_sort:
            destinations_pre_sort.append(movement['destination']['literal'])

    for movement in desc_circ:

        if movement['origin']['literal'] not in origins_pre_sort:
            origins_pre_sort.append(movement['origin']['literal'])

        if movement['destination']['literal'] not in destinations_pre_sort:
            destinations_pre_sort.append(movement['destination']['literal'])

    for movement in asc_shunt:

        if movement['origin']['literal'] not in origins_pre_sort:
            origins_pre_sort.append(movement['origin']['literal'])

        if movement['destination']['literal'] not in destinations_pre_sort:
            destinations_pre_sort.append(movement['destination']['literal'])

    for movement in desc_shunt:

        if movement['origin']['literal'] not in origins_pre_sort:
            origins_pre_sort.append(movement['origin']['literal'])

        if movement['destination']['literal'] not in destinations_pre_sort:
            destinations_pre_sort.append(movement['destination']['literal'])

    origins = sortSigLabels(origins_pre_sort, signals)
    destinations = sortSigLabels(destinations_pre_sort, signals)

    asc_circ_pre_srt = []
    desc_circ_pre_srt = []
    asc_shunt_pre_srt = []
    desc_shunt_pre_srt = []

    for origin in origins:
        temp = []

        for movement in asc_circ:

            if movement['origin']['literal'] == origin:
                temp.append(movement)

        if temp:
            asc_circ_pre_srt.append(temp)

        temp = []

        for movement in desc_circ:

            if movement['origin']['literal'] == origin:
                temp.append(movement)

        if temp:
            desc_circ_pre_srt.append(temp)

        temp = []

        for movement in asc_shunt:

            if movement['origin']['literal'] == origin:
                temp.append(movement)

        if temp:
            asc_shunt_pre_srt.append(temp)

        temp = []

        for movement in desc_shunt:

            if movement['origin']['literal'] == origin:
                temp.append(movement)

        if temp:
            desc_shunt_pre_srt.append(temp)

    semi_sorted_raw = []

    for destination in destinations:

        for group in asc_circ_pre_srt:
            temp = []

            for movement in group:

                if movement['destination']['literal'] == destination:
                    temp.append(movement)

            if temp:
                semi_sorted_raw.append(temp)

        for group in desc_circ_pre_srt:
            temp = []

            for movement in group:

                if movement['destination']['literal'] == destination:
                    temp.append(movement)

            if temp:
                semi_sorted_raw.append(temp)

        for group in asc_shunt_pre_srt:
            temp = []

            for movement in group:

                if movement['destination']['literal'] == destination:
                    temp.append(movement)

            if temp:
                semi_sorted_raw.append(temp)

        for group in desc_shunt_pre_srt:
            temp = []

            for movement in group:

                if movement['destination']['literal'] == destination:
                    temp.append(movement)

            if temp:
                semi_sorted_raw.append(temp)

    sorted_movements = []

    for group in semi_sorted_raw:

        for regime in ['Main', 'DOS', 'Shunt']:

            for movement in group:

                if (movement['aux']['alt_OL'] is None and
                        movement['aux']['alt_route'] is None and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' not in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is None and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is None and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is None and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] != '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is None and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] == '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' not in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] != '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] != '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' not in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] == '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

            for movement in group:

                if (movement['aux']['alt_OL'] is not None and
                        '-' in movement['aux']['alt_OL'] and
                        movement['aux']['alt_route'] is not None and
                        movement['aux']['alt_route'][0]['SWI_pos'] == '-' and
                        movement['type'] == regime):
                    sorted_movements.append(movement)

    circ = []
    shunt = []

    for movement in sorted_movements:

        if movement['type'] == 'Shunt':
            shunt.append(movement)

        else:
            circ.append(movement)

    return circ + shunt


def locFinder(movement, signals):
    """Find origin location for a specified movement.

    Parameters
    ----------
    movement : dict
        Dictionary containing data relative to a certain movement.
    signals : Pandas Dataframe
        Dataframe of signals and their respective properties.

    Returns
    -------
    orig_loc : str
        Label of the origin location of the movement.
    dest_loc : str
        Label of the destination location of the movement.
    """
    orig_sig = movement['origin']['literal']
    dest_sig = movement['destination']['literal']
    orig_loc = signals.loc[signals.signal == orig_sig].prev_sec.iloc[0]
    dest_sig_data = signals.loc[signals.signal == dest_sig]

    if bool(dest_sig_data.virtual.iloc[0]):
        dest_loc = dest_sig_data.section.iloc[0]

    else:
        dest_loc = dest_sig_data.prev_sec.iloc[0]

    return orig_loc, dest_loc


def reverseMovement(movement, layout):
    """Find if a circulation movement is reverse.

    Parameters
    ----------
    movement : dict
        Dictionary containing data relative to a certain movement.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the movement is reverse, False otherwise.
    """
    block_labels = [block['label'] for block in layout['blocks']]
    orig_sig = movement['origin']['literal']
    dest_sig = movement['destination']['literal']

    if 'SC' in orig_sig:
        return True

    elif dest_sig in block_labels and len(dest_sig) == 4:
        dest_blk_number = int(dest_sig[-1])
        even_blk_number = False

        if (dest_blk_number % 2) == 0:
            even_blk_number = True

        if movement['direction'] == 'asc' and even_blk_number:
            return True

        elif movement['direction'] == 'desc' and not even_blk_number:
            return True

    return False


def entryExit(orig_loc, dest_loc, layout):
    """Find if a circulation movement enters or exits the station.

    Parameters
    ----------
    orig_loc : str
        Label of the origin location of the movement.
    dest_loc : str
        Label of the destination location of the movement.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        "entry" if the movement enters the station, "exit" otherwise.
    """
    block_labels = [block['label'] for block in layout['blocks']]
    ndz_labels = [ndz['label'] for ndz in layout['NDZs']]

    if orig_loc in block_labels:
        return 'entry'

    elif dest_loc in block_labels:
        return 'exit'

    elif orig_loc in ndz_labels:
        return 'entry'

    elif dest_loc in ndz_labels:
        return 'exit'

    else:
        return 'entry'


def tampSec(sec_lbl, layout):
    """Find if a section is connected to a block or NDZ.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to evaluate.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the section is connected to a block or NDZ, False otherwise.
    """
    block_labels = [block['label'] for block in layout['blocks']]
    ndz_labels = [ndz['label'] for ndz in layout['NDZs']]

    for section in layout['sections']:

        if section['label'] == sec_lbl:
            break

    for node in section['nodes']:

        if node['con_ele'] in block_labels or node['con_ele'] in ndz_labels:
            return True

    return False


def forwardBackward(movement, layout):
    """Find if a shunt mov. takes the train closer or further to the station.

    Parameters
    ----------
    movement : dict
        Dictionary containing data relative to a certain movement.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        "backward" if the movement takes the train closer to the station,
        "further" otherwise.
    """
    for section in movement['sections']['route']:

        if tampSec(section, layout):
            return 'forward'

    for section in movement['sections']['overlap']:

        if tampSec(section, layout):
            return 'forward'

    return 'backward'


def refactorSwiDict(swi_dict, logic_ol):
    """Refactor the switches dictionary and ready data for printing to .xlsx.

    Parameters
    ----------
    swi_dict : dict
        Dictionary containing required switch information.
    logic_ol : Bool
        True if the associated movement has logic overlap, False otherwise.

    Returns
    -------
    dict
        Dictionary containing required switch information, ready for .xlsx
        printing or serialization.
    """
    refac_swi_dict = {'rt': {'normal': '',
                             'reverse': ''},
                      'ol': {'normal': '',
                             'reverse': ''},
                      'fp': {'rt': {'normal': '',
                                    'reverse': ''},
                             'ol': {'normal': '',
                                    'reverse': ''}}}

    for req_swi in swi_dict['route']:

        if req_swi['SWI_pos'] == '+':

            if len(refac_swi_dict['rt']['normal']) != 0:
                refac_swi_dict['rt']['normal'] += ', '

            refac_swi_dict['rt']['normal'] += req_swi['SWI_lbl']

        else:

            if len(refac_swi_dict['rt']['reverse']) != 0:
                refac_swi_dict['rt']['reverse'] += ', '

            refac_swi_dict['rt']['reverse'] += req_swi['SWI_lbl']

    if not logic_ol:

        for req_swi in swi_dict['overlap']:

            if req_swi['SWI_pos'] == '+':

                if len(refac_swi_dict['ol']['normal']) != 0:
                    refac_swi_dict['ol']['normal'] += ', '

                refac_swi_dict['ol']['normal'] += req_swi['SWI_lbl']

            else:

                if len(refac_swi_dict['ol']['reverse']) != 0:
                    refac_swi_dict['ol']['reverse'] += ', '

                refac_swi_dict['ol']['reverse'] += req_swi['SWI_lbl']

    for req_swi in swi_dict['flank_prot']['route']:

        if req_swi['SWI_pos'] == '+':

            if len(refac_swi_dict['fp']['rt']['normal']) != 0:
                refac_swi_dict['fp']['rt']['normal'] += ', '

            refac_swi_dict['fp']['rt']['normal'] += req_swi['SWI_lbl']

        else:

            if len(refac_swi_dict['fp']['rt']['reverse']) != 0:
                refac_swi_dict['fp']['rt']['reverse'] += ', '

            refac_swi_dict['fp']['rt']['reverse'] += req_swi['SWI_lbl']

    if not logic_ol:

        for req_swi in swi_dict['flank_prot']['overlap']:

            if req_swi['SWI_pos'] == '+':

                if len(refac_swi_dict['fp']['ol']['normal']) != 0:
                    refac_swi_dict['fp']['ol']['normal'] += ', '

                refac_swi_dict['fp']['ol']['normal'] += req_swi['SWI_lbl']

            else:

                if len(refac_swi_dict['fp']['ol']['reverse']) != 0:
                    refac_swi_dict['fp']['ol']['reverse'] += ', '

                refac_swi_dict['fp']['ol']['reverse'] += req_swi['SWI_lbl']

    return refac_swi_dict


def sectionIsNDZ(sec_lbl, layout):
    """Evaluate is a section is a NDZ.

    Parameters
    ----------
    sec_lbl : dict
        Label of the section to evaluate.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the section is an NDZ, False otherwise.
    """
    for section in layout['sections']:

        if section['label'] == sec_lbl:

            if section['NDZ']:
                return True

            else:
                return False


def refactorSecDict(sec_dict, regime, logic_ol, layout):
    """Refactor the sections dictionary and ready data for printing to .xlsx.

    Parameters
    ----------
    sec_dict : dict
        Dictionary containing required section information.
    regime : str
        Regime (type) of the associated movement.
    logic_ol : Bool
        True if the associated movement has logic overlap, False otherwise.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    dict
        Dictionary containing required section information, ready for .xlsx
        printing or serialization.
    """
    refac_sec_dict = {'rt': '',
                      'ol': '',
                      'fp': {'rt': {'vital': '',
                                    'sub_vital': '',
                                    'remote': ''},
                             'ol': {'vital': '',
                                    'sub_vital': '',
                                    'remote': ''}}}

    if regime == 'Main':

        for req_sec in sec_dict['route']:

            if not sectionIsNDZ(req_sec, layout):

                if len(refac_sec_dict['rt']) != 0:
                    refac_sec_dict['rt'] += ', '

                refac_sec_dict['rt'] += req_sec

        for req_sec in sec_dict['overlap']:

            if not sectionIsNDZ(req_sec, layout):

                if len(refac_sec_dict['ol']) != 0:
                    refac_sec_dict['ol'] += ', '

                refac_sec_dict['ol'] += req_sec

    for req_sec in sec_dict['flank_prot']['route']['vital']:

        if not sectionIsNDZ(req_sec, layout):

            if len(refac_sec_dict['fp']['rt']['vital']) != 0:
                refac_sec_dict['fp']['rt']['vital'] += ', '

            refac_sec_dict['fp']['rt']['vital'] += req_sec

    for req_sec in sec_dict['flank_prot']['route']['sub_vital']:

        if not sectionIsNDZ(req_sec, layout):

            if len(refac_sec_dict['fp']['rt']['sub_vital']) != 0:
                refac_sec_dict['fp']['rt']['sub_vital'] += ', '

            refac_sec_dict['fp']['rt']['sub_vital'] += req_sec

    for req_sec in sec_dict['flank_prot']['route']['remote']:

        if not sectionIsNDZ(req_sec, layout):

            if len(refac_sec_dict['fp']['rt']['remote']) != 0:
                refac_sec_dict['fp']['rt']['remote'] += ', '

            refac_sec_dict['fp']['rt']['remote'] += req_sec

    if not logic_ol:

        for req_sec in sec_dict['flank_prot']['overlap']['vital']:

            if not sectionIsNDZ(req_sec, layout):

                if len(refac_sec_dict['fp']['ol']['vital']) != 0:
                    refac_sec_dict['fp']['ol']['vital'] += ', '

                refac_sec_dict['fp']['ol']['vital'] += req_sec

        for req_sec in sec_dict['flank_prot']['overlap']['sub_vital']:

            if not sectionIsNDZ(req_sec, layout):

                if len(refac_sec_dict['fp']['ol']['sub_vital']) != 0:
                    refac_sec_dict['fp']['ol']['sub_vital'] += ', '

                refac_sec_dict['fp']['ol']['sub_vital'] += req_sec

        for req_sec in sec_dict['flank_prot']['overlap']['remote']:

            if not sectionIsNDZ(req_sec, layout):

                if len(refac_sec_dict['fp']['ol']['remote']) != 0:
                    refac_sec_dict['fp']['ol']['remote'] += ', '

                refac_sec_dict['fp']['ol']['remote'] += req_sec

    return refac_sec_dict


def getBlockDir(movement, layout):
    """Compute required blocks for each movement.

    Parameters
    ----------
    movement : dict
        Dictionary containing data relative to a certain movement.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    dict
        Dictionary containing required blocks, ready for .xlsx printing or
        serialization.
    """
    block_labels = [block['label'] for block in layout['blocks']]
    blocks_dict = {'up': '',
                   'down': ''}

    if movement['destination']['literal'] in block_labels:

        if movement['direction'] == 'asc':
            blocks_dict['up'] = movement['destination']['literal']

        else:
            blocks_dict['down'] = movement['destination']['literal']

    return blocks_dict
