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
    sig_table = pd.DataFrame(columns=['signal', 'section', 'direction'])

    for section in layout['sections']:
        for node in section['nodes']:

            if node['signal'] is not None:
                signal = node['signal']
                section_lbl = section['label']
                direction = 'desc' if node['index'][-1] == '+' else 'asc'

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction}

            if (node['con_ele'] in layout['blocks'] or
                    node['con_ele'] in layout['NDZs']):
                signal = None
                section_lbl = node['con_ele']
                direction = 'desc' if node['index'][-1] == '-' else 'asc'

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction}

    return sig_table


def tamponSections(layout):
    """Identify tampon sections (connected w/ BLK or NDZ)."""
    tamp_secs = []

    for section in layout['sections']:
        for node in section['nodes']:
            if (node['con_ele'] in layout['blocks'] or
                    node['con_ele'] in layout['NDZs']):

                label = section['label']
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


def updatePaths(last_section, direction, paths, nxt_secs):
    """Update the paths list, adding the nxt secs and creating new paths."""
    new_paths = []

    for path in paths:

        if (path['path_secs'][-1] == last_section and
                path['direction'] == direction):

            for i in range(len(nxt_secs)):
                if i == 0:
                    path['path_secs'].append(nxt_secs[i])
                else:
                    new_path = deepcopy(path)
                    new_path['path_secs'].pop(-1)
                    new_path['path_secs'].append(nxt_secs[i])
                    new_paths.append(deepcopy(new_path))
    if len(new_paths) > 0:
        paths.append(new_paths)


def pathFinder(con_mat, tamp_secs):
    """Find all possble paths departing from the tampon sections."""
    corresp = {'high': 1,
               'low': -1}

    paths = []
    for tamp_sec in tamp_secs:

        paths.append([tamp_sec['label']])

        break_while = False
        while True:
            for k in range(len(paths)):
                index = con_mat[1].index(paths[k][-1])
                connections = con_mat[0][index]
                nxt_sec_idxs = np.where(connections == corresp[tamp_sec['place']])[0]

                if len(nxt_sec_idxs) == 0:
                    break_while = True

                nxt_secs = [con_mat[1][i] for i in nxt_sec_idxs]

                for i in range(len(nxt_secs)):
                    if i == 0:
                        paths[k].append(nxt_secs[i])
                    else:
                        new_path = deepcopy(paths[-1][:-1])
                        new_path.append(nxt_secs[i])
                        paths.append(new_path)

            if break_while:
                break

    return paths


lt = readStationLayout('MAF.ZcfgL0')
lt = addNodeSigns(lt)

con_mat = conMatrix(lt)
sig_table = sigTable(lt)
tamp_secs = tamponSections(lt)

#paths = pathFinder(con_mat, tamp_secs)



