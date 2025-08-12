""" Discontinued code."""


def isDerailer(label, layout):
    """Find if a switch is a derailer.

    Parameters
    ----------
    label : str
        Label of the switch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    bool
        True if the switch is a derailer, False if not.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if label == switch['label'] and switch['lr_pk'] is None:

                    return True

    return False


def getSwitchSection(label, layout):
    """Get the section where a switch (inc. derailer) lies.

    Parameters
    ----------
    label : str
        Label of the switch to be evaluated.
    layout : dict
        Description of the station's layout.

    Returns
    -------
    str
        Label of the section where the evaluated switch lies.
    """
    for section in layout['sections']:

        for node in section['nodes']:

            for switch in node['switches']:

                if label == switch['label']:

                    return section['label']


def consecSwitch(path, switch_pos, layout, adjacency_data, no_derailer=True):
    """Find if a path crosses more than one switch at a certain position.

    Parameters
    ----------
    path : dict
        Dictionary containing the sections crossed by a given path, as well
           as the respective transits.
    switch_pos : str
        Relevant switch position.
    layout : dict
        Description of the station's layout.
    adjacency_data : dict
        Dictionary containing the adjacency matrix (as a Numpy Array) and a
        list of the layout elements, indexed congruently with the adjacency
        matrix.
    no_derailer : bool
        True if derailers are to be ignored, False otherwise

    Returns
    -------
    list
        List of lists, each representing a streak of crossed sections where a
        point commanded in the relevant position exists.
    """
    consec = []
    temp = []

    for com_swi in path['switch_positions']:

        if not (isDerailer(com_swi['SWI_lbl'], layout) and no_derailer):
            nxt_sec = getSwitchSection(com_swi['SWI_lbl'], layout)

            if com_swi['SWI_pos'] == switch_pos:

                if temp:

                    if isContiguous(temp[-1], nxt_sec, adjacency_data):
                        temp.append(nxt_sec)

                    elif temp[-1] == nxt_sec:
                        pass

                    else:

                        if len(temp) > 1:
                            consec.append(temp)
                        temp = []
                        temp.append(nxt_sec)

                else:
                    temp.append(nxt_sec)

            else:

                if temp:

                    if temp[-1] == nxt_sec:
                        pass

                    elif len(temp) > 1:
                        consec.append(temp)

                temp = []

    if len(temp) > 1:
        consec.append(temp)

    return consec

