"""ZIRCON PoC v0.5.0."""

import numpy as np
import pandas as pd
from copy import deepcopy


def zltParser(station_label):
    """Parse .zlt file, which encodes the station's topography.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed (<STATION_LABEL>.zlt).

    Returns
    -------
    dict
        Station topography as encoded in the .zlt file.
    """
    file_name = station_label + '.zlt'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    blocks = []
    NDZs = []
    sections = []

    for line in lines:
        split_line = line.split()

        if split_line[0] == 'BLK':
            reading = 'block'
            block = {'label': split_line[1],
                     'signal': None}
            blocks.append(block)

        elif split_line[0] == 'NDZ':
            reading = 'ndz'
            ndz = {'label': split_line[1],
                   'signal': None}
            NDZs.append(ndz)

        elif split_line[0] == 'SEC':
            reading = 'section'
            section = {'label': split_line[1],
                       'nodes': []}
            sections.append(section)

        elif split_line[0] == 'NDE':

            if len(split_line) > 2 and split_line[2] != '-':
                con_ele = split_line[2]

            else:
                con_ele = None

            node = {'index': split_line[1],
                    'con_ele': con_ele,
                    'signal': None,
                    'switches': [],
                    'TJS_weak_nde': True if split_line[-1] == '-' else False}
            sections[-1]['nodes'].append(node)

        elif split_line[0] == 'SIG':
            signal = {'label': split_line[1],
                      'pedal': False,
                      'RW': True if '*' in split_line else False}

            if reading == 'section':
                sections[-1]['nodes'][-1]['signal'] = signal

            elif reading == 'ndz':
                NDZs[-1]['signal'] = signal

            elif reading == 'block':
                blocks[-1]['signal'] = signal

        elif split_line[0] == 'SWP':
            signal = {'label': split_line[1],
                      'pedal': True,
                      'RW': True if '*' in split_line else False}

            if reading == 'section':
                sections[-1]['nodes'][-1]['signal'] = signal

            elif reading == 'ndz':
                NDZs[-1]['signal'] = signal

            elif reading == 'block':
                blocks[-1]['signal'] = signal

        elif split_line[0] == 'SWI':
            switch = {'label': split_line[1]}
            sections[-1]['nodes'][-1]['switches'].append(switch)

    lt_top_raw = {'blocks': blocks,
                  'NDZs': NDZs,
                  'sections': sections}

    return lt_top_raw


def inferNdeSigns(layout_raw):
    """Infer node signs and add them to lt_top_raw.

    Parameters
    ----------
    lt_top_raw : dict
        Layout's topography without node signs.

    Returns
    -------
    dict
        Layout with explicit node signs.
    """
    layout = deepcopy(layout_raw)

    for section in layout['sections']:
        counter = 0

        for node in section['nodes']:
            counter += 1
            index = node['index']

            if len(index) == 1:

                if index == 'A':
                    node['index'] = 'A+'

                elif counter == len(section['nodes']):
                    node['index'] = index + '-'

                else:

                    for switch in node['switches']:
                        if switch['lr_pk'] is not None:

                            if node['pk'] > switch['point_pk']:
                                node['index'] = index + '+'

                            else:
                                node['index'] = index + '-'

        for node in section['nodes']:
            index = node['index']

            if len(index) == 1:

                for node2 in deepcopy(section['nodes']):
                    index2 = node2['index']

                    if (len(node2['switches']) == 0 and
                            len(node2['index']) != 1):

                        if index2[-1] == '+':
                            node['index'] = index + '-'

                        else:
                            node['index'] = index + '+'

                    elif (len(node2['switches']) == 0 and
                            node2['index'] > node['index']):
                        node['index'] = index + '+'
                        node2['index'] = index2 + '-'

                    elif (len(node2['switches']) == 0 and
                            node2['index'] < node['index']):
                        node['index'] = index + '-'
                        node2['index'] = index2 + '+'

    return layout


