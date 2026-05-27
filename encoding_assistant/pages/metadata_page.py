"""Metadata page: fill in the five .zad keys."""

import datetime

from PySide6.QtCore import Signal as QtSignal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit,
                                QPushButton, QHBoxLayout, QLabel)

from encoding_assistant.model import Encoding


class MetadataPage(QWidget):

    back_clicked = QtSignal()
    next_clicked = QtSignal()

    def __init__(self, encoding: Encoding, parent=None):
        super().__init__(parent)
        self._encoding = encoding

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<b>Station metadata</b> '
                                '(maps to the .zad file)'))

        form = QFormLayout()
        self.station_name = QLineEdit()
        self.station_lbl = QLineEdit()
        self.interlocking_name = QLineEdit()
        self.encoding_author = QLineEdit()
        self.date = QLineEdit(datetime.date.today().strftime('%d/%m/%Y'))
        form.addRow('Station name*:', self.station_name)
        form.addRow('Station label*:', self.station_lbl)
        form.addRow('Interlocking name*:', self.interlocking_name)
        form.addRow('Encoding author*:', self.encoding_author)
        form.addRow('Date*:', self.date)
        layout.addLayout(form)

        layout.addStretch()
        row = QHBoxLayout()
        self.back_btn = QPushButton('Back')
        self.next_btn = QPushButton('Next')
        row.addWidget(self.back_btn)
        row.addStretch()
        row.addWidget(self.next_btn)
        layout.addLayout(row)

        for edit in (self.station_name, self.station_lbl,
                     self.interlocking_name, self.encoding_author, self.date):
            edit.textChanged.connect(self._update_next_state)

        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.next_btn.clicked.connect(self._on_next)
        self._update_next_state()

    def _update_next_state(self):
        ok = all(e.text().strip() for e in (
            self.station_name, self.station_lbl, self.interlocking_name,
            self.encoding_author, self.date))
        self.next_btn.setEnabled(ok)

    def _on_next(self):
        self._encoding.metadata = {
            'station_name': self.station_name.text().strip(),
            'station_lbl': self.station_lbl.text().strip(),
            'interlocking_name': self.interlocking_name.text().strip(),
            'encoding_author': self.encoding_author.text().strip(),
            'date': self.date.text().strip(),
        }
        self.next_clicked.emit()

    def load_from_encoding(self):
        m = self._encoding.metadata
        self.station_name.setText(m.get('station_name', ''))
        self.station_lbl.setText(m.get('station_lbl', ''))
        self.interlocking_name.setText(m.get('interlocking_name', ''))
        self.encoding_author.setText(m.get('encoding_author', ''))
        if m.get('date'):
            self.date.setText(m['date'])
