"""ZIRCON Spatial Engine."""

import numpy as np
from copy import deepcopy


def spatialEngine(layout, allow_terminal_branches, HN_possible):
    """Abstract station's layout, returning all possible paths and aux info.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    allow_terminal_branches : bool
        True if a terminal section branch is to be considered a possible
        origin/destiny of paths, False otherwise.
    HN_possible : bool
        True if paths containing horse-neck are to be allowed, False otherwise.

    Returns
    -------
    list
        List of dictionaries (each representing a possible path) where key
        "path_secs" holds a list of ordered sections intercepted by the path,
        key "path_transits" holds a list of the transits through the path
        sections (same index), and "switch_positions" holds a list of the
        required switches, their required position, and respective sections.
        Finally, "direction" is the path's direction.
    """
    adjacency_data = adjacency(layout)
    abs_origins = absoluteOrigins(layout, allow_terminal_branches)
    imp_trans = impossibleTransits(layout)
    raw_paths_w_imp_trans_HN = pathFinder(adjacency_data, abs_origins, layout,
                                          imp_trans)
    raw_paths_w_HN = impTransEnforcer(raw_paths_w_imp_trans_HN, imp_trans)

    if not HN_possible:
        raw_paths = antiHorseNeck(raw_paths_w_HN, layout, adjacency_data)

    else:
        raw_paths = raw_paths_w_HN

    paths_wo_swi_pos = addVirtualTransits(raw_paths, layout)
    paths = switchPositionFinder(paths_wo_swi_pos, layout)

    return paths


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


def absoluteOrigins(layout, allow_terminal_branches):
    """Identify absolute origins (BLKs, NDZs and terminal sections).

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    allow_terminal_branches : bool
        True if a terminal section branch is to be considered a possible
        origin/destiny of paths, False otherwise.

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

            if node['con_ele'] is None and (len(section['nodes']) == 2
                                            or allow_terminal_branches):
                label = section['label']
                place = 'high' if node['index'][-1] == '+' else 'low'
                branch = True if len(section['nodes']) > 2 else False

                abs_origins.append({'label': label,
                                    'place': place,
                                    'branch': branch})

            elif (node['con_ele'] in blocks or node['con_ele'] in NDZs):
                label = node['con_ele']
                place = 'high' if node['index'][-1] == '+' else 'low'

                abs_origins.append({'label': label,
                                    'place': place,
                                    'branch': False})

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


def TJS(layout):
    """Identify transits that are impossible due to TJS.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each containing a section where an impossible
        transit due to TJS exists, as well as the transit itself.
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


def cross(layout):
    """Identify transits that are impossible due to cross section.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each containing a section where an impossible
        transit due to a cross section exists, as well as the transit itself.
    """
    imp_trans = []

    for section in layout['sections']:
        node_count = len(section['nodes'])

        if node_count > 2:
            is_cross = True

            for node in section['nodes']:

                for switch in node['switches']:

                    if switch['lr_pk'] is not None:
                        is_cross = False
                        break

        else:
            is_cross = False

        if is_cross:
            imp_trans.append({'section': section['label'],
                              'imp_trans': ['DA', 'AD', 'CB', 'BC']})

    return imp_trans


def impossibleTransits(layout):
    """Identify all impossible transits.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries, each containing a section where an impossible
        transit exists, as well as the transit itself.
    """
    imp_trans_TJS = TJS(layout)
    imp_trans_cross = cross(layout)

    imp_trans = imp_trans_TJS + imp_trans_cross

    return imp_trans


def impTransEnforcer(raw_paths_w_imp_trans_HN, imp_trans):
    """Remove impossible transits from paths list.

    Parameters
    ----------
    raw_paths_w_imp_trans_HN : list
       List of dictionaries (each representing a possible path) where key
       "path_secs" holds a list of ordered sections intercepted by the path,
       key "path_transits" holds a list of the transits through the path
       sections (same index), and "switch_positions" holds a list of the
       required switches, their required position, and respective sections.
       Finally, "direction" is the path's direction. Paths to terminal
       sections don't have a virtual transit associated with the last section.
       Impossible transits at TJS and horse neck paths are included.
    imp_trans : list
        List of dictionaries, each containing a section where an impossible
        transit exists, as well as the transit itself.

    Returns
    -------
    list
       List of dictionaries (each representing a possible path) where key
       "path_secs" holds a list of ordered sections intercepted by the path,
       key "path_transits" holds a list of the transits through the path
       sections (same index), and "switch_positions" holds a list of the
       required switches, their required position, and respective sections.
       Finally, "direction" is the path's direction. Paths to terminal
       sections don't have a virtual transit associated with the last section.
       Horse neck paths are included.
    """
    imp_paths = []
    raw_paths_w_HN = deepcopy(raw_paths_w_imp_trans_HN)

    for imp_trans_inspected in imp_trans:

        for path in deepcopy(raw_paths_w_HN):

            for i in range(len(path['path_secs'])):

                if imp_trans_inspected['section'] == path['path_secs'][i]:

                    for transit in imp_trans_inspected['imp_trans']:

                        if transit == path['path_transits'][i]:
                            imp_paths.append(path)

    for imp_path in imp_paths:
        raw_paths_w_HN.pop(raw_paths_w_HN.index(imp_path))

    return raw_paths_w_HN


def switchPositionFinder(paths_wo_swi_pos, layout):
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
    paths = deepcopy(paths_wo_swi_pos)

    for path in paths:
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
                                           'SWI_pos': SWI_pos,
                                           'sec_lbl': section_lbl}
                            switch_positions.append(switch_data)

        path['switch_positions'] = switch_positions

    return paths


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
    if transit is None:
        return False

    for section in layout['sections']:

        if sec_lbl == section['label']:

            for node in section['nodes']:

                if node['switches']:

                    if node['index'][0] in transit:

                        return True
    return False


