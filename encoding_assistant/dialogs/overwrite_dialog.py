"""Overwrite-conflict dialog: Overwrite / Save-with-suffix / Cancel."""

from PySide6.QtWidgets import (QDialog, QLabel, QDialogButtonBox,
                                QVBoxLayout, QPushButton)


class OverwriteDialog(QDialog):

    OVERWRITE = 1
    SAVE_WITH_SUFFIX = 2

    def __init__(self, parent=None, existing_paths=None, suggested_suffix=''):
        super().__init__(parent)
        self.setWindowTitle('Files already exist')
        self._choice = None

        layout = QVBoxLayout(self)
        msg = ('The following file(s) already exist in stations/input/:\n  '
               + '\n  '.join(existing_paths or [])
               + f'\n\nChoose how to proceed. '
               f'Save-with-suffix would use "{suggested_suffix}".')
        layout.addWidget(QLabel(msg))

        box = QDialogButtonBox()
        overwrite_btn = QPushButton('Overwrite')
        save_btn = QPushButton(f'Save with suffix {suggested_suffix}')
        cancel_btn = QPushButton('Cancel')
        box.addButton(overwrite_btn, QDialogButtonBox.AcceptRole)
        box.addButton(save_btn, QDialogButtonBox.AcceptRole)
        box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        layout.addWidget(box)

        overwrite_btn.clicked.connect(self._on_overwrite)
        save_btn.clicked.connect(self._on_save_with_suffix)
        cancel_btn.clicked.connect(self.reject)

    def _on_overwrite(self):
        self._choice = self.OVERWRITE
        self.accept()

    def _on_save_with_suffix(self):
        self._choice = self.SAVE_WITH_SUFFIX
        self.accept()

    def choice(self):
        return self._choice
