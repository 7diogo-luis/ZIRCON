"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""


def loader(station_label, parameters_label):
    """Load .zlt, .zlg, .zad and .zop files.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed.
    parameters_label : str
        Label of the parameter file to be considered.

    Returns
    -------
    lt_top_raw : dict
        Layout's topography with incomplete ILM labels.
    lt_geo : dict
        Layout's geometry.
    aux_data : dict
        Layout's auxiliary data.
    parameters : dict
        Operational parameter variables as encoded in the .zop file.
    inputs : dict
        Inputs read from each file.
    """
    if station_label is not None:
        lt_top_raw, zlt_input = zltParser(station_label)
        lt_geo, zlg_input = zlgParser(station_label)
        aux_data, zad_input = zadParser(station_label)

        if parameters_label is None:
            parameters = None
            inputs = {'zlt': zlt_input,
                      'zlg': zlg_input,
                      'zad': zad_input,
                      'zop': None}

        else:
            parameters, zop_input = zopParser(parameters_label)
            inputs = {'zlt': zlt_input,
                      'zlg': zlg_input,
                      'zad': zad_input,
                      'zop': zop_input}

    else:
        lt_top_raw = lt_geo = aux_data = inputs = None
        parameters, zop_input = zopParser(parameters_label)
        inputs = {'zlt': None,
                  'zlg': None,
                  'zad': None,
                  'zop': zop_input}

    return lt_top_raw, lt_geo, aux_data, parameters, inputs


def zltParser(station_label):
    """Parse .zlt file, which encodes the station's topography.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed.

    Returns
    -------
    dict
        Layout's topography with incomplete ILM labels.
    """
    file_name = 'stations/input/' + station_label + '.zlt'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    blocks = []
    NDZs = []
    sections = []
    zlt_input = []

    for line in lines:
        zlt_input.append(line)
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
                       'nodes': [],
                       'NDZ': True if 'NDZ' in split_line else False,
                       'special_type': 'TJD' if 'TJD' in split_line else None}
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

    return lt_top_raw, zlt_input


def zlgParser(station_label):
    """Parse .zlg file, which encodes the station's geometry.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed.

    Returns
    -------
    dict
        Layout's geometry.
    """
    file_name = 'stations/input/' + station_label + '.zlg'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    sections = []
    switches = []
    signals = []
    zlg_input = []

    for line in lines:
        zlg_input.append(line)
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
                zap_origin = float(split_line[2])
                zap_origin_sft_fac = float(split_line[3])

            else:
                zap_origin = zap_origin_sft_fac = ''

            signal = {'label': signal_lbl,
                      'pk': signal_pk,
                      'zap_origin_pk': zap_origin,
                      'zap_origin_sft_fac': zap_origin_sft_fac}
            signals.append(signal)

    lt_geo = {'sections': sections,
              'switches': switches,
              'signals': signals}

    return lt_geo, zlg_input


def zadParser(station_label):
    """Read and interpret .zad file, which encodes station's auxiliary data.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed.

    Returns
    -------
    dict
        Layout's auxiliary data.
    """
    file_name = 'stations/input/' + station_label + '.zad'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    aux_data = {}
    zad_input = []

    for line in lines:
        zad_input.append(line)
        split_line = line.split()

        if split_line[0] == 'station_name':
            aux_data['station_name'] = concat_string(split_line[1:])

        elif split_line[0] == 'station_lbl':
            aux_data['station_lbl'] = concat_string(split_line[1:])

        elif split_line[0] == 'interlocking_name':
            aux_data['interlocking_name'] = concat_string(split_line[1:])

        elif split_line[0] == 'encoding_author':
            aux_data['encoding_author'] = concat_string(split_line[1:])

        elif split_line[0] == 'date':
            aux_data['date'] = concat_string(split_line[1:])

    return aux_data, zad_input


def concat_string(split_string):
    """Transform a list of string snippets in to a concatenated string.

    Parameters
    ----------
    split_string : list
        List of string snippets.

    Returns
    -------
    str
        Concatenated string.
    """
    string = ''
    first_iter = True
    for snippet in split_string:

        if not first_iter:
            string += ' '

        string += snippet
        first_iter = False

    return string


