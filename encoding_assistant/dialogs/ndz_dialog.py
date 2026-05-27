"""Add/Edit an NDZ (undetected section, singularly connected)."""

from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit,
                                QDialogButtonBox, QVBoxLayout)

from encoding_assistant.dialogs._signal_slot import SignalSlot
from encoding_assistant.model import Ndz


class NdzDialog(QDialog):

    def __init__(self, parent=None, existing: Ndz = None):
        super().__init__(parent)
        self.setWindowTitle('Undetected section (NDZ)')

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.label_edit = QLineEdit()
        form.addRow('Label*:', self.label_edit)

        existing_signal = existing.signal if existing is not None else None
        self.signal_slot = SignalSlot(self, signal=existing_signal)
        form.addRow('Signal:', self.signal_slot)
        layout.addLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if existing is not None:
            self.label_edit.setText(existing.label)

        self.label_edit.textChanged.connect(self._update_ok_state)
        self._update_ok_state()

    def _update_ok_state(self):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.label_edit.text().strip()))

    def to_ndz(self) -> Ndz:
        return Ndz(label=self.label_edit.text().strip(),
                   signal=self.signal_slot.signal())
