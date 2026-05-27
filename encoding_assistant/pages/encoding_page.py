"""Encoding page: tree view of elements + Add/Edit/Delete/Move + Generate."""

from PySide6.QtCore import Qt, Signal as QtSignal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTreeWidget, QTreeWidgetItem, QMessageBox,
                                QLabel)

from encoding_assistant.dialogs.block_dialog import BlockDialog
from encoding_assistant.dialogs.ndz_dialog import NdzDialog
from encoding_assistant.dialogs.section_dialog import SectionDialog
from encoding_assistant.dialogs.overwrite_dialog import OverwriteDialog
from encoding_assistant.model import Block, Ndz, Section, Encoding
from encoding_assistant.validation import duplicate_labels
from encoding_assistant import io_utils


class EncodingPage(QWidget):

    back_clicked = QtSignal()
    generated = QtSignal()

    def __init__(self, encoding: Encoding, parent=None):
        super().__init__(parent)
        self._encoding = encoding

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<b>Layout encoding</b> '
                                '(elements go into .zlt + .zlg)'))

        main_row = QHBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['Type', 'Label', 'Detail'])
        self.tree.setColumnWidth(0, 140)
        self.tree.setColumnWidth(1, 140)
        main_row.addWidget(self.tree, stretch=1)

        side = QVBoxLayout()
        self.add_block_btn = QPushButton('Add Block')
        self.add_ndz_btn = QPushButton('Add NDZ')
        self.add_section_btn = QPushButton('Add Section')
        self.edit_btn = QPushButton('Edit')
        self.delete_btn = QPushButton('Delete')
        self.up_btn = QPushButton('Move Up')
        self.down_btn = QPushButton('Move Down')
        for btn in (self.add_block_btn, self.add_ndz_btn, self.add_section_btn,
                    self.edit_btn, self.delete_btn,
                    self.up_btn, self.down_btn):
            side.addWidget(btn)
        side.addStretch()
        main_row.addLayout(side)
        layout.addLayout(main_row)

        bottom = QHBoxLayout()
        self.back_btn = QPushButton('Back')
        self.generate_btn = QPushButton('Generate')
        bottom.addWidget(self.back_btn)
        bottom.addStretch()
        bottom.addWidget(self.generate_btn)
        layout.addLayout(bottom)

        self.add_block_btn.clicked.connect(self._on_add_block)
        self.add_ndz_btn.clicked.connect(self._on_add_ndz)
        self.add_section_btn.clicked.connect(self._on_add_section)
        self.edit_btn.clicked.connect(self._on_edit)
        self.delete_btn.clicked.connect(self._on_delete)
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(+1))
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.generate_btn.clicked.connect(self._on_generate)

        self.rebuild_tree()

    def rebuild_tree(self):
        self.tree.clear()
        for element in self._encoding.elements:
            if isinstance(element, Block):
                item = QTreeWidgetItem(['BLK', element.label, ''])
                item.setData(0, Qt.UserRole, element)
                self._add_signal_child(item, element.signal)
                self.tree.addTopLevelItem(item)
            elif isinstance(element, Ndz):
                item = QTreeWidgetItem(['NDZ', element.label, ''])
                item.setData(0, Qt.UserRole, element)
                self._add_signal_child(item, element.signal)
                self.tree.addTopLevelItem(item)
            elif isinstance(element, Section):
                flags = []
                if element.tjd:
                    flags.append('TJD')
                if element.ndz_flag:
                    flags.append('NDZ')
                item = QTreeWidgetItem(['SEC', element.label,
                                        ' '.join(flags)])
                item.setData(0, Qt.UserRole, element)
                sorted_nodes = sorted(element.nodes, key=lambda n: n.index)
                for node in sorted_nodes:
                    con = node.con_ele if node.con_ele.strip() else '—'
                    tjs = ' [TJS]' if node.tjs_weak else ''
                    nd_item = QTreeWidgetItem(
                        ['NDE', node.index,
                         f'→{con} @PK {node.pk}{tjs}'])
                    nd_item.setData(0, Qt.UserRole, node)
                    self._add_signal_child(nd_item, node.signal)
                    for switch in node.switches:
                        tag = ('derailer' if not switch.lr_pk.strip()
                               else 'switch')
                        sw_item = QTreeWidgetItem(
                            ['SWI', switch.label,
                             f'{tag} @PK {switch.point_pk}'])
                        sw_item.setData(0, Qt.UserRole, switch)
                        nd_item.addChild(sw_item)
                    item.addChild(nd_item)
                self.tree.addTopLevelItem(item)
        self.tree.expandAll()

    def _add_signal_child(self, parent_item, signal):
        if signal is None:
            return
        keyword = 'SWP' if signal.pedal else 'SIG'
        rw = ' *' if signal.rw_only else ''
        item = QTreeWidgetItem([keyword, f'{signal.label}{rw}',
                                f'@PK {signal.pole_pk}'])
        item.setData(0, Qt.UserRole, signal)
        parent_item.addChild(item)

    def _on_add_block(self):
        dlg = BlockDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._encoding.elements.append(dlg.to_block())
            self.rebuild_tree()

    def _on_add_ndz(self):
        dlg = NdzDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._encoding.elements.append(dlg.to_ndz())
            self.rebuild_tree()

    def _on_add_section(self):
        dlg = SectionDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._encoding.elements.append(dlg.to_section())
            self.rebuild_tree()

    def _selected_top_level_element(self):
        item = self.tree.currentItem()
        if item is None:
            return None
        # Walk to top-level item
        while item.parent() is not None:
            item = item.parent()
        return item.data(0, Qt.UserRole)

    def _on_edit(self):
        element = self._selected_top_level_element()
        if element is None:
            return
        if isinstance(element, Block):
            dlg = BlockDialog(self, existing=element)
            if dlg.exec() == dlg.DialogCode.Accepted:
                idx = self._encoding.elements.index(element)
                self._encoding.elements[idx] = dlg.to_block()
        elif isinstance(element, Ndz):
            dlg = NdzDialog(self, existing=element)
            if dlg.exec() == dlg.DialogCode.Accepted:
                idx = self._encoding.elements.index(element)
                self._encoding.elements[idx] = dlg.to_ndz()
        elif isinstance(element, Section):
            dlg = SectionDialog(self, existing=element)
            if dlg.exec() == dlg.DialogCode.Accepted:
                idx = self._encoding.elements.index(element)
                self._encoding.elements[idx] = dlg.to_section()
        self.rebuild_tree()

    def _on_delete(self):
        element = self._selected_top_level_element()
        if element is None:
            return
        confirm = QMessageBox.question(
            self, 'Delete element',
            f'Delete "{element.label}"? This cannot be undone.')
        if confirm == QMessageBox.Yes:
            self._encoding.elements.remove(element)
            self.rebuild_tree()

    def _move(self, delta):
        element = self._selected_top_level_element()
        if element is None:
            return
        elements = self._encoding.elements
        idx = elements.index(element)
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(elements):
            return
        elements[idx], elements[new_idx] = elements[new_idx], elements[idx]
        self.rebuild_tree()
        # Reselect
        self.tree.setCurrentItem(self.tree.topLevelItem(new_idx))

    def _on_generate(self):
        if not self._encoding.elements:
            QMessageBox.warning(self, 'Nothing to generate',
                                'Add at least one element before generating.')
            return

        dups = duplicate_labels(self._encoding)
        if dups:
            msg = ('The following labels appear more than once:\n\n'
                   + '\n'.join(f'  [{cat}] "{lbl}" × {n}'
                               for cat, lbl, n in dups)
                   + '\n\nGenerate anyway?')
            if QMessageBox.warning(self, 'Duplicate labels', msg,
                                   QMessageBox.Yes | QMessageBox.No
                                   ) != QMessageBox.Yes:
                return

        label = self._encoding.metadata['station_lbl']
        suffix = ''
        if io_utils.any_target_exists(label):
            existing = [p for p in io_utils.target_paths(label)
                        if __import__('os').path.exists(p)]
            suggested = io_utils.next_free_suffix(label)
            dlg = OverwriteDialog(self, existing_paths=existing,
                                  suggested_suffix=suggested)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            if dlg.choice() == OverwriteDialog.SAVE_WITH_SUFFIX:
                suffix = suggested

        try:
            written = io_utils.write_triplet(self._encoding, suffix=suffix)
        except OSError as exc:
            QMessageBox.critical(self, 'Write failed', str(exc))
            return

        QMessageBox.information(
            self, 'Generated',
            'Wrote:\n  ' + '\n  '.join(written))
        self.generated.emit()
