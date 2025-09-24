"""ZIRCON Command Line Interface."""


def cli(sw_version, loaded_layout, processed_layout):
    """Prompt user and register commands.

    Parameters
    ----------
    sw_version : str
        ZIRCON software version.
    loaded_layout : bool
        True if a layout has been loaded, False otherwise.
    processed_layout : bool
        True if a layout has been processed, False otherwise.

    Returns
    -------
    dict
        User's commands.
    """
    commands = {'load': ('\tLoad station layout from .zlt .zlg and .zad files'
                         '\n\tSyntax: load [STATION_LABEL]'),
                'process': ('\tProcess the loaded layout according to selected'
                            'parameters\n\tSyntax: proc [ZOP_FILE_NAME]'),
                'export': ('\tExport the results of layout processing with'
                           'format "pickle" or "xlsx"\n\tSyntax: export'
                           ' [FORMAT]'),
                'exit': '\tStop execution',
                'version': '\tPrint ZIRCON software version',
                'help': '\tList commands their and descriptions'}

    usr_input = str(input('ZIRCON -> '))
    split_usr_input = usr_input.split()

    if split_usr_input[0] not in commands.keys():
        print('Invalid command')

        return {'action': None,
                'modifier': None}

    elif (split_usr_input[0] == 'inspect' or split_usr_input[0] == 'exit' or
          split_usr_input[0] == 'version' or split_usr_input[0] == 'help'):

        if len(split_usr_input) != 1:
            print('Invalid syntax')

            return {'action': None,
                    'modifier': None}

    elif (split_usr_input[0] == 'load' or split_usr_input[0] == 'process' or
          split_usr_input[0] == 'export'):

        if len(split_usr_input) != 2:
            print('Invalid syntax')

            return {'action': None,
                    'modifier': None}

    if split_usr_input[0] == 'help':

        for key in commands.keys():
            print(key)
            print(commands[key])
            print()

        return {'action': None,
                'modifier': None}

    elif split_usr_input[0] == 'version':
        print(sw_version)

        return {'action': None,
                'modifier': None}

    elif split_usr_input[0] == 'exit':

        return {'action': 'exit',
                'modifier': None}

    elif split_usr_input[0] == 'load':
        return {'action': 'load',
                'modifier': split_usr_input[1]}

    elif split_usr_input[0] == 'process':

        if not loaded_layout:
            print('No layout was loaded')

            return {'action': None,
                    'modifier': None}

        else:
            return {'action': 'process',
                    'modifier': split_usr_input[1]}

    elif split_usr_input[0] == 'export':

        if not processed_layout:
            print('No layout was processed')

            return {'action': None,
                    'modifier': None}

        else:
            return {'action': 'export',
                    'modifier': split_usr_input[1]}
