from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy


class Card(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None, accent: bool = False):
        super().__init__()
        self.setObjectName('AccentPanel' if accent else 'Panel')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(10)
        if title:
            title_label = QLabel(title)
            title_label.setObjectName('SectionTitle')
            self.layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName('Muted')
            subtitle_label.setWordWrap(True)
            self.layout.addWidget(subtitle_label)