def zlgParser(station_label):
    """Parse .zlg file, which encodes the station's geometry.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed (<STATION_LABEL>.zlg).

    Returns
    -------
    dict
        Station geometry as encoded in the .zlg file.
    """
    file_name = station_label + '.zlg'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    sections = []
    switches = []
    signals = []

    for line in lines:
        split_line = line.split()

        if 'SECS' in split_line:
            reading = 'secs'
            continue

        elif 'SWIS' in split_line:
            reading = 'swis'
            continue

        elif 'SIGS' in split_line:
            reading = 'sigs'
            continue

        if reading == 'secs':
            section_lbl = split_line[0]
            nde_pks_str = split_line[1:]
            nde_pks = [float(pk_str) for pk_str in nde_pks_str]
            section = {'label': section_lbl,
                       'node_pks': nde_pks}
            sections.append(section)

        elif reading == 'swis':
            switch_lbl = split_line[0]
            point_pk = float(split_line[1])

            if len(split_line) == 3:
                lr_pk = float(split_line[2])

            else:
                lr_pk = None

            switch = {'label': switch_lbl,
                      'point_pk': point_pk,
                      'lr_pk': lr_pk}
            switches.append(switch)

        elif reading == 'sigs':
            signal_lbl = split_line[0]
            signal_pk = float(split_line[1])

            if len(split_line) != 2:
                zap_origin = split_line[2]
                zap_origin_sft_fac = split_line[3]

            else:
                zap_origin = zap_origin_sft_fac = None

            signal = {'label': signal_lbl,
                      'pk': signal_pk,
                      'zap_origin_pk': zap_origin,
                      'zap_origin_sft_fac': zap_origin_sft_fac}
            signals.append(signal)

    lt_geo = {'sections': sections,
              'switches': switches,
              'signals': signals}

    return lt_geo


def layoutAssembler(lt_top_raw, lt_geo):
    """Unify topographic and geometric data in a single dictionary.

    Parameters
    ----------
    lt_top_raw : dict
        Topographic layout information without node signs.
    lt_geo : dict
        Geometric layout information.

    Returns
    -------
    dict
        Unified description of the layout without node signs.
    """
    layout_raw = deepcopy(lt_top_raw)

    for lt_top_section in layout_raw['sections']:

        for lt_geo_section in lt_geo['sections']:

            if lt_top_section['label'] == lt_geo_section['label']:
                index = 0

                for node in lt_top_section['nodes']:
                    node['pk'] = lt_geo_section['node_pks'][index]
                    index += 1

                    for lt_geo_switch in lt_geo['switches']:

                        for lt_top_switch in node['switches']:

                            if lt_top_switch['label'] ==\
                                    lt_geo_switch['label']:
                                lt_top_switch['point_pk'] =\
                                    lt_geo_switch['point_pk']
                                lt_top_switch['lr_pk'] =\
                                    lt_geo_switch['lr_pk']

                    for lt_geo_signal in lt_geo['signals']:

                        if node['signal'] is not None:

                            if node['signal']['label'] == lt_geo_signal[
                                    'label']:
                                node['signal']['pk'] = lt_geo_signal['pk']
                                node['signal']['zap_origin_pk'] = \
                                    lt_geo_signal['zap_origin_pk']
                                node['signal']['zap_origin_sft_fac'] = \
                                    lt_geo_signal['zap_origin_sft_fac']

                        for block in layout_raw['blocks']:

                            if block['signal'] is not None:

                                if block['signal']['label'] == lt_geo_signal[
                                         'label']:
                                    block['signal']['pk'] = lt_geo_signal['pk']
                                    block['signal']['zap_origin_pk'] = \
                                        lt_geo_signal['zap_origin_pk']
                                    block['signal']['zap_origin_sft_fac'] = \
                                        lt_geo_signal['zap_origin_sft_fac']

                        for ndz in layout_raw['NDZs']:

                            if ndz['signal'] is not None:

                                if ndz['signal']['label'] == lt_geo_signal[
                                       'label']:
                                    ndz['signal']['pk'] = lt_geo_signal['pk']
                                    ndz['signal']['zap_origin_pk'] = \
                                        lt_geo_signal['zap_origin_pk']
                                    ndz['signal']['zap_origin_sft_fac'] = \
                                        lt_geo_signal['zap_origin_sft_fac']

    return layout_raw


