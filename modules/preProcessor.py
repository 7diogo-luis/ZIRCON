"""ZIRCON Pre-processor."""

from copy import deepcopy


def preProcessor(lt_top_raw, lt_geo):
    """Infer node signs and add them to the station's layout.

    Parameters
    ----------
    station_label : str
        Label of the station to be processed (<STATION_LABEL>.zlt).
    lt_geo : dict
        Layout's geometry.

    Returns
    -------
    dict
        Station's layout with explicit node signs.
    """
    lt_top_canonical = ILMLabelProc(lt_top_raw)
    layout_canonical = layoutAssembler(lt_top_canonical, lt_geo)
    layout_wo_special_sec_flags = inferNdeSigns(layout_canonical)
    layout = specialSectionFlagsAndSwitchDir(layout_wo_special_sec_flags)

    return layout


def inferNdeSigns(layout_canonical):
    """Infer node signs and add them to the station's layout.

    Parameters
    ----------
    layout_canonical : dict
        Station's layout without node signs.

    Returns
    -------
    list
        Station's layout without flags for special sections, except for TJD,
        which is directly read from the zlt file. Node signs are explicit.
    """
    layout = deepcopy(layout_canonical)

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


def ILMLabelProc(lt_top_raw):
    """Add suffix to ILM labels, alluding to the respective element's label.

    Parameters
    ----------
    lt_top_raw : dict
        Layout's topography with incomplete ILM labels.
    lt_top_canonical : dict
        Layout's topography.
    """
    lt_top_canonical = deepcopy(lt_top_raw)

    for block in lt_top_canonical['blocks']:

        if block['signal'] is not None:

            if block['signal']['label'] == 'M':
                new_label = 'M_' + block['label']
                block['signal']['label'] = new_label

    for ndz in lt_top_canonical['NDZs']:

        if ndz['signal'] is not None:

            if ndz['signal']['label'] == 'M':
                new_label = 'M_' + ndz['label']
                ndz['signal']['label'] = new_label

    for section in lt_top_canonical['sections']:

        for node in section['nodes']:

            if node['signal'] is not None:

                if node['signal']['label'] == 'M':
                    new_label = 'M_' + section['label']
                    node['signal']['label'] = new_label

    return lt_top_canonical


def layoutAssembler(lt_top_canonical, lt_geo):
    """Unify topographic and geometric data in a single dictionary.

    Parameters
    ----------
    lt_top_canonical : dict
        Layout's topography.
    lt_geo : dict
        Layout's geometry.

    Returns
    -------
    dict
        Unified description of the layout (without explicit node signs).
    """
    layout_canonical = deepcopy(lt_top_canonical)

    for lt_top_section in layout_canonical['sections']:

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

                        for block in layout_canonical['blocks']:

                            if block['signal'] is not None:

                                if block['signal']['label'] == lt_geo_signal[
                                         'label']:
                                    block['signal']['pk'] = lt_geo_signal['pk']
                                    block['signal']['zap_origin_pk'] = \
                                        lt_geo_signal['zap_origin_pk']
                                    block['signal']['zap_origin_sft_fac'] = \
                                        lt_geo_signal['zap_origin_sft_fac']

                        for ndz in layout_canonical['NDZs']:

                            if ndz['signal'] is not None:

                                if ndz['signal']['label'] == lt_geo_signal[
                                       'label']:
                                    ndz['signal']['pk'] = lt_geo_signal['pk']
                                    ndz['signal']['zap_origin_pk'] = \
                                        lt_geo_signal['zap_origin_pk']
                                    ndz['signal']['zap_origin_sft_fac'] = \
                                        lt_geo_signal['zap_origin_sft_fac']

    return layout_canonical


def flagTJS(layout):
    """Explicitlly flag TJS sections.

    Parameters
    ----------
    layout : list
        Station's layout with explicit node signs and implicit TJS flag.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            if node['TJS_weak_nde']:
                section['special_type'] = 'TJS'
                break


def flagMultiSwitch(layout):
    """Flag sections with more than one switch. Requires TJD/TJS flags.

    Parameters
    ----------
    layout : list
        Station's layout with explicit node signs and no flags related to
        sections with multiple switches.
    """
    for section in layout['sections']:
        num_switches_at_section_nodes = []

        if (section['special_type'] == 'TJS' or
                section['special_type'] == 'TJD'):
            continue

        for node in section['nodes']:

            switches_at_node = 0

            for switch in node['switches']:

                if switch['lr_pk'] is not None:
                    switches_at_node += 1

            num_switches_at_section_nodes.append(switches_at_node)

        if sum(num_switches_at_section_nodes) > 1:
            section['special_type'] = 'multi_switch'

        if max(num_switches_at_section_nodes) > 1:
            section['special_type'] = 'nested'


def specialSectionFlagsAndSwitchDir(layout_wo_special_sec_flags):
    """Add flags for special sections.

    Parameters
    ----------
    layout_wo_special_sec_flags : list
        Station's layout without flags for special sections, except for TJD,
        which is directly read from the zlt file. Node signs are explicit.

    Returns
    -------
    dict
        Station's layout with special section flags.
    """
    layout = deepcopy(layout_wo_special_sec_flags)
    flagTJS(layout)
    flagMultiSwitch(layout)
    switchDirections(layout)

    return layout


def switchDirections(layout):
    """Add switch effective directions to switch dictionaries.

    Parameters
    ----------
    layout : list
        Station's layout with explicit node signs and no flags related to
        sections with multiple switches.
    """
    for section in layout['sections']:

        for node in section['nodes']:
            node_sign = node['index'][-1]

            for switch in node['switches']:

                if switch['lr_pk'] is None:
                    switch['effective_direction'] = 'bidirectional'

                elif node_sign == '+':
                    switch['effective_direction'] = 'asc'

                else:
                    switch['effective_direction'] = 'desc'
