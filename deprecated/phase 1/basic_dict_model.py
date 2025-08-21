"""Structure of the layout dict. Sample for Bifurcação de Sapataria."""

# detail of node dict
node = {'lbl': 'A',
        'pk': 43942,
        'adj': 'A1',
        'adj_nde': 'B'}


# detail of signal dict

signal = {'lbl': 'S1',
          'pk': 43934}


# detail of point dict

point = {'lbl': '2',
         'pk_lr': 1,
         'pk_tip': 2,
         'spec_trans': ['AB']}


# detail of section dict

section = {'lbl': 'I',
           'nodes': [node],
           'transits': ['AB'],
           'signals': [signal],
           'points': [point]}


# detail of station dict

station = {'label': 'BSP',
           'sections': [section]}


# detain of block dict

block = {'lbl': 'CEABCDEFA',
         'stations': ['S1', 'S2'],
         'dir': 'asc'}


# detail of layout dict

layout = {'stations': [station],
          'blocks': [block]}
