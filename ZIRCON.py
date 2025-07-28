"""ZIRCON prototype."""

import numpy as np
import pandas as pd
from copy import deepcopy


def readStationLayout(filename):
    """Read the layout file and load data to main layout dict."""
    with open(filename, 'r') as file:
        lines = file.readlines()

    blocks = []
    NDZs = []
    sections = []

    for line in lines:

        if 'BLK' in line:

            label = line[4:-1]
            blocks.append(label)

        elif 'NDZ' in line:

            label = line[4:-1]
            NDZs.append(label)

        elif 'SEC' in line:

            label = line[4:-1]
            section = {'label': label,
                       'nodes': [],
                       'points': []}
            sections.append(section)

        elif 'NDE' in line:

            data = line[8:-1].split()
            node = {'index': data[0],
                    'con_ele': data[1] if len(data) > 1 else None,
                    'con_sec_nde': data[2] if len(data) > 2 else None,
                    'signal': None}
            sections[-1]['nodes'].append(node)

        elif 'SIG' in line:

            data = line[12:-1]
            sections[-1]['nodes'][-1]['signal'] = data

        elif 'PNT' in line:

            data = line[8:-1].split()
            point = {'label': data[0],
                     'spec_trs': data[1:]}
            sections[-1]['points'].append(point)

        else:

            return 'ERROR - LINE WITHOUT KNOWN KEY' + line

    layout = {'blocks': blocks,
              'NDZs': NDZs,
              'sections': sections}

    return layout


def addNodeSigns(layout):
    """Add implicit signs of node indices."""
    for section in layout['sections']:
        counter = 0
        for node in section['nodes']:
            counter += 1
            index = node['index']

            if index == 'A':
                node['index'] = 'A+'
            elif counter == len(section['nodes']) and len(index) == 1:
                node['index'] = index + '-'

    return layout


def conMatrix(layout):
    """Build a connection matrix from the station layout."""
    blocks = layout['blocks']
    NDZs = layout['NDZs']
    sections = [section['label'] for section in layout['sections']]

    elements = sections + blocks + NDZs

    con_mat = np.zeros([len(elements), len(elements)])

    section_index = -1
    for section in layout['sections']:
        section_index += 1
        for node in section['nodes']:

            con_ele = node['con_ele']
            if con_ele is None:
                continue

            con_ele_index = elements.index(con_ele)

            if node['index'][-1] == '+':
                con_mat[section_index, con_ele_index] = 1
            elif node['index'][-1] == '-':
                con_mat[section_index, con_ele_index] = -1

    for i in range(len(blocks) + len(NDZs)):
        index = -(i + 1)
        column = con_mat[:, index]
        con_mat[index, :] = -column

    return {'matrix': con_mat,
            'ordered_elements': elements}


def sigTable(layout):
    """Assembles a table of real and virtual signals with relevant info."""
    sig_table = pd.DataFrame(columns=['signal',
                                      'section',
                                      'direction',
                                      'virtual',
                                      'prev_sec'])

    for section in layout['sections']:
        for node in section['nodes']:

            if node['signal'] is not None:
                signal = node['signal']
                section_lbl = section['label']
                direction = 'desc' if node['index'][-1] == '+' else 'asc'
                prev_sec = node['con_ele']

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction,
                                                 'virtual': False,
                                                 'prev_sec': prev_sec}

            if (node['con_ele'] in layout['blocks'] or
                    node['con_ele'] in layout['NDZs']):
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

    return sig_table


def tamponSections(layout):
    """Identify tampon sections (connected w/ BLK or NDZ or terminal)."""
    tamp_secs = []

    for section in layout['sections']:
        for node in section['nodes']:
            if node['con_ele'] is None and len(section['nodes']) == 2:

                label = section['label']
                place = 'high' if node['index'][-1] == '+' else 'low'

                tamp_secs.append({'label': label,
                                  'place': place})

            elif (node['con_ele'] in layout['blocks'] or
                    node['con_ele'] in layout['NDZs']):

                label = node['con_ele']
                place = 'high' if node['index'][-1] == '+' else 'low'

                tamp_secs.append({'label': label,
                                  'place': place})

    return tamp_secs


def connectedSections(section_lbl, rel_position, con_mat):
    """Find sections connected w/ a section @ relevant position."""
    corresp = {'upstream': 1,
               'downstream': -1}

    index = con_mat['ordered_elements'].index(section_lbl)
    connections = con_mat['matrix'][index]
    nxt_sec_idxs = np.where(connections == corresp[rel_position])[0]

    if len(nxt_sec_idxs) == 0:
        return None

    nxt_secs = [con_mat['ordered_elements'][i] for i in nxt_sec_idxs]
    return nxt_secs


def transitFinder(section_prior, section_crossed, section_after, layout):
    """Find thansit through a crossed section."""
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


def pathFinder(con_mat, tamp_secs, layout):
    """Find all possble paths departing from the tampon sections."""
    paths = []
    corresp = {'asc': 'upstream',
               'desc': 'downstream'}

    for tamp_sec in tamp_secs:
        path = {'path_secs': [tamp_sec['label']],
                'path_transits': [None],
                'direction': 'asc' if tamp_sec['place'] == 'low' else 'desc'}
        paths.append(path)

    for path in paths:
        nxt_secs = True

        while nxt_secs is not None:
            nxt_secs = connectedSections(path['path_secs'][-1],
                                         corresp[path['direction']],
                                         con_mat)
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

    return paths


def initITdict():
    """Initialize IT info containing dictionary."""
    return {'lbl': None,
            'origin': None,
            'destiny': None,
            'type': None,
            'route_secs': None,
            'possible_OL_path': None}


def MainITFinder(paths, sig_table):
    """Return Main itineraries, route sections and possible OL sections."""
    it = initITdict()
    main_its = []

    for path in paths:
        sections = path['path_secs']
        direction = path['direction']

        candidates = []
        route_secs = []
        prev_sec = None
        for section in sections:
            new_candidates = list(sig_table.loc[
                                 (sig_table.section == section) &
                                 (sig_table.direction == direction) &
                                 (sig_table.prev_sec == prev_sec)].signal)
            prev_sec = section
            if len(candidates) == 0 and len(new_candidates) != 0:
                for sig in new_candidates:
                    candidates.append(sig)
                route_secs.append(section)

            elif len(candidates) != 0 and len(new_candidates) == 0:
                route_secs.append(section)

            elif len(candidates) != 0 and len(new_candidates) != 0:
                for origin_sig in candidates:
                    for destiny_sig in new_candidates:
                        new_it = deepcopy(it)
                        new_it['lbl'] = origin_sig + '-' + destiny_sig
                        new_it['origin'] = origin_sig
                        new_it['destiny'] = destiny_sig
                        new_it['type'] = 'Main'
                        new_it['route_secs'] = route_secs

                        last_route_sec_idx = sections.index(route_secs[-1])
                        possible_OL_path = sections[last_route_sec_idx + 1:]
                        new_it['possible_OL_path'] = possible_OL_path

                        main_its.append(new_it)

                candidates = []
                for sig in new_candidates:
                    candidates.append(sig)
                route_secs = []
                route_secs.append(section)

    return main_its






lt = readStationLayout('MAF.ZcfgL0')
lt = addNodeSigns(lt)

con_mat = conMatrix(lt)
sig_table = sigTable(lt)
tamp_secs = tamponSections(lt)

paths = pathFinder(con_mat, tamp_secs, lt)

main_its = MainITFinder(paths, sig_table)

