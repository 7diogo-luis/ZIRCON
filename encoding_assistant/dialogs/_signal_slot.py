"""Reusable signal-slot widget: shows current signal or 'no signal', with
Add/Edit and Remove buttons."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from encoding_assistant.dialogs.signal_dialog import SignalDialog
from encoding_assistant.model import Signal


class SignalSlot(QWidget):

    def __init__(self, parent=None, signal: Signal = None):
        super().__init__(parent)
        self._signal = signal

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.edit_btn = QPushButton('Add signal')
        self.remove_btn = QPushButton('Remove')
        layout.addWidget(self.label, stretch=1)
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.remove_btn)

        self.edit_btn.clicked.connect(self._on_edit)
        self.remove_btn.clicked.connect(self._on_remove)
        self._refresh()

    def signal(self) -> Signal:
        return self._signal

    def _on_edit(self):
        dlg = SignalDialog(self, existing=self._signal)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._signal = dlg.to_signal()
            self._refresh()

    def _on_remove(self):
        self._signal = None
        self._refresh()

    def _refresh(self):
        if self._signal is None:
            self.label.setText('No signal')
            self.edit_btn.setText('Add signal')
            self.remove_btn.setEnabled(False)
        else:
            keyword = 'SWP' if self._signal.pedal else 'SIG'
            rw = ' *' if self._signal.rw_only else ''
            self.label.setText(f'{keyword} {self._signal.label}{rw}  '
                               f'@PK {self._signal.pole_pk}')
            self.edit_btn.setText('Edit signal')
            self.remove_btn.setEnabled(True)
