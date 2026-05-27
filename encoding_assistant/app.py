"""MainWindow + QApplication wiring for the ZIRCON Encoding Assistant."""

import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QStackedWidget,
                                QMessageBox)

from encoding_assistant.model import Encoding
from encoding_assistant.pages.start_page import StartPage
from encoding_assistant.pages.metadata_page import MetadataPage
from encoding_assistant.pages.encoding_page import EncodingPage


class MainWindow(QMainWindow):

    PAGE_START = 0
    PAGE_METADATA = 1
    PAGE_ENCODING = 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle('ZIRCON Encoding Assistant')
        self.resize(900, 600)

        self._encoding = Encoding()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.start_page = StartPage()
        self.metadata_page = MetadataPage(self._encoding)
        self.encoding_page = EncodingPage(self._encoding)

        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.metadata_page)
        self.stack.addWidget(self.encoding_page)

        self.start_page.encode_new_clicked.connect(self._on_encode_new)
        self.metadata_page.back_clicked.connect(self._on_metadata_back)
        self.metadata_page.next_clicked.connect(self._on_metadata_next)
        self.encoding_page.back_clicked.connect(self._on_encoding_back)
        self.encoding_page.exit_clicked.connect(self._on_encoding_exit)

    def _on_encode_new(self):
        self._encoding.metadata = {
            'station_name': '', 'station_lbl': '',
            'interlocking_name': '', 'encoding_author': '', 'date': '',
        }
        self._encoding.elements.clear()
        self.metadata_page.load_from_encoding()
        self.encoding_page.rebuild_tree()
        self._update_title()
        self.stack.setCurrentIndex(self.PAGE_METADATA)

    def _on_metadata_back(self):
        if self._encoding.elements:
            confirm = QMessageBox.question(
                self, 'Discard encoding?',
                'Going back to the start discards the current encoding. '
                'Continue?')
            if confirm != QMessageBox.Yes:
                return
        self._encoding.elements.clear()
        self.stack.setCurrentIndex(self.PAGE_START)

    def _on_metadata_next(self):
        self._update_title()
        self.stack.setCurrentIndex(self.PAGE_ENCODING)

    def _on_encoding_back(self):
        self.stack.setCurrentIndex(self.PAGE_METADATA)

    def _on_encoding_exit(self):
        self._encoding.elements.clear()
        self.stack.setCurrentIndex(self.PAGE_START)

    def _update_title(self):
        lbl = self._encoding.metadata.get('station_lbl', '')
        if lbl:
            self.setWindowTitle(f'ZIRCON Encoding Assistant — {lbl}')
        else:
            self.setWindowTitle('ZIRCON Encoding Assistant')


def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
