"""
ZIRCON graphical user interface subsystem.

This module defines the `ZIRCON_GUI` class, which implements the main
Tkinter-based user interface for the ZIRCON application. It coordinates
user interactions, delegates actions to domain-specific subsystems,
and updates shared application state through the `persist` dictionary.
"""

import tkinter as tk
from tkinter import ttk

import subsystems.GUIActions as gui
from subsystems.inputLayer import inputLayer
from subsystems.core import core
from subsystems.outputLayer import outputLayer


class ZIRCON_GUI:
    """
    Main graphical user interface controller for the ZIRCON application.

    This class is responsible for:
    - Creating and managing the Tkinter window lifecycle
    - Building the user interface layout
    - Handling user-triggered events (load, process, export)
    - Coordinating calls to input, core, and output subsystems
    - Updating shared application state via the `persist` dictionary

    The GUI runs in a blocking Tkinter main loop and relies on side
    effects rather than return values for state propagation.
    """

    def __init__(self, sw_version, icon_path, loaded_layout, processed_layout, persist):
        """
        Initialize the GUI and start the Tkinter main event loop.

        Parameters
        ----------
        sw_version : str
            Current software version identifier, displayed in the GUI.
        icon_path : str
            Filesystem path to the application icon image.
        loaded_layout : bool
            Initial flag indicating whether a layout has been loaded.
        processed_layout : bool
            Initial flag indicating whether the layout has been processed.
        persist : dict
            Shared application state dictionary. This object is mutated
            throughout the GUI lifecycle to store layouts, parameters,
            signals, and export results.

        Notes
        -----
        - This constructor starts the Tkinter `mainloop()` and therefore
          blocks until the GUI is closed.
        - All state updates occur through the `persist` dictionary.
        """

        self.sw_version = sw_version

        # ---- GUI state (returned values live here) ----
        self.result = None
        self.loaded_layout = loaded_layout
        self.processed_layout = processed_layout
        self.persist = persist
        self.file_format = '.xlsx'

        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.root.title("ZIRCON")
        self.root.geometry("420x320")
        self.root.resizable(True, True)

        # Icon
        try:
            icon_image = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, icon_image)
        except Exception:
            # Icon loading failure should not prevent GUI startup
            pass

        self.build_ui()
        self.root.mainloop()

    # ======================
    # UI
    # ======================
    def build_ui(self):
        """
        Construct and layout all GUI widgets.

        This method creates:
        - Header section with application title
        - Main content area with action buttons
        - Footer section with version and help controls

        Notes
        -----
        Widget callbacks are bound to instance methods that handle
        application logic and subsystem coordination.
        """

        header_frame = tk.Frame(self.root, bg="#2b2b2b", height=60)
        header_frame.pack(fill="x")

        tk.Label(
            header_frame,
            text="ZIRCON",
            fg="white",
            bg="#2b2b2b",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=15)

        content_frame = tk.Frame(self.root, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)

        ttk.Button(
            content_frame,
            text="Load",
            command=self.on_load,
            width=22
        ).pack(pady=5)

        ttk.Button(
            content_frame,
            text="Process",
            command=self.on_process,
            width=22
        ).pack(pady=5)

        ttk.Button(
            content_frame,
            text="Export Excel",
            command=self.on_exportExcel,
            width=22
        ).pack(pady=5)

        ttk.Button(
            content_frame,
            text="Export Pickle",
            command=self.on_exportPickle,
            width=22
        ).pack(pady=5)

        footer_frame = tk.Frame(self.root)
        footer_frame.pack(fill="x", pady=10)

        ttk.Button(
            footer_frame,
            text="Version",
            command=lambda: gui.open_version_window(self.root, self.sw_version),
            width=10
        ).pack(side="left", padx=20)

        ttk.Button(
            footer_frame,
            text="Help",
            command=lambda: gui.open_help_window(self.root),
            width=10
        ).pack(side="right", padx=20)

    # ======================
    # Button handlers
    # ======================
    def on_load(self):
        """
        Handle the "Load" button action.

        Opens a file selection dialog and loads a layout through the
        input subsystem. Updates shared state with layout data and
        auxiliary metadata.

        Side Effects
        ------------
        Updates the following keys in `persist`:
        - 'layout'
        - 'aux_data'
        - 'inputs'
        - 'loaded_layout'
        """

        result = gui.load(self.root)

        if result["action"] != "load":
            return

        layout, parameters, aux_data, inputs = inputLayer(result['modifier'], None)
        aux_data['sw_version'] = self.persist['sw_version']

        self.persist['layout'] = layout
        self.persist['aux_data'] = aux_data
        self.persist['inputs'] = inputs
        self.persist['loaded_layout'] = True

        print("Layout loaded")

    def on_process(self):
        """
        Handle the "Process" button action.

        Validates that a layout has been loaded, processes it through
        the core subsystem, and stores derived signals, paths, movements,
        and delays in shared state.

        Returns
        -------
        dict or None
            Result dictionary returned by the GUI action handler, or
            `None` if processing was aborted.

        Side Effects
        ------------
        Updates multiple keys in `persist`, including:
        - 'parameters'
        - 'signals'
        - 'paths'
        - 'movements'
        - 'delays'
        - 'processed_layout'
        """

        self.result = gui.process(self.root, self.persist['loaded_layout'])

        if self.result["action"] == "process":
            self.persist['processed_layout'] = True

            layout, parameters, aux_data, inputs = inputLayer(
                None,
                self.result['modifier']
            )

            self.persist['inputs']['zop'] = inputs['zop']
            self.persist['parameters'] = parameters

            signals, paths, movements, delays = core(
                self.persist['layout'],
                self.persist['parameters']
            )

            self.persist['signals'] = signals
            self.persist['paths'] = paths
            self.persist['movements'] = movements
            self.persist['delays'] = delays
            self.persist['processed_layout'] = True

        print("Result:", self.result)
        return self.result

    def on_exportExcel(self):
        """
        Handle the "Export Excel" button action.

        Exports processed data to an Excel file via the output subsystem.

        Returns
        -------
        dict or None
            Updated `persist` dictionary if export succeeds, otherwise
            `None`.

        Notes
        -----
        Export is only allowed after successful layout processing.
        """

        if not self.persist['processed_layout']:
            print("Process layout first")
            return

        result = gui.export(self.root, self.persist['processed_layout'], 'xlsx')

        if result["action"] != "export":
            return

        interlocking_prog = outputLayer(
            self.persist['movements'],
            self.persist['delays'],
            self.persist['aux_data'],
            self.persist['inputs'],
            self.persist['layout'],
            self.persist['signals'],
            result["modifier"]
        )

        self.persist['interlocking_prog'] = interlocking_prog
        print("Excel exported")
        return self.persist

    def on_exportPickle(self):
        """
        Handle the "Export Pickle" button action.

        Serializes processed data using the pickle format through the
        output subsystem.

        Notes
        -----
        Export is only allowed after successful layout processing.
        """

        if not self.persist['processed_layout']:
            print("Process layout first")
            return

        result = gui.export(self.root, self.persist['processed_layout'], 'pickle')

        if result["action"] != "export":
            return

        interlocking_prog = outputLayer(
            self.persist['movements'],
            self.persist['delays'],
            self.persist['aux_data'],
            self.persist['inputs'],
            self.persist['layout'],
            self.persist['signals'],
            result["modifier"]
        )

        self.persist['interlocking_prog'] = interlocking_prog
        print("Pickle exported")

    def on_exit(self):
        """
        Handle application shutdown.

        Destroys the Tkinter root window and exits the GUI event loop.
        """

        self.root.destroy()