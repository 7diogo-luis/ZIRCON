"""Add/Edit a Section, including its nodes."""

from copy import deepcopy

from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QCheckBox,
                                QDialogButtonBox, QVBoxLayout, QListWidget,
                                QListWidgetItem, QPushButton, QHBoxLayout,
                                QLabel)

from encoding_assistant.dialogs.node_dialog import NodeDialog
from encoding_assistant.model import Section
from encoding_assistant.validation import section_odd_no_switch


class SectionDialog(QDialog):

    def __init__(self, parent=None, existing: Section = None):
        super().__init__(parent)
        self.setWindowTitle('Section')
        self._working = (deepcopy(existing) if existing is not None
                         else Section())

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.label_edit = QLineEdit(self._working.label)
        self.tjd_chk = QCheckBox('TJD (double-junction switch)')
        self.tjd_chk.setChecked(self._working.tjd)
        self.ndz_chk = QCheckBox('Without train detection (NDZ flag)')
        self.ndz_chk.setChecked(self._working.ndz_flag)

        form.addRow('Label*:', self.label_edit)
        form.addRow('', self.tjd_chk)
        form.addRow('', self.ndz_chk)
        layout.addLayout(form)

        layout.addWidget(QLabel('Nodes:'))
        self.node_list = QListWidget()
        layout.addWidget(self.node_list)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton('Add node')
        self.edit_btn = QPushButton('Edit node')
        self.del_btn = QPushButton('Delete node')
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self._on_add_node)
        self.edit_btn.clicked.connect(self._on_edit_node)
        self.del_btn.clicked.connect(self._on_delete_node)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet('color: #b00020; font-weight: bold;')
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                           QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._rebuild_node_list()
        self.label_edit.textChanged.connect(self._update_ok_state)
        self._update_ok_state()

    def _rebuild_node_list(self):
        self.node_list.clear()
        sorted_nodes = sorted(self._working.nodes, key=lambda n: n.index)
        for node in sorted_nodes:
            con = node.con_ele if node.con_ele.strip() else '(no con_ele)'
            tjs = ' [TJS weak]' if node.tjs_weak else ''
            QListWidgetItem(f'NDE {node.index} → {con}  '
                            f'@PK {node.pk}{tjs}', self.node_list)
        self._update_warning_label()

    def _update_warning_label(self):
        if section_odd_no_switch(self._working):
            self.warning_label.setText(
                '⚠ Section has an odd number of nodes (≥ 3) and no switch. '
                'Real-track sections with an odd node count require at least '
                'one switch (derailers do not count). Likely encoding mistake.')
            self.warning_label.setVisible(True)
        else:
            self.warning_label.setVisible(False)

    def _on_add_node(self):
        dlg = NodeDialog(self, section=self._working, existing=None)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._working.nodes.append(dlg.to_node())
            self._rebuild_node_list()

    def _on_edit_node(self):
        idx = self.node_list.currentRow()
        if idx < 0:
            return
        sorted_nodes = sorted(self._working.nodes, key=lambda n: n.index)
        target = sorted_nodes[idx]
        dlg = NodeDialog(self, section=self._working, existing=target)
        if dlg.exec() == dlg.DialogCode.Accepted:
            real_idx = self._working.nodes.index(target)
            self._working.nodes[real_idx] = dlg.to_node()
            self._rebuild_node_list()

    def _on_delete_node(self):
        idx = self.node_list.currentRow()
        if idx < 0:
            return
        sorted_nodes = sorted(self._working.nodes, key=lambda n: n.index)
        target = sorted_nodes[idx]
        self._working.nodes.remove(target)
        self._rebuild_node_list()

    def _update_ok_state(self):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.label_edit.text().strip()))

    def to_section(self) -> Section:
        return Section(label=self.label_edit.text().strip(),
                       tjd=self.tjd_chk.isChecked(),
                       ndz_flag=self.ndz_chk.isChecked(),
                       nodes=self._working.nodes)
