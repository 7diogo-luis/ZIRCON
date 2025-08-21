"""Automation for railway project documentation validation."""
import pandas as pd
import numpy as np


def sample_data(EXPORT_FILES=False):
    """Create sample data from Mafra station."""
    section_names = ['320', '324', 'I', 'II', '336', '340', '342']
    section_parameters = {'PKi': [32000, 32415, 33043, 33043, 33573, 34000,
                                  34200],
                          'PKf': [32415, 32747, 33272, 33272, 34000, 34200,
                                  34938],
                          'ant': [None, '320', '1', '1', '2', '336', '340'],
                          'post': ['324', '1', '2', '2', '340', '342', None]}

    switch_names = ['1', '2']
    switch_parameters = {'PK_A': [33043, 33272],
                         'PK_B': [33043, 33272],
                         'PK_C': [32747, 33573],
                         'PK_LR': [33028, 33315],
                         'con_A': ['I', 'I'],
                         'con_B': ['II', 'II'],
                         'con_C': ['324', '336']}

    signal_names = ['320D', 'S1', 'S6', 'S4', 'S5', 'S3', 'S2', '349A']
    signal_parameters = {'PK': [32005, 32739, 33048, 33048, 33267, 33267,
                                33581, 34933],
                         'direction': ['desc', 'asc', 'desc', 'desc', 'asc',
                                       'asc', 'desc', 'asc'],
                         'type': ['PV', 'MD', 'MD', 'MD', 'MD', 'MD', 'MD',
                                  'PV']}

    sections = pd.DataFrame(section_parameters, index=section_names)
    switches = pd.DataFrame(switch_parameters, index=switch_names)
    signals = pd.DataFrame(signal_parameters, index=signal_names)

    if EXPORT_FILES:
        sections.to_csv('sections.csv')
        switches.to_csv('switches.csv')
        signals.to_csv('signals.csv')

    return sections, switches, signals


def order_elements(sections, switches):
    """Order elements for refference of all functions."""
    elements = sections.index.to_list() + switches.index.to_list()

    return elements


def adjacency_matrix(elements, sections, switches):
    """Assemble adjacency matrix."""
    num_elements = len(elements)
    A = np.zeros([num_elements, num_elements])

    for index, element in zip([i for i in range(num_elements)], elements):

        if element in sections.index:
            ant = sections.loc[element].ant
            post = sections.loc[element].post

            if ant is not None:
                index_ant = elements.index(ant)
                A[index][index_ant] = 1

            if post is not None:
                index_post = elements.index(post)
                A[index][index_post] = 1

        else:
            con_A = switches.loc[element].con_A
            con_B = switches.loc[element].con_B
            con_C = switches.loc[element].con_C

            if con_A is not None:
                index_con_A = elements.index(con_A)
                A[index][index_con_A] = 1

            if con_B is not None:
                index_con_B = elements.index(con_B)
                A[index][index_con_B] = 1

            if con_C is not None:
                index_con_C = elements.index(con_C)
                A[index][index_con_C] = 1

    return A


def degree_matrix(elements, sections, switches, A, direction='bidirectional'):
    """Assembles degree matrix."""
    num_elements = len(elements)
    D = np.zeros([num_elements, num_elements])

    for index in range(num_elements):

        if direction == 'bidirectional':
            D[index][index] = sum(A[index])
        elif direction == 'asc':
            element = elements[index]
            if element in sections.index:
                if sections.loc[element].post is not None:
                    D[index][index] = 1
            elif element in switches.index:
                con_A = switches.loc[element].con_A
                con_B = switches.loc[element].con_B
                con_C = switches.loc[element].con_C
                    

    return D


def laplacian_matrix(A, D):
    """Compute the Laplacian matrix."""
    L = D - A

    return L


def mafra_D(direction='bidirectional'):
    """Artificially build D matrix for Mafra."""
    D = np.zeros([9, 9])

    if direction == 'asc':
        D[0, 0] = 1
        D[1, 1] = 1
        D[2, 2] = 1
        D[3, 3] = 1
        D[4, 4] = 1
        D[5, 5] = 1
        D[6, 6] = 0
        D[7, 7] = 2
        D[8, 8] = 1
    elif direction == 'desc':
        D[0, 0] = 0
        D[1, 1] = 1
        D[2, 2] = 1
        D[3, 3] = 1
        D[4, 4] = 1
        D[5, 5] = 1
        D[6, 6] = 1
        D[7, 7] = 1
        D[8, 8] = 2
    else:
        D[0, 0] = 1
        D[1, 1] = 2
        D[2, 2] = 2
        D[3, 3] = 2
        D[4, 4] = 2
        D[5, 5] = 2
        D[6, 6] = 1
        D[7, 7] = 3
        D[8, 8] = 3

    return D
