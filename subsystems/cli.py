"""ZIRCON CLI."""


def cli():
    """Prompt user and register commands.

    Returns
    -------
    dict
        User's commands.
    """
    usr_input = input('ZIRCON -> ')

    split_usr_input = usr_input.split()

    if 'proc' in split_usr_input:

        if len(split_usr_input) != 3:
            return

        station_label = split_usr_input[1]
        parameters_label = split_usr_input[2]

        return {'station_label': station_label,
                'parameters_label': parameters_label}

    elif (usr_input == 'exit' or usr_input == 'debug' or
          usr_input == 'prod'):

        return usr_input
