"""Add/Edit a Switch (or derailer)."""

from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit,
                                QDialogButtonBox, QVBoxLayout, QLabel)

from encoding_assistant.model import Switch
from encoding_assistant.validation import is_numeric, is_optional_numeric


class SwitchDialog(QDialog):

    def __init__(self, parent=None, existing: Switch = None):
        super().__init__(parent)
        self.setWindowTitle('Switch / Derailer')

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.label_edit = QLineEdit()
        self.point_pk_edit = QLineEdit()
        self.lr_pk_edit = QLineEdit()

        form.addRow('Label*:', self.label_edit)
        form.addRow('Point PK*:', self.point_pk_edit)
        form.addRow('Fouling PK:', self.lr_pk_edit)
        layout.addLayout(form)
        layout.addWidget(QLabel('(Leave Fouling PK empty for derailer; '
                                'include "C" in label per DSL convention.)'))

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if existing is not None:
            self.label_edit.setText(existing.label)
            self.point_pk_edit.setText(existing.point_pk)
            self.lr_pk_edit.setText(existing.lr_pk)

        for edit in (self.label_edit, self.point_pk_edit, self.lr_pk_edit):
            edit.textChanged.connect(self._update_ok_state)

        self._update_ok_state()

    def _update_ok_state(self):
        ok = (bool(self.label_edit.text().strip()) and
              is_numeric(self.point_pk_edit.text()) and
              is_optional_numeric(self.lr_pk_edit.text()))
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(ok)

    def to_switch(self) -> Switch:
        return Switch(label=self.label_edit.text().strip(),
                      point_pk=self.point_pk_edit.text().strip(),
                      lr_pk=self.lr_pk_edit.text().strip())