def zopParser(parameters_label):
    """Read and interpret .zop file, which encodes the operational parameters.

    Parameters
    ----------
    parameters_label : str
        Label of the parameter file to be considered.

    Returns
    -------
    dict
        Operational parameter variables as encoded in the .zop file.
    """
    file_name = 'parameters/' + parameters_label + '.zop'

    with open(file_name, 'r') as file:
        lines = file.readlines()

    parameters = {}
    zop_input = []

    for line in lines:
        zop_input.append(line)
        split_line = line.split()

        if split_line[0] == 'regimes_to_block':
            parameters['regimes_to_block'] = split_line[1:]

        elif split_line[0] == 'regimes_to_NDZ':
            parameters['regimes_to_NDZ'] = split_line[1:]

        elif split_line[0] == 'regimes_to_terminal':
            parameters['regimes_to_terminal'] = split_line[1:]

        elif split_line[0] == 'allow_shunt_to_circ_sig':
            parameters['allow_shunt_to_circ_sig'] = str2bool(split_line[-1])

        elif split_line[0] == 'terminal_branches_are_destinations':
            parameters['terminal_branches_are_destinations'] =\
                str2bool(split_line[-1])

        elif split_line[0] == 'overlap_to_terminal_branch':
            parameters['overlap_to_terminal_branch'] = str2bool(split_line[-1])

        elif split_line[0] == 'main_ol_distance':
            parameters['main_ol_distance'] = float(split_line[-1])

        elif split_line[0] == 'dos_ol_distance':
            parameters['dos_ol_distance'] = float(split_line[-1])

        elif split_line[0] == 'shunt_ol_distance':
            parameters['shunt_ol_distance'] = float(split_line[-1])

        elif split_line[0] == 'horse_neck_possible':
            parameters['horse_neck_possible'] = str2bool(split_line[-1])

        elif split_line[0] == 'logic_ol_possible_regimes':
            parameters['logic_ol_possible_regimes'] = split_line[1:]

        elif split_line[0] == 'logic_ol_switch_point_dependent':
            parameters['logic_ol_switch_point_dependant'] =\
                str2bool(split_line[-1])

        elif split_line[0] == 'allow_distant_switch_OL_lock':
            parameters['allow_distant_switch_OL_lock'] =\
                str2bool(split_line[-1])

        elif split_line[0] == 'derailer_alt_OL_allowed_types':
            parameters['derailer_alt_OL_allowed_types'] = split_line[1:]

        elif split_line[0] == 'derailer_margin':
            parameters['derailer_margin'] = float(split_line[-1])

        elif split_line[0] == 'OL_delay_dist_weight':
            parameters['OL_delay_dist_weight'] = float(split_line[-1])

        elif split_line[0] == 'OL_delay_dist_bias':
            parameters['OL_delay_dist_bias'] = float(split_line[-1])

        elif split_line[0] == 'ARC_delay_dist_weight':
            parameters['ARC_delay_dist_weight'] = float(split_line[-1])

        elif split_line[0] == 'ERC_delay_circ_multiplier':
            parameters['ERC_delay_circ_multiplier'] = float(split_line[-1])

        elif split_line[0] == 'ERC_delay_shunt_multiplier':
            parameters['ERC_delay_shunt_multiplier'] = float(split_line[-1])

        elif split_line[0] == 'RC_min_delay':
            parameters['RC_min_delay'] = float(split_line[-1])

        elif split_line[0] == 'RC_max_delay':
            parameters['RC_max_delay'] = float(split_line[-1])

        elif split_line[0] == 'delay_round_multiple':
            parameters['delay_round_multiple'] = float(split_line[-1])

        elif split_line[0] == 'delay_round_down_allowed':
            parameters['delay_round_down_allowed'] = str2bool(split_line[-1])

        elif split_line[0] == 'shunt_sig_filters_fp':
            parameters['shunt_sig_filters_fp'] = str2bool(split_line[-1])

        elif split_line[0] == 'vital_fp_threshold':
            parameters['vital_fp_threshold'] = float(split_line[-1])

        elif split_line[0] == 'sub_vital_fp_threshold':
            parameters['sub_vital_fp_threshold'] = float(split_line[-1])

        elif split_line[0] == 'remote_fp_threshold':
            parameters['remote_fp_threshold'] = float(split_line[-1])

    return parameters, zop_input


def str2bool(string):
    """Interpret string as boolean value.

    Parameters
    ----------
    string : str
        "True" or "False".

    Returns
    -------
    bool
        Corresponding boolean value.
    """
    if string == 'True':
        return True

    elif string == 'False':
        return False
