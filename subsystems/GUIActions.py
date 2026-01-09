"""
GUI action handlers and auxiliary windows for the ZIRCON application.

This module contains:
- Button action routing logic
- File dialog helpers
- Simple modal windows (Version, Help)
- Lightweight wrappers for load, process, export, and exit actions

All functions return structured dictionaries describing the requested
action, allowing higher-level controllers to interpret and execute
application logic.
"""

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter import filedialog


# ======================
# Actions
# ======================
def on_button_click(action, root, layout_value=False, file_format=".xlsx"):
    """
    Dispatch a GUI button action to the appropriate handler.

    Parameters
    ----------
    action : str
        Identifier of the requested action (e.g. 'load', 'process',
        'export', 'exit').
    root : tkinter.Tk
        Root Tkinter window used as the parent for dialogs.
    layout_value : bool, optional
        Flag indicating whether a layout has already been loaded or
        processed, depending on the action context.
    file_format : str, optional
        File format extension used for export actions.

    Returns
    -------
    dict
        Dictionary describing the requested action and its modifier.
    """

    return options(action, root, layout_value, file_format)


def open_version_window(root, sw_version):
    """
    Open a modal window displaying application version information.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.
    sw_version : str
        Current software version identifier.

    Notes
    -----
    This function creates a non-resizable `Toplevel` window.
    """

    win = tk.Toplevel(root)
    win.title("ZIRCON – Version")
    win.geometry("350x235")
    win.resizable(False, False)

    ttk.Label(
        win,
        text="ZIRCON",
        font=("Segoe UI", 16, "bold")
    ).pack(pady=(20, 5))

    ttk.Label(
        win,
        text="Version " + sw_version,
        font=("Segoe UI", 11)
    ).pack(pady=2)

    ttk.Label(
        win,
        text="Image Processing Tool",
        font=("Segoe UI", 10)
    ).pack(pady=2)

    ttk.Separator(win).pack(fill="x", padx=20, pady=15)

    ttk.Label(
        win,
        text="Developed by: Diogo Luís\n© 2026",
        font=("Segoe UI", 9),
        justify="center"
    ).pack()

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=15)


def open_help_window(root):
    """
    Open a modal help window with basic usage instructions.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.

    Notes
    -----
    The help text is displayed in a read-only `Text` widget.
    """

    win = tk.Toplevel(root)
    win.title("ZIRCON – Help")
    win.geometry("420x350")
    win.resizable(False, False)

    ttk.Label(
        win,
        text="Help",
        font=("Segoe UI", 16, "bold")
    ).pack(pady=(15, 10))

    help_text = (
        "1. Click 'Load' to load station layout from .zlt .zlg and .zad files.\n\n"
        "2. Click 'Process' to select the parameters to process the loaded layout.\n\n"
        "3. Click 'Export Excel' to export the results of layout processing in Excel.\n\n"
        "4. Click 'Export Pickle' to export the results of layout processing in Pickle.\n\n"
        "For issues or questions, contact support."
    )

    text_box = tk.Text(
        win,
        wrap="word",
        height=13,
        width=45,
        padx=10,
        pady=10
    )
    text_box.insert("1.0", help_text)
    text_box.config(state="disabled")
    text_box.pack(padx=15, pady=5)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


# ======================
# File Explorer
# ======================
def file_opener(root):
    """
    Open a file selection dialog and return the selected file path.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.

    Returns
    -------
    str
        Full filesystem path to the selected file, or an empty string
        if the dialog is cancelled.
    """

    file_path = filedialog.askopenfilename(
        title="Select a File",
        filetypes=[("All files", "*.*")]
    )

    return file_path


# ======================
# Load
# ======================
def load(root):
    """
    Handle a layout load request.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.

    Returns
    -------
    dict
        Action descriptor with keys:
        - 'action' : str
            Always 'load'
        - 'modifier' : str
            Stem of the selected filename
    """

    path = file_opener(root)
    filename = Path(path).stem
    print(f"Selected file: {filename}")

    return {
        'action': 'load',
        'modifier': filename
    }