def zopParser(label):
    """Read and interpret .zop file, which encodes the operational parameters.

    Parameters
    ----------
    label : str
        Label of the parameter file to be considered (<LABEL>.zop).

    Returns
    -------
    dict
        Operational parameter variables as encoded in the .zop file.
    """
    file_name = label + '.zop'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    parameters = {}

    for line in lines:
        split_line = line.split()

        if split_line[0] == 'MAIN_OL_DISTANCE':
            parameters['MAIN_OL_DISTANCE'] = float(split_line[1])

        elif split_line[0] == 'DOS_OL_DISTANCE':
            parameters['DOS_OL_DISTANCE'] = float(split_line[1])

        elif split_line[0] == 'SHUNT_OL_DISTANCE':
            parameters['SHUNT_OL_DISTANCE'] = float(split_line[1])

        elif split_line[0] == 'HORSE_NECK_POSSIBLE':

            if split_line[1] == 'TRUE':
                parameters['HORSE_NECK_POSSIBLE'] = True

            else:
                parameters['HORSE_NECK_POSSIBLE'] = False

        elif split_line[0] == 'TO_BLOCK':
            parameters['TO_BLOCK'] = split_line[1:]

        elif split_line[0] == 'TO_NDZ':
            parameters['TO_NDZ'] = split_line[1:]

        elif split_line[0] == 'TO_TERMINAL':
            parameters['TO_TERMINAL'] = split_line[1:]

        elif split_line[0] == 'TO_TERMINAL_SWITCH_BRANCH':
            parameters['TO_TERMINAL_SWITCH_BRANCH'] = split_line[1:]

    return parameters


