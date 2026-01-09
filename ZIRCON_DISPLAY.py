from subsystems.GUIController import GUIController

persist = {
    'sw_version': 'v1.0.2',
    'icon_path': 'subsystems/Resources/ZIRCON.png',
    'loaded_layout': False,
    'processed_layout': False,
    'station_label': None,
    'layout': None,
    'parameters': None,
    'aux_data': None,
    'inputs': None,
    'signals': None,
    'paths': None,
    'movements': None,
    'delays': None,
    'interlocking_prog': None
}

GUIController(persist)
