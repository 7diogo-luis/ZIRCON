"""Add/Edit a Signal."""

from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QCheckBox,
                                QDialogButtonBox, QVBoxLayout)

from encoding_assistant.model import Signal
from encoding_assistant.validation import is_numeric, zap_pair_valid


class SignalDialog(QDialog):

    def __init__(self, parent=None, existing: Signal = None):
        super().__init__(parent)
        self.setWindowTitle('Signal')
        self._existing = existing

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.label_edit = QLineEdit()
        self.pedal_chk = QCheckBox('Equipped with pedal (emits SWP keyword)')
        self.pole_pk_edit = QLineEdit()
        self.zap_origin_edit = QLineEdit()
        self.zap_sft_fac_edit = QLineEdit()
        self.rw_chk = QCheckBox('RED + WHITE beams only (emits "*" suffix)')

        form.addRow('Label*:', self.label_edit)
        form.addRow('', self.pedal_chk)
        form.addRow('Pole PK*:', self.pole_pk_edit)
        form.addRow('ZAP origin PK:', self.zap_origin_edit)
        form.addRow('ZAP safety factor:', self.zap_sft_fac_edit)
        form.addRow('', self.rw_chk)
        layout.addLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if existing is not None:
            self.label_edit.setText(existing.label)
            self.pedal_chk.setChecked(existing.pedal)
            self.pole_pk_edit.setText(existing.pole_pk)
            self.zap_origin_edit.setText(existing.zap_origin_pk)
            self.zap_sft_fac_edit.setText(existing.zap_sft_fac)
            self.rw_chk.setChecked(existing.rw_only)

        for edit in (self.label_edit, self.pole_pk_edit,
                     self.zap_origin_edit, self.zap_sft_fac_edit):
            edit.textChanged.connect(self._update_ok_state)

        self._update_ok_state()

    def _update_ok_state(self):
        ok = (bool(self.label_edit.text().strip()) and
              is_numeric(self.pole_pk_edit.text()) and
              zap_pair_valid(self.zap_origin_edit.text(),
                             self.zap_sft_fac_edit.text()))
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(ok)

    def to_signal(self) -> Signal:
        return Signal(label=self.label_edit.text().strip(),
                      pedal=self.pedal_chk.isChecked(),
                      rw_only=self.rw_chk.isChecked(),
                      pole_pk=self.pole_pk_edit.text().strip(),
                      zap_origin_pk=self.zap_origin_edit.text().strip(),
                      zap_sft_fac=self.zap_sft_fac_edit.text().strip())
