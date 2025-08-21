"""ZIRCON."""


def readLayout(filename):
    """Read the layout file and loads data to main layout dict."""
    with open(filename, 'r') as file:
        lines = file.readlines()

    blocks = []
    stations = []

    for line in lines:

        if 'BLOCK' in line:

            label = line[6:-1]
            block = {'lbl': label,
                     'stations': None,
                     'dir': None}
            blocks.append(block)

        elif 'STATION' in line:

            label = line[8:-1]
            station = {'lbl': label,
                       'sections': []}
            stations.append(station)

        elif 'SECTION' in line:

            label = line[9:-1]
            section = {'lbl': label,
                       'nodes': [],
                       'transits': [],
                       'signals': [],
                       'points': []}
            stations[-1]['sections'].append(section)

        elif 'NODE' in line:

            data = line[7:-1].split()
            node = {'lbl': data[0],
                    'pk': data[1],
                    'adj': data[2] if len(data) >= 3 else None,
                    'adj_nde': data[3] if len(data) == 4 else None}
            stations[-1]['sections'][-1]['nodes'].append(node)

        elif 'TRANSITS' in line:

            transits = line[11:-1].split()
            stations[-1]['sections'][-1]['transits'] = transits

        elif 'SIGNAL' in line:

            data = line[9:-1].split()
            signal = {'lbl': data[0],
                      'pk': data[1] if len(data) > 1 else None}
            stations[-1]['sections'][-1]['signals'].append(signal)

        elif 'POINT' in line:

            data = line[8:-1].split()
            point = {'lbl': data[0],
                     'pk_lr': data[1],
                     'pk_tip': data[2],
                     'spec_trans': data[3:]}
            stations[-1]['sections'][-1]['points'].append(point)

        else:

            return 'ERROR - LINE WITHOUT KNOWN KEY'

    layout = {'blocks': blocks,
              'stations': stations}

    return layout
