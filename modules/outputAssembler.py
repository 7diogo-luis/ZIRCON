"""ZIRCON Output Assembler."""

def outputAssembler(movements, delays, inputs):
    
    route_example = {'rt_ID': None,
                     'origin_loc': None,
                     'origin_sig': None,
                     'destination_loc': None,
                     'destination_sig': None,
                     'regime': None,
                     'alt_ol': None,
                     'alt_rt': None,
                     'obs': None,
                     'switches': None,
                     'sections': None,
                     'blocks': None}

    cover = {'station_name': None,
             'station_lbl': None,
             'interlocking_name': None,
             'sw_version': None}

    circulation = {'normal_entry': [],
                   'normal_exit': [],
                   'reverse_entry': [route_example],
                   'reverse_exit': []}

    shunt = {'forward': [],
             'backward': []}

    delays = {'overlap': [],
              'approach_rt_cncl': [],
              'emerg_rt_cncl': []}

    inputs = {'zlt': [],
              'zlg': [],
              'zop': []}

    PEE = {'COVER': cover,
           'CIRCULATION': circulation,
           'SHUNT': shunt,
           'DELAYS': delays,
           'INPUTS': inputs}

    return PEE




# switch = {'rt': {'normal': '',
#                  'reverse': ''},
#           'ol': {'normal': '',
#                  'reverse': ''},
#           'fp': {'rt': {'normal': '',
#                         'reverse': ''},
#                  'ol': {'normal': '',
#                         'reverse': ''}}}

# section = {'rt': '',
#            'ol': '',
#            'fp': {'rt': {'vital': '',
#                          'sub_vital': '',
#                          'remote': ''},
#                   'ol': {'vital': '',
#                          'sub_vital': '',
#                          'remote': ''}}}

# block = {'up': '',
#          'down': ''}







# route_1 = {'rt_ID': '1',
#            'origin_loc': 'BPF',
#            'origin_sig': 'S1',
#            'destination_loc': 'MAF_II',
#            'destination_sig': 'S3',
#            'regime': 'Main',
#            'alt_ol': None,
#            'alt_rt': None,
#            'obs': None,
#            'switches': {'rt': {'normal': '1',
#                             'reverse': ''},
#                      'ol': {'normal': '2',
#                             'reverse': ''},
#                      'fp': {'rt': {'normal': '',
#                                    'reverse': ''},
#                             'ol': {'normal': '',
#                                    'reverse': ''}}},
#            'sections': {'rt': '1, I',
#                       'ol': '2',
#                       'fp': {'rt': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''},
#                              'ol': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''}}},
#            'blocks': {'up': '',
#                     'down': ''}}

# route_2 = {'rt_ID': '2',
#            'origin_loc': 'BPF',
#            'origin_sig': 'S1',
#            'destination_loc': 'MAF_II',
#            'destination_sig': 'S3',
#            'regime': 'DOS',
#            'alt_ol': None,
#            'alt_rt': None,
#            'obs': None,
#            'switches': {'rt': {'normal': '1',
#                             'reverse': ''},
#                      'ol': {'normal': '2',
#                             'reverse': ''},
#                      'fp': {'rt': {'normal': '',
#                                    'reverse': ''},
#                             'ol': {'normal': '',
#                                    'reverse': ''}}},
#            'sections': {'rt': '',
#                       'ol': '',
#                       'fp': {'rt': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''},
#                              'ol': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''}}},
#            'blocks': {'up': '',
#                     'down': ''}}

# route_3 = {'rt_ID': '3',
#            'origin_loc': 'MAF_I',
#            'origin_sig': 'S5',
#            'destination_loc': 'MAL',
#            'destination_sig': 'MAL',
#            'regime': 'Main',
#            'alt_ol': None,
#            'alt_rt': None,
#            'obs': None,
#            'switches': {'rt': {'normal': '',
#                             'reverse': '2'},
#                      'ol': {'normal': '',
#                             'reverse': ''},
#                      'fp': {'rt': {'normal': '',
#                                    'reverse': ''},
#                             'ol': {'normal': '',
#                                    'reverse': ''}}},
#            'sections': {'rt': '2',
#                       'ol': '',
#                       'fp': {'rt': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''},
#                              'ol': {'vital': '',
#                                     'sub_vital': '',
#                                     'remote': ''}}},
#            'blocks': {'up': 'MAF-MAL',
#                     'down': ''}}

# cover = {'station_name': 'Mafra',
#          'station_lbl': 'MAF',
#          'interlocking_name': 'Linha do Oeste',
#          'sw_version': 'v0.18.0'}

# circulation = {'normal_entry': [route_1, route_2],
#                'normal_exit': [route_3],
#                'reverse_entry': [],
#                'reverse_exit': []}

# shunt = {'forward': [],
#          'backward': []}

# delays = {'overlap': [{'track': 'I',
#                        'delay': '50'}],
#           'approach_rt_cncl': [{'signal': 'S1',
#                                 'delay': '75'}],
#           'emerg_rt_cncl': [{'destination': 'MAL',
#                              'delay': '250'}]}

# inputs = {'zlt': ['sample', 'test'],
#           'zlg': ['nothing'],
#           'zop': ['par', 'par2']}

# PEE = {'COVER': cover,
#        'CIRCULATION': circulation,
#        'SHUNT': shunt,
#        'DELAYS': delays,
#        'INPUTS': inputs}