# ======================
# Process
# ======================
def process(root, loaded_layout):
    """
    Handle a layout processing request.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.
    loaded_layout : bool
        Indicates whether a layout has already been loaded.

    Returns
    -------
    dict
        Action descriptor with keys:
        - 'action' : str or None
        - 'modifier' : str or None
    """

    if not loaded_layout:
        print('No layout was loaded')
        return {
            'action': None,
            'modifier': None
        }

    path = file_opener(root)
    filename = Path(path).stem
    print(f"Selected file: {filename}")

    return {
        'action': 'process',
        'modifier': filename
    }


# ======================
# Export
# ======================
def export(root, processed_layout, file_format):
    """
    Handle an export request.

    Parameters
    ----------
    root : tkinter.Tk
        Parent Tkinter window.
    processed_layout : bool
        Indicates whether the layout has already been processed.
    file_format : str
        File format identifier (e.g. '.xlsx', 'pickle').

    Returns
    -------
    dict
        Action descriptor with keys:
        - 'action' : str or None
        - 'modifier' : str or None
    """

    if not processed_layout:
        print('No layout was processed')
        return {
            'action': None,
            'modifier': None
        }

    return {
        'action': 'export',
        'modifier': file_format
    }


# ======================
# Exit
# ======================
def exit_app():
    """
    Handle an application exit request.

    Returns
    -------
    dict
        Action descriptor indicating an exit request.
    """

    return {
        'action': 'Exit',
        'modifier': None
    }


# ======================
# Options
# ======================
def options(selected_option, root, layout_value, file_format):
    """
    Route a selected GUI option to the corresponding handler.

    Parameters
    ----------
    selected_option : str
        Selected action identifier.
    root : tkinter.Tk
        Parent Tkinter window.
    layout_value : bool
        Layout state flag used by process and export actions.
    file_format : str
        File format for export actions.

    Returns
    -------
    dict or None
        Action descriptor dictionary, or `None` if the option is invalid.
    """

    match selected_option:
        case "exit":
            return exit_app()
        case "load":
            return load(root)
        case "process":
            return process(root, layout_value)
        case "export":
            return export(root, layout_value, file_format)
        case _:
            print("Invalid option selected")


# ======================
# Main Window
# ======================
def GUI(sw_version, loaded_layout, processed_layout, icon_path):
    """
    Launch the standalone ZIRCON GUI window.

    Parameters
    ----------
    sw_version : str
        Current software version identifier.
    loaded_layout : bool
        Initial state indicating whether a layout has been loaded.
    processed_layout : bool
        Initial state indicating whether a layout has been processed.
    icon_path : str
        Filesystem path to the application icon.

    Notes
    -----
    This function initializes the Tkinter root window and enters
    the blocking `mainloop()`.
    """

    root = tk.Tk()
    root.title("ZIRCON")
    root.geometry("420x320")
    root.resizable(True, True)

    # Icon
    try:
        icon_image = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_image)
    except Exception:
        pass

    # Header
    header_frame = tk.Frame(root, bg="#2b2b2b", height=60)
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text="ZIRCON",
        fg="white",
        bg="#2b2b2b",
        font=("Segoe UI", 18, "bold")
    ).pack(pady=15)

    # Content
    content_frame = tk.Frame(root, padx=20, pady=20)
    content_frame.pack(fill="both", expand=True)

    ttk.Button(
        content_frame,
        text="Load",
        command=lambda: on_button_click("load", root, False),
        width=22
    ).pack(pady=5)

    ttk.Button(
        content_frame,
        text="Process",
        command=lambda: on_button_click("process", root, loaded_layout),
        width=22
    ).pack(pady=5)

    ttk.Button(
        content_frame,
        text="Export Pickle",
        command=lambda: on_button_click("export", root, processed_layout, ""),
        width=22
    ).pack(pady=5)

    ttk.Button(
        content_frame,
        text="Export Excel",
        command=lambda: on_button_click("export", root, processed_layout, ".xlsx"),
        width=22
    ).pack(pady=5)

    # Footer
    footer_frame = tk.Frame(root)
    footer_frame.pack(fill="x", pady=10)

    ttk.Button(
        footer_frame,
        text="Version",
        command=lambda: open_version_window(root, sw_version),
        width=10
    ).pack(side="left", padx=20)

    ttk.Button(
        footer_frame,
        text="Help",
        command=lambda: open_help_window(root),
        width=10
    ).pack(side="right", padx=20)

    root.mainloop()