def adjacency(layout):
    """Assemble the adjacency matrix of the station's layout.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    sections = [section['label'] for section in layout['sections']]

    elements = sections + blocks + NDZs
    matrix = np.zeros([len(elements), len(elements)])
    section_index = -1

    for section in layout['sections']:
        section_index += 1

        for node in section['nodes']:
            con_ele = node['con_ele']

            if con_ele is None:
                continue

            con_ele_index = elements.index(con_ele)

            if node['index'][-1] == '+':
                matrix[section_index, con_ele_index] = 1

            elif node['index'][-1] == '-':
                matrix[section_index, con_ele_index] = -1

    for i in range(len(blocks) + len(NDZs)):
        index = -(i + 1)
        column = matrix[:, index]
        matrix[index, :] = -column

    adjacency_data = {'matrix': matrix,
                      'index_map': elements}

    return adjacency_data


def sigTable(layout):
    """Generate a table containing relevant info on real and virtual signals.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    Pandas DataFrame
        Signal table.
    """
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    sig_table = pd.DataFrame(columns=['signal',
                                      'section',
                                      'direction',
                                      'virtual',
                                      'prev_sec'])

    for section in layout['sections']:

        for node in section['nodes']:

            if node['signal'] is not None:
                signal = node['signal']['label']
                section_lbl = section['label']
                direction = 'desc' if node['index'][-1] == '+' else 'asc'
                prev_sec = node['con_ele']

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction,
                                                 'virtual': False,
                                                 'prev_sec': prev_sec}

            if (node['con_ele'] in blocks or node['con_ele'] in NDZs):
                signal = node['con_ele']
                section_lbl = node['con_ele']
                direction = 'desc' if node['index'][-1] == '-' else 'asc'
                prev_sec = section['label']

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction,
                                                 'virtual': True,
                                                 'prev_sec': prev_sec}

            if node['con_ele'] is None and len(section['nodes']) == 2:
                signal = section['label']
                section_lbl = section['label']
                direction = 'desc' if node['index'][-1] == '-' else 'asc'

                for node2 in section['nodes']:
                    prev_sec_cand = node2['con_ele']

                    if prev_sec_cand is not None:
                        prev_sec = prev_sec_cand

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction,
                                                 'virtual': True,
                                                 'prev_sec': prev_sec}

    for block_dict in layout['blocks']:

        if block_dict['signal'] is not None:

            for section in layout['sections']:

                for node in section['nodes']:

                    if node['con_ele'] == block_dict['label']:
                        signal = block_dict['signal']['label']
                        section_lbl = block_dict['label']
                        direction = 'desc' if node['index'][-1] ==\
                            '-' else 'asc'
                        prev_sec = section['label']

                        sig_table.loc[len(sig_table)] =\
                            {'signal': signal,
                             'section': section_lbl,
                             'direction': direction,
                             'virtual': True,
                             'prev_sec': prev_sec}

    for ndz_dict in layout['NDZs']:

        if ndz_dict['signal'] is not None:

            for section in layout['sections']:

                for node in section['nodes']:

                    if node['con_ele'] == ndz_dict['label']:
                        signal = block_dict['signal']['label']
                        section_lbl = block_dict['label']
                        direction = 'desc' if node['index'][-1] ==\
                            '-' else 'asc'
                        prev_sec = section['label']

                        sig_table.loc[len(sig_table)] =\
                            {'signal': signal,
                             'section': section_lbl,
                             'direction': direction,
                             'virtual': True,
                             'prev_sec': prev_sec}

    return sig_table


def sigLogic(circ, shunt, ILM, pedal, RW, block, NDZ, terminal):
    """Derive signal abilities from flags.

    Parameters
    ----------
    circ : bool
        Circulation signal.
    shunt : bool
        Shunt signal.
    ILM : bool
        Shunt limit indicator.
    pedal : bool
        Signal has an associated pedal.
    RW : bool
        Signal has only red and white aspects.
    block : bool
        Block (virtual signal).
    NDZ : bool
        NDZ (virtual signal).
    terminal : bool
        Terminal section (virtual signal).

    Returns
    -------
    dict
        Types of itineraries possible from and to the signal.
    """
    M_origin = D_origin = S_origin = True
    M_destiny = D_destiny = S_destiny = True

    if not circ:
        M_origin = D_origin = M_destiny = D_destiny = False

    if not shunt:
        S_origin = False

    if not pedal:
        D_origin = False

    if RW:
        M_origin = False

    if block or terminal:
        M_origin = D_origin = S_origin = S_destiny = False
        M_destiny = D_destiny = True

    if NDZ:
        M_origin = D_origin = S_origin = M_destiny = False
        D_destiny = S_destiny = True

    if ILM:
        S_origin = False
        S_destiny = True

    possible_origin = possible_destiny = ''

    if M_origin:
        possible_origin += ('M')

    if D_origin:
        possible_origin += ('D')

    if S_origin:
        possible_origin += ('S')

    if M_destiny:
        possible_destiny += ('M')

    if D_destiny:
        possible_destiny += ('D')

    if S_destiny:
        possible_destiny += ('S')

    signal_abilities = {'possible_origin': possible_origin,
                        'possible_destiny': possible_destiny}

    return signal_abilities


def sigDecoder(sig_table, layout):
    """Decode signal names and flags.

    Parameters
    ----------
    sig_table : Pandas DataFrame
        Signal table.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    Pandas DataFrame
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    """
    signals = deepcopy(sig_table)
    signals['possible_origin'] = signals['possible_destiny'] = None

    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]
    secs = [section['label'] for section in layout['sections']]

    for index, row in signals.iterrows():

        for section in layout['sections']:

            for node in section['nodes']:

                if node['signal'] is not None:

                    if node['signal']['label'] == row['signal']:

                        circ = True if 'S' in row['signal'] else False
                        shunt = True if 'M' in row['signal'] else False
                        ILM = True if row['signal'] == 'M' else False
                        pedal = node['signal']['pedal']
                        RW = node['signal']['RW']
                        block = True if row['signal'] in blocks else False
                        NDZ = True if row['signal'] in NDZs else False
                        terminal = True if row['signal'] in secs else False

                        signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                    RW, block, NDZ, terminal)

                        signals.loc[index, 'possible_origin'] =\
                            signal_abilities['possible_origin']
                        signals.loc[index, 'possible_destiny'] =\
                            signal_abilities['possible_destiny']

        for block_dict in layout['blocks']:

            if block_dict['signal'] is not None:

                if block_dict['signal']['label'] == row['signal']:

                    circ = True if 'S' in row['signal'] else False
                    shunt = True if 'M' in row['signal'] else False
                    ILM = True if row['signal'] == 'M' else False
                    pedal = block_dict['signal']['pedal']
                    RW = block_dict['signal']['RW']
                    block = True if row['signal'] in blocks else False
                    NDZ = True if row['signal'] in NDZs else False
                    terminal = True if row['signal'] in secs else False

                    signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                RW, block, NDZ, terminal)

                    signals.loc[index, 'possible_origin'] =\
                        signal_abilities['possible_origin']
                    signals.loc[index, 'possible_destiny'] =\
                        signal_abilities['possible_destiny']

        for ndz_dict in layout['NDZs']:

            if ndz_dict['signal'] is not None:

                if ndz_dict['signal']['label'] == row['signal']:

                    circ = True if 'S' in row['signal'] else False
                    shunt = True if 'M' in row['signal'] else False
                    ILM = True if row['signal'] == 'M' else False
                    pedal = block_dict['signal']['pedal']
                    RW = block_dict['signal']['RW']
                    block = True if row['signal'] in blocks else False
                    NDZ = True if row['signal'] in NDZs else False
                    terminal = True if row['signal'] in secs else False

                    signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                RW, block, NDZ, terminal)

                    signals.loc[index, 'possible_origin'] =\
                        signal_abilities['possible_origin']
                    signals.loc[index, 'possible_destiny'] =\
                        signal_abilities['possible_destiny']

        if (row['signal'] in blocks or row['signal'] in NDZs or
                row['signal'] in secs):
            circ = False
            shunt = False
            ILM = False
            pedal = False
            RW = False
            block = True if row['signal'] in blocks else False
            NDZ = True if row['signal'] in NDZs else False
            terminal = True if row['signal'] in secs else False

            signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                        RW, block, NDZ, terminal)

            signals.loc[index, 'possible_origin'] =\
                signal_abilities['possible_origin']
            signals.loc[index, 'possible_destiny'] =\
                signal_abilities['possible_destiny']

    return signals


def absoluteOrigins(layout):
    """Identify absolute origins (BLKs, NDZs and terminal sections).

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, one for each absolute origin, containing the
        respective label and a "low" or "high" "place" key, for weather the
        absolute origin is of ascending or descending itinieraries.
    """
    abs_origins = []
    blocks = [block['label'] for block in layout['blocks']]
    NDZs = [ndz['label'] for ndz in layout['NDZs']]

    for section in layout['sections']:

        for node in section['nodes']:

            if node['con_ele'] is None and len(section['nodes']) == 2:
                label = section['label']
                place = 'high' if node['index'][-1] == '+' else 'low'

                abs_origins.append({'label': label,
                                    'place': place})

            elif (node['con_ele'] in blocks or node['con_ele'] in NDZs):
                label = node['con_ele']
                place = 'high' if node['index'][-1] == '+' else 'low'

                abs_origins.append({'label': label,
                                    'place': place})

    return abs_origins


def connectedSections(section_lbl, rel_position, adjacency_data):
    """Identify immediate connections of a sections at a higher or lower PK.

    Parameters
    ----------
    section_lbl : str
        Label of the section to be considered.
    rel_position : str
        'upstream' or 'downstream' weather to find a connection at a higher or
        lower PK, respectivelly.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.

    Returns
    -------
    list
        List of all connected sections at the specified relative position.
    """
    corresp = {'upstream': 1,
               'downstream': -1}

    index = adjacency_data['index_map'].index(section_lbl)
    connections = adjacency_data['matrix'][index]
    nxt_sec_idxs = np.where(connections == corresp[rel_position])[0]

    if len(nxt_sec_idxs) == 0:
        return None

    con_secs = [adjacency_data['index_map'][i] for i in nxt_sec_idxs]

    return con_secs


def transitFinder(section_prior, section_crossed, section_after, layout):
    """Identify immediate connections of a section at a higher or lower PK.

    Parameters
    ----------
    section_prior : str
        Label of the section from where the transit originates.
    section_crossed : str
        Label of the section through which the transit passes.
    section_after : str
        Label of the section to which the transit goes.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Transit (two letters, order sensitive).
    """
    transit = ''

    for section in layout['sections']:

        if section['label'] == section_crossed:

            for node in section['nodes']:

                if node['con_ele'] == section_prior:
                    transit += node['index'][:-1]

            for node in section['nodes']:

                if node['con_ele'] == section_after:
                    transit += node['index'][:-1]

    return transit


def impossibleTransits(layout):
    """Identify transits that are impossible due to TJS and analogue elements.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each containing a section where a legal but
        impossible transit exists, as well as the transit itself.
    """
    imp_trans = []

    for section in layout['sections']:
        last_found = []

        for node in section['nodes']:

            if node['TJS_weak_nde']:
                weak_node_index = node['index'][0]
                weak_node_sign = node['index'][-1]

                for node2 in section['nodes']:

                    for switch in node2['switches']:

                        if (switch['lr_pk'] is not None and
                                node2['index'][-1] != weak_node_sign):
                            trans1 = node2['index'][0] + weak_node_index
                            trans2 = trans1[::-1]
                            last_found.append(trans1)
                            last_found.append(trans2)

        if last_found:
            imp_trans.append({'section': section['label'],
                              'imp_trans': last_found})

    return imp_trans


def impTransEnforcer(paths, imp_trans):
    """Remove impossible transits from paths list.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    """
    imp_paths = []

    for imp_trans_inspected in imp_trans:

        for path in paths:

            for i in range(len(path['path_secs'])):

                if imp_trans_inspected['section'] == path['path_secs'][i]:

                    for transit in imp_trans_inspected['imp_trans']:

                        if transit == path['path_transits'][i]:
                            imp_paths.append(path)

    for imp_path in imp_paths:
        paths.pop(paths.index(imp_path))


def switchPositionFinder(path, layout):
    """Find required switch positions for a given path.

    Parameters
    ----------
    path : dict
        Dictionary containing the sections crossed by a given path, as well as
        the respective transits.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each relative to a switch that needs to be set.
        The dictionaries contain the switch's label and the required position
        (+ for normal or - for reverse).
    """
    switch_positions = []

    for i in range(len(path['path_secs'])):
        section_lbl = path['path_secs'][i]
        transit_lbl = path['path_transits'][i]

        if transit_lbl is None:
            continue

        for section in layout['sections']:

            if section['label'] == section_lbl:

                for node in section['nodes']:

                    for switch in node['switches']:

                        if node['index'][0] in transit_lbl:
                            SWI_pos = '-'

                        else:
                            SWI_pos = '+'

                        switch_data = {'SWI_lbl': switch['label'],
                                       'SWI_pos': SWI_pos}
                        switch_positions.append(switch_data)

    return switch_positions


def isContiguous(section1, section2, adjacency_data):
    """Find if two sections are contiguous.

    Parameters
    ----------
    section1 : str
        Label of the first section to be evaluated.
    section2 : str
        Label of the second section to be evaluated.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.

    Returns
    -------
    bool
        True if the two sections are contiguous, False otherwise.
    """
    section1_idx = adjacency_data['index_map'].index(section1)
    section2_idx = adjacency_data['index_map'].index(section2)

    if adjacency_data['matrix'][section1_idx, section2_idx].item() != 0:

        return True

    return False


def crossesSwitchBranch(sec_lbl, transit, layout):
    """Find if a transit crosses a switch branch.

    Parameters
    ----------
    sec_lbl : str
        Label of the section to be evaluated.
    transit : str
        Transit through the section to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if a switch branch is crossed, False otherwise.
    """
    for section in layout['sections']:

        if sec_lbl == section['label']:

            for node in section['nodes']:

                if node['switches']:

                    if node['index'][0] in transit:

                        return True
    return False


def antiHorseNeck(paths, layout, adjacency_data):
    """Find if two sections are contiguous.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    layout : dict
        Description of the station's layout.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.
    """
    for path in paths:
        candidate = []

        for i in range(len(path['path_secs'])):

            sec_lbl = path['path_secs'][i]
            transit = path['path_transits'][i]

            if crossesSwitchBranch(sec_lbl, transit, layout):

                if len(candidate) < 4:
                    candidate.append(sec_lbl)

                else:
                    candidate.pop(0)
                    candidate.append(sec_lbl)

            else:
                candidate = []

            if len(candidate) == 4:

                if isContiguous(candidate[0], candidate[-1], adjacency_data):
                    paths.pop(paths.index(path))


def pathFinder(adjacency_data, abs_origins, layout, imp_trans):
    """Find all possible paths (transit sequences) in the station.

    Parameters
    ----------
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.
    abs_origins : list
        List of dictionaries, one for each absolute origin, containing the
        respective label and a "low" or "high" "place" key, for weather the
        absolute origin is of ascending or descending itinieraries.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries (each representing a possible path) where key
        "path_secs" holds a list of ordered sections intercepted by the path
        and key "path_transits" holds a list of the transits through the path
        sections (same index).
    """
    paths = []
    corresp = {'asc': 'upstream',
               'desc': 'downstream'}

    for tamp_sec in abs_origins:
        path = {'path_secs': [tamp_sec['label']],
                'path_transits': [None],
                'switch_positions': None,
                'direction': 'asc' if tamp_sec['place'] == 'low' else 'desc'}

        paths.append(path)

    for path in paths:
        nxt_secs = True

        while nxt_secs is not None:
            nxt_secs = connectedSections(path['path_secs'][-1],
                                         corresp[path['direction']],
                                         adjacency_data)

            if nxt_secs is None:
                break

            new_paths = []

            for i in range(len(nxt_secs)):

                if i == 0:
                    path['path_secs'].append(nxt_secs[i])

                else:
                    new_path = deepcopy(path)
                    new_path['path_secs'].pop(-1)
                    new_path['path_secs'].append(nxt_secs[i])
                    new_paths.append(deepcopy(new_path))

            if len(new_paths) > 0:

                for new_path in new_paths:
                    paths.append(new_path)

        for i in range(len(path['path_secs'])-2):
            transit = transitFinder(path['path_secs'][i],
                                    path['path_secs'][i+1],
                                    path['path_secs'][i+2],
                                    layout)

            path['path_transits'].append(transit)

        path['path_transits'].append(None)

        switch_positions = switchPositionFinder(path, layout)
        path['switch_positions'] = switch_positions

    impTransEnforcer(paths, imp_trans)
    antiHorseNeck(paths, layout, adjacency_data)

    return paths


def ITFinder(paths, signals):
    """Find all possible itineraries in the station.

    Parameters
    ----------
    paths : list
        List of all possible paths in the station.
    signals : Pandas Dataframe
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.

    Returns
    -------
    list
        List of dictionaries, each relative to a possible itinerary.
    """
    its = []
    it = {'lbl': None,
          'path_index': None,
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

                    for i in range(len(possible_new_candidates)):
                        possible_origin =\
                            signals.loc[signals.signal ==
                                        possible_new_candidates[i]].\
                            possible_origin.iloc[0]

                        if IT_type[0] in possible_origin:
                            new_candidates.append(possible_new_candidates[i])

                else:

                    for i in range(len(possible_new_candidates)):
                        possible_destiny =\
                            signals.loc[signals.signal ==
                                        possible_new_candidates[i]].\
                            possible_destiny.iloc[0]

                        if IT_type[0] in possible_destiny:
                            new_candidates.append(possible_new_candidates[i])

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

                            new_it['lbl'] = origin_sig + '-' + destiny_sig
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

                            its.append(new_it)

                    candidates = []
                    route_secs = []
                    route_secs.append(section)

                    for sig in new_candidates:
                        candidates.append(sig)

    return its


station_label = 'CIS'

lt_top_raw = zltParser(station_label)
lt_geo = zlgParser(station_label)

layout_raw = layoutAssembler(lt_top_raw, lt_geo)

layout = inferNdeSigns(layout_raw)

parameters = zopParser('GENERAL')

adjacency_data = adjacency(layout)
sig_table = sigTable(layout)
signals = sigDecoder(sig_table, layout)
abs_origins = absoluteOrigins(layout)

imp_trans = impossibleTransits(layout)
paths = pathFinder(adjacency_data, abs_origins, layout, imp_trans)

its = ITFinder(paths, signals)

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
