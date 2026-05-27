"""Start page: choose 'Encode new station' or 'Edit encoded station' (stub)."""

from PySide6.QtCore import Qt, Signal as QtSignal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                                QHBoxLayout)


class StartPage(QWidget):

    encode_new_clicked = QtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.addStretch()

        title = QLabel('ZIRCON Encoding Assistant')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 22pt; font-weight: bold;')
        outer.addWidget(title)
        outer.addSpacing(40)

        row = QHBoxLayout()
        row.addStretch()
        self.encode_btn = QPushButton('Encode new station')
        self.encode_btn.setMinimumHeight(60)
        self.encode_btn.setMinimumWidth(220)
        self.edit_btn = QPushButton('Edit encoded station')
        self.edit_btn.setMinimumHeight(60)
        self.edit_btn.setMinimumWidth(220)
        self.edit_btn.setEnabled(False)
        self.edit_btn.setToolTip('Coming in v2')
        row.addWidget(self.encode_btn)
        row.addSpacing(20)
        row.addWidget(self.edit_btn)
        row.addStretch()
        outer.addLayout(row)
        outer.addStretch()

        self.encode_btn.clicked.connect(self.encode_new_clicked.emit)
