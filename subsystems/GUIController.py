"""Copyright (c) 2025-present Diogo Luís.

Distributed under the MIT software license, see the accompanying
file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""

from subsystems.ZIRCON_GUI import ZIRCON_GUI


def GUIController(persist):
    """
    High-level controller responsible for initializing and coordinating
    the graphical user interface subsystem.

    This function acts as an entry point for the GUI layer, forwarding
    relevant application state from the `persist` dictionary to the
    `ZIRCON_GUI` subsystem. It relies on side effects to modify shared
    state rather than returning a value.

    Parameters
    ----------
    persist : dict
        Dictionary containing the current application state.
        Expected keys include:

        - 'sw_version' : str
            Current software version identifier.
        - 'icon_path' : str
            Filesystem path to the application icon.
        - 'loaded_layout' : Any
            Raw layout configuration loaded from storage.
        - 'processed_layout' : Any
            Layout configuration after processing or transformation.

        This dictionary may be mutated by the GUI subsystem.

    Returns
    -------
    None
        This function does not return a value. All updates are applied
        through shared state and subsystem side effects.
    """

    print("Controller started")

    ZIRCON_GUI(
        sw_version=persist['sw_version'],
        icon_path=persist['icon_path'],
        loaded_layout=persist['loaded_layout'],
        processed_layout=persist['processed_layout'],
        persist=persist
    )
