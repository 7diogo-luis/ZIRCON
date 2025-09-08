"""ZIRCON Signal Processor."""

import pandas as pd
from copy import deepcopy


def signalProcessor(layout, allow_terminal_branches, reg_to_block, reg_to_ndz,
                    reg_to_terminal, allow_shunt_to_circ_sig):
    """Generate a table containing relevant info on real and virtual signals.

    Parameters
    ----------
    layout : dict
        Description of the station's layout.
    allow_terminal_branches : bool
        True if terminal section branches are to be consideres virtual signals,
        False otherwise.
    reg_to_block : list
        List of strings, each corresponding to a regime that is possible with a
        block as destination.
    reg_to_ndz : list
        List of strings, each corresponding to a regime that is possible with a
        NDZ as destination.
    reg_to_terminal : list
        List of strings, each corresponding to a regime that is possible with a
        terminal section as destination.

    Returns
    -------
    Pandas DataFrame
        Table of signals and their respective properties.
    """
    sig_table = sigTable(layout, allow_terminal_branches)
    signals = sigDecoder(sig_table, layout, reg_to_block, reg_to_ndz,
                         reg_to_terminal, allow_shunt_to_circ_sig)

    return signals


def sigTable(layout, allow_terminal_branches):
    """Generate a table containing basic info on real and virtual signals.

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
                                      'alt_origin',
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
                                                 'alt_origin': False,
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
                                                 'alt_origin': False,
                                                 'prev_sec': prev_sec}

            if node['con_ele'] is None and (len(section['nodes']) == 2
                                            or allow_terminal_branches):
                signal = section['label']
                section_lbl = section['label']
                direction = 'desc' if node['index'][-1] == '-' else 'asc'

                for node2 in section['nodes']:
                    prev_sec_cand = node2['con_ele']
                    prev_sec_cand_sign = node2['index'][-1]
                    terminal_nde_sign = node['index'][-1]

                    if (prev_sec_cand is not None and
                            prev_sec_cand_sign != terminal_nde_sign):
                        prev_sec = prev_sec_cand

                sig_table.loc[len(sig_table)] = {'signal': signal,
                                                 'section': section_lbl,
                                                 'direction': direction,
                                                 'virtual': True,
                                                 'alt_origin': False,
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
                             'virtual': False,
                             'alt_origin': False,
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
                             'virtual': False,
                             'alt_origin': False,
                             'prev_sec': prev_sec}

    return sig_table


def sigLogic(circ, shunt, ILM, pedal, RW, block, NDZ, terminal, reg_to_block,
             reg_to_ndz, reg_to_terminal, allow_shunt_to_circ_sig):
    """AUX. Derive signal abilities from flags.

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
    reg_to_block : list
        List of strings, each corresponding to a regime that is possible with a
        block as destination.
    reg_to_ndz : list
        List of strings, each corresponding to a regime that is possible with a
        NDZ as destination.
    reg_to_terminal : list
        List of strings, each corresponding to a regime that is possible with a
        terminal section as destination.
    allow_shunt_to_circ_sig : bool
        True if shunting movements with circulation signals (no shunt lights)
        as destinations are to be allowed. False otherwise.

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

        if not allow_shunt_to_circ_sig:
            S_destiny = False

    if not pedal:
        D_origin = False

    if RW:
        M_origin = False

    if block:
        M_origin = D_origin = S_origin = False
        M_destiny = D_destiny = S_destiny = False

        if 'Main' in reg_to_block:
            M_destiny = True

        if 'DOS' in reg_to_block:
            D_destiny = True

        if 'Shunt' in reg_to_block:
            S_destiny = True

    if terminal:
        M_origin = D_origin = S_origin = False
        M_destiny = D_destiny = S_destiny = False

        if 'Main' in reg_to_terminal:
            M_destiny = True

        if 'DOS' in reg_to_terminal:
            D_destiny = True

        if 'Shunt' in reg_to_terminal:
            S_destiny = True

    if NDZ:
        M_origin = D_origin = S_origin = False
        M_destiny = D_destiny = S_destiny = False

        if 'Main' in reg_to_ndz:
            M_destiny = True

        if 'DOS' in reg_to_ndz:
            D_destiny = True

        if 'Shunt' in reg_to_ndz:
            S_destiny = True

    if ILM:
        S_origin = M_origin = D_origin = M_destiny = D_destiny = False
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


