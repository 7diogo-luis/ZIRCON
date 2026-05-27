"""Add/Edit a Node within a Section."""

from copy import deepcopy

from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox,
                                QCheckBox, QDialogButtonBox, QVBoxLayout,
                                QListWidget, QListWidgetItem, QPushButton,
                                QHBoxLayout, QLabel, QWidget)
from PySide6.QtCore import Qt

from encoding_assistant.dialogs._signal_slot import SignalSlot
from encoding_assistant.dialogs.switch_dialog import SwitchDialog
from encoding_assistant.model import Node, Section, next_free_node_index
from encoding_assistant.validation import is_numeric


class NodeDialog(QDialog):

    def __init__(self, parent=None, section: Section = None,
                 existing: Node = None):
        super().__init__(parent)
        self.setWindowTitle('Node')
        self._section = section
        self._existing = existing
        self._switches = (deepcopy(existing.switches)
                          if existing is not None else [])

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.index_combo = QComboBox()
        used = {n.index for n in section.nodes if n is not existing}
        free_letters = [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        if c not in used]
        for letter in free_letters:
            self.index_combo.addItem(letter)
        if existing is not None:
            self.index_combo.insertItem(0, existing.index)
            self.index_combo.setCurrentIndex(0)
        elif free_letters:
            self.index_combo.setCurrentText(next_free_node_index(section)
                                            if section else 'A')

        self.con_ele_edit = QLineEdit()
        self.pk_edit = QLineEdit()
        self.tjs_chk = QCheckBox('TJS weak node (emits "-" suffix)')

        form.addRow('Index*:', self.index_combo)
        form.addRow('Connected element:', self.con_ele_edit)
        form.addRow('Node PK*:', self.pk_edit)
        form.addRow('', self.tjs_chk)

        existing_signal = existing.signal if existing is not None else None
        self.signal_slot = SignalSlot(self, signal=existing_signal)
        form.addRow('Signal:', self.signal_slot)
        layout.addLayout(form)

        layout.addWidget(QLabel('Switches / Derailers:'))
        self.switch_list = QListWidget()
        layout.addWidget(self.switch_list)
        sw_btn_row = QHBoxLayout()
        self.add_sw_btn = QPushButton('Add')
        self.edit_sw_btn = QPushButton('Edit')
        self.del_sw_btn = QPushButton('Delete')
        sw_btn_row.addWidget(self.add_sw_btn)
        sw_btn_row.addWidget(self.edit_sw_btn)
        sw_btn_row.addWidget(self.del_sw_btn)
        sw_btn_row.addStretch()
        layout.addLayout(sw_btn_row)

        self.add_sw_btn.clicked.connect(self._on_add_switch)
        self.edit_sw_btn.clicked.connect(self._on_edit_switch)
        self.del_sw_btn.clicked.connect(self._on_delete_switch)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if existing is not None:
            self.con_ele_edit.setText(existing.con_ele)
            self.pk_edit.setText(existing.pk)
            self.tjs_chk.setChecked(existing.tjs_weak)

        self._rebuild_switch_list()
        self.pk_edit.textChanged.connect(self._update_ok_state)
        self.index_combo.currentTextChanged.connect(self._update_ok_state)
        self._update_ok_state()

    def _rebuild_switch_list(self):
        self.switch_list.clear()
        for sw in self._switches:
            tag = 'derailer' if not sw.lr_pk.strip() else 'switch'
            QListWidgetItem(f'{sw.label}  ({tag}, point PK {sw.point_pk})',
                            self.switch_list)

    def _on_add_switch(self):
        dlg = SwitchDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._switches.append(dlg.to_switch())
            self._rebuild_switch_list()

    def _on_edit_switch(self):
        idx = self.switch_list.currentRow()
        if idx < 0:
            return
        dlg = SwitchDialog(self, existing=self._switches[idx])
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._switches[idx] = dlg.to_switch()
            self._rebuild_switch_list()

    def _on_delete_switch(self):
        idx = self.switch_list.currentRow()
        if idx < 0:
            return
        self._switches.pop(idx)
        self._rebuild_switch_list()

    def _update_ok_state(self):
        ok = (bool(self.index_combo.currentText()) and
              is_numeric(self.pk_edit.text()))
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(ok)

    def to_node(self) -> Node:
        return Node(index=self.index_combo.currentText(),
                    con_ele=self.con_ele_edit.text().strip(),
                    pk=self.pk_edit.text().strip(),
                    tjs_weak=self.tjs_chk.isChecked(),
                    signal=self.signal_slot.signal(),
                    switches=self._switches)