def antiHorseNeck(raw_paths_w_HN, layout, adjacency_data):
    """Remove paths that contain horse-neck (legal but invalid paths).

    Parameters
    ----------
    raw_paths_w_HN : list
       List of dictionaries (each representing a possible path) where key
       "path_secs" holds a list of ordered sections intercepted by the path,
       key "path_transits" holds a list of the transits through the path
       sections (same index), and "switch_positions" holds a list of the
       required switches, their required position, and respective sections.
       Finally, "direction" is the path's direction. Paths to terminal
       sections don't have a virtual transit associated with the last section.
       Horse neck paths are included.
    layout : dict
        Description of the station's layout.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.

    Returns
    -------
    list
       List of dictionaries (each representing a possible path) where key
       "path_secs" holds a list of ordered sections intercepted by the path,
       key "path_transits" holds a list of the transits through the path
       sections (same index), and "switch_positions" holds a list of the
       required switches, their required position, and respective sections.
       Finally, "direction" is the path's direction. Paths to terminal
       sections don't have a virtual transit associated with the last section.
    """
    raw_paths = deepcopy(raw_paths_w_HN)

    for path in deepcopy(raw_paths):
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
                    raw_paths.pop(raw_paths.index(path))

    return raw_paths


def pathToBranch(path, abs_origins, layout):
    """Generate path to section branch from path that crosses section branch.

    Parameters
    ----------
    path : dict
        Dictionary containing the sections crossed by a given path, as well as
        the respective transits.
    abs_origins : list
        List of dictionaries, one for each absolute origin, containing the
        respective label and a "low" or "high" "place" key, for weather the
        absolute origin is of ascending or descending itinieraries.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    path : dict
        Dictionary containing the sections crossed by a given path, as well as
        the respective transits. This corresponds to the new path found. If
        no new path was found, the function returns None
    """
    corresp = {'low': 'desc',
               'high': 'asc'}

    for abs_origin in abs_origins:

        if abs_origin['branch']:

            if path['direction'] == corresp[abs_origin['place']]:

                for i in range(len(path['path_secs'])):

                    if path['path_secs'][i] == abs_origin['label']:
                        new_path = deepcopy(path)
                        new_path['path_secs'] = path['path_secs'][:i + 1]

                        return new_path


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
        "path_secs" holds a list of ordered sections intercepted by the path,
        key "path_transits" holds a list of the transits through the path
        sections (same index), and "switch_positions" holds a list of the
        required switches, their required position, and respective sections.
        Finally, "direction" is the path's direction. Paths to terminal
        sections don't have a virtual transit associated with the last section.
        Impossible transits at TJS and horse neck paths are included.
    """
    raw_paths_w_imp_trans_HN = []
    corresp = {'asc': 'upstream',
               'desc': 'downstream'}

    for tamp_sec in abs_origins:
        path = {'path_secs': [tamp_sec['label']],
                'path_transits': [None],
                'direction': 'asc' if tamp_sec['place'] == 'low' else 'desc'}

        raw_paths_w_imp_trans_HN.append(path)

    for path in raw_paths_w_imp_trans_HN:
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
                    raw_paths_w_imp_trans_HN.append(new_path)

    for path in deepcopy(raw_paths_w_imp_trans_HN):
        path_to_branch = pathToBranch(path, abs_origins, layout)

        if path_to_branch is not None:

            if path_to_branch not in raw_paths_w_imp_trans_HN:
                raw_paths_w_imp_trans_HN.append(path_to_branch)

    for path in raw_paths_w_imp_trans_HN:

        for i in range(len(path['path_secs'])-2):
            transit = transitFinder(path['path_secs'][i],
                                    path['path_secs'][i+1],
                                    path['path_secs'][i+2],
                                    layout)

            path['path_transits'].append(transit)

        path['path_transits'].append(None)

    return raw_paths_w_imp_trans_HN


def addVirtualTransits(raw_paths, layout):
    """Find all possible paths (transit sequences) in the station.

    Parameters
    ----------
    raw_paths : list
        List of dictionaries (each representing a possible path) where key
        "path_secs" holds a list of ordered sections intercepted by the path,
        key "path_transits" holds a list of the transits through the path
        sections (same index), and "switch_positions" holds a list of the
        required switches, their required position, and respective sections.
        Finally, "direction" is the path's direction. Paths to terminal
        sections don't have a virtual transit associated with the last section.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    list
        List of dictionaries (each representing a possible path) where key
        "path_secs" holds a list of ordered sections intercepted by the path,
        key "path_transits" holds a list of the transits through the path
        sections (same index), and "switch_positions" holds a list of the
        required switches, their required position, and respective sections.
        Finally, "direction" is the path's direction.
    """
    sections = [section['label'] for section in layout['sections']]
    paths_wo_swi_pos = deepcopy(raw_paths)

    for path in paths_wo_swi_pos:

        if path['path_secs'][-1] in sections:

            for section in layout['sections']:

                if section['label'] == path['path_secs'][-1]:

                    for node in section['nodes']:

                        if node['con_ele'] is None:
                            terminal_node_index = node['index'][0]

                        if node['con_ele'] == path['path_secs'][-2]:
                            entry_node_index = node['index'][0]

            last_transit = entry_node_index + terminal_node_index
            path['path_transits'][-1] = last_transit

    return paths_wo_swi_pos