def sigDecoder(sig_table, layout, reg_to_block, reg_to_ndz, reg_to_terminal,
               allow_shunt_to_circ_sig):
    """Decode signal names and flags.

    Parameters
    ----------
    sig_table : Pandas DataFrame
        Signal table.
    layout : dict
        Description of the station's layout.
    reg_to_block : list
        List of strings, each corresponding to a regime that is possible with a
        block as destination.
    reg_to_ndz : list
        List of strings, each corresponding to a regime that is possible with a
        NDZ as destination.
    reg_to_terminal : list
        List of strings, each corresponding to a regime that is possible with a
        terminal section as destination.

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
                        ILM = True if 'M_' in row['signal'] else False
                        pedal = node['signal']['pedal']
                        RW = node['signal']['RW']
                        block = True if row['signal'] in blocks else False
                        NDZ = True if row['signal'] in NDZs else False
                        terminal = True if row['signal'] in secs else False

                        signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                    RW, block, NDZ, terminal,
                                                    reg_to_block, reg_to_ndz,
                                                    reg_to_terminal,
                                                    allow_shunt_to_circ_sig)

                        signals.loc[index, 'possible_origin'] =\
                            signal_abilities['possible_origin']
                        signals.loc[index, 'possible_destiny'] =\
                            signal_abilities['possible_destiny']

        for block_dict in layout['blocks']:

            if block_dict['signal'] is not None:

                if block_dict['signal']['label'] == row['signal']:

                    circ = True if 'S' in row['signal'] else False
                    shunt = True if 'M' in row['signal'] else False
                    ILM = True if 'M_' in row['signal'] else False
                    pedal = block_dict['signal']['pedal']
                    RW = block_dict['signal']['RW']
                    block = True if row['signal'] in blocks else False
                    NDZ = True if row['signal'] in NDZs else False
                    terminal = True if row['signal'] in secs else False

                    signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                RW, block, NDZ, terminal,
                                                reg_to_block, reg_to_ndz,
                                                reg_to_terminal,
                                                allow_shunt_to_circ_sig)

                    signals.loc[index, 'possible_origin'] =\
                        signal_abilities['possible_origin']
                    signals.loc[index, 'possible_destiny'] =\
                        signal_abilities['possible_destiny']

        for ndz_dict in layout['NDZs']:

            if ndz_dict['signal'] is not None:

                if ndz_dict['signal']['label'] == row['signal']:

                    circ = True if 'S' in row['signal'] else False
                    shunt = True if 'M' in row['signal'] else False
                    ILM = True if 'M_' in row['signal'] else False
                    pedal = block_dict['signal']['pedal']
                    RW = block_dict['signal']['RW']
                    block = True if row['signal'] in blocks else False
                    NDZ = True if row['signal'] in NDZs else False
                    terminal = True if row['signal'] in secs else False

                    signal_abilities = sigLogic(circ, shunt, ILM, pedal,
                                                RW, block, NDZ, terminal,
                                                reg_to_block, reg_to_ndz,
                                                reg_to_terminal,
                                                allow_shunt_to_circ_sig)

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
                                        RW, block, NDZ, terminal,
                                        reg_to_block, reg_to_ndz,
                                        reg_to_terminal,
                                        allow_shunt_to_circ_sig)

            signals.loc[index, 'possible_origin'] =\
                signal_abilities['possible_origin']
            signals.loc[index, 'possible_destiny'] =\
                signal_abilities['possible_destiny']

    altOrigin(signals)

    return signals


def altOrigin(signals):
    """Flag repeated (alternative origin) signals.

    Parameters
    ----------
    sig_table : Pandas DataFrame
        Signal table containing the possible itinerary types departing from
        and arriving to each signal.
    """
    mask = signals.signal.duplicated(keep=False)
    alt_origin_indices = signals.index[mask].tolist()

    for alt_origin_index in alt_origin_indices:
        signals.at[alt_origin_index, "alt_origin"] = True
