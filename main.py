import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blackbox_editor import BlackBoxEditor
from unequal_editor import UnequalEditor


class PuzzleWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Puzzle Studio")
        self.resize(1080, 860)

        title = QLabel("Puzzle Studio")
        title.setObjectName("title")
        title.setFont(QFont("Georgia", 24, 600))

        subtitle = QLabel(
            "Switch between puzzle families and use the dedicated editor for each board type."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.puzzle_type_combo = QComboBox()
        self.puzzle_type_combo.addItems(["Black Box", "Unequal"])

        selector_row = QHBoxLayout()
        selector_row.setSpacing(14)
        selector_row.addWidget(
            self.make_labeled_field("Puzzle type", self.puzzle_type_combo)
        )
        selector_row.addStretch(1)

        self.stack = QStackedWidget()
        self.blackbox_editor = BlackBoxEditor()
        self.unequal_editor = UnequalEditor()
        self.stack.addWidget(self.blackbox_editor)
        self.stack.addWidget(self.unequal_editor)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setWidget(self.stack)

        self.puzzle_type_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(selector_row)
        layout.addWidget(self.scroll_area, 1)

        self.setStyleSheet(self.stylesheet())

    def make_labeled_field(self, label_text: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def stylesheet(self) -> str:
        return """
        QWidget {
            background: #efe2cf;
            color: #2d241b;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 14px;
        }
        QLabel#title {
            color: #38281a;
        }
        QLabel#subtitle, QLabel#status, QLabel#fieldLabel {
            color: #5f4f41;
        }
        QLabel#summary {
            color: #725f4b;
            background: #f6ead9;
            border: 1px solid #d1b798;
            border-radius: 10px;
            padding: 8px 12px;
        }
        QFrame#boardFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e5d4bd, stop:1 #dcc7ad);
            border: 1px solid #b79d7d;
            border-radius: 20px;
        }
        QSpinBox, QPushButton, QComboBox, QLineEdit {
            min-height: 36px;
            border-radius: 10px;
            border: 1px solid #9d8160;
            background: #f8efe4;
            selection-background-color: #cda96b;
            selection-color: #241a12;
            color: #241a12;
            padding: 4px 10px;
        }
        QPushButton:hover, QComboBox:hover, QLineEdit:hover {
            background: #f4e2cc;
        }
        QPushButton:pressed {
            background: #ebd1af;
        }
        QPushButton#edgeButton {
            min-width: 48px;
            min-height: 48px;
            font-weight: 700;
            background: #f5e7d4;
        }
        QPushButton#edgeButton[filled="true"] {
            background: #dbc19d;
            color: #241a12;
        }
        QLabel#cell {
            min-width: 52px;
            min-height: 52px;
            border-radius: 8px;
            background: #676767;
            border: 1px solid #8d8d8d;
            color: #fff4e7;
            font-size: 18px;
            font-weight: 700;
        }
        QLabel#cell[ball="true"] {
            background: #b24d36;
            border: 1px solid #d98f76;
        }
        QLineEdit#digitCell {
            min-width: 54px;
            min-height: 54px;
            border-radius: 4px;
            background: #d9d9d9;
            border: 1px solid #9f9f9f;
            font-size: 24px;
            font-weight: 600;
            padding: 0;
        }
        QPushButton#relationButton {
            min-width: 30px;
            min-height: 30px;
            background: transparent;
            border: none;
            border-radius: 0;
            font-size: 28px;
            font-weight: 700;
            padding: 0;
            color: #4e4640;
        }
        QPushButton#relationButton[axis="horizontal"] {
            min-width: 30px;
        }
        QPushButton#relationButton[axis="vertical"] {
            min-height: 30px;
        }
        QPushButton#relationButton[active="true"] {
            color: #16120d;
        }
        QPushButton#relationButton:hover {
            background: #e6d4bf;
            border-radius: 6px;
        }
        """


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PuzzleWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
