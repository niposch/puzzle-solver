from __future__ import annotations

import json
import sys
from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from solver import EdgePosition, Solution, format_ball_positions, solve_from_clues


class EdgeButton(QPushButton):
    def __init__(self, edge: EdgePosition, owner: "BlackBoxWindow") -> None:
        super().__init__("")
        self.edge = edge
        self.owner = owner

    def mousePressEvent(self, e: QMouseEvent | None) -> None:
        if e is None:
            return
        if e.button() == Qt.MouseButton.RightButton:
            self.owner.cycle_edge_value(self.edge, -1)
            e.accept()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.owner.cycle_edge_value(self.edge, 1)
            e.accept()
            return
        super().mousePressEvent(e)


class BlackBoxWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.clues: dict[EdgePosition, str] = {}
        self.edge_buttons: dict[EdgePosition, QPushButton] = {}
        self.cell_labels: dict[tuple[int, int], QLabel] = {}
        self.solution: Solution | None = None

        self.setWindowTitle("Black Box Solver")
        self.resize(940, 780)

        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(3, 10)
        self.grid_size_spin.setValue(5)
        self.grid_size_spin.valueChanged.connect(self.on_grid_size_changed)

        self.ball_count_spin = QSpinBox()
        self.ball_count_spin.setRange(0, 25)
        self.ball_count_spin.setValue(4)

        self.solve_button = QPushButton("Solve")
        self.solve_button.clicked.connect(self.solve)

        self.clear_button = QPushButton("Clear clues")
        self.clear_button.clicked.connect(self.clear_clues)

        self.save_button = QPushButton("Save clues")
        self.save_button.clicked.connect(self.save_clues)

        self.load_button = QPushButton("Load clues")
        self.load_button.clicked.connect(self.load_clues)

        title = QLabel("Black Box Puzzle")
        title.setObjectName("title")
        title.setFont(QFont("Georgia", 22, 600))

        subtitle = QLabel(
            "Click the perimeter to cycle through blank, H, R, and paired numbers. Right-click an edge to step backward."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")

        self.clue_summary_label = QLabel()
        self.clue_summary_label.setObjectName("summary")
        self.clue_summary_label.setWordWrap(True)

        controls = QHBoxLayout()
        controls.setSpacing(14)
        controls.addWidget(self.make_labeled_field("Grid", self.grid_size_spin))
        controls.addWidget(self.make_labeled_field("Balls", self.ball_count_spin))
        controls.addStretch(1)
        controls.addWidget(self.load_button)
        controls.addWidget(self.save_button)
        controls.addWidget(self.clear_button)
        controls.addWidget(self.solve_button)

        self.board_frame = QFrame()
        self.board_frame.setObjectName("boardFrame")
        self.board_layout = QVBoxLayout(self.board_frame)
        self.board_layout.setContentsMargins(22, 22, 22, 22)

        self.status_label = QLabel("Set the side clues, then solve for a ball layout.")
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.clue_summary_label)
        layout.addLayout(controls)
        layout.addWidget(self.board_frame, 1)
        layout.addWidget(self.status_label)

        self.setStyleSheet(self.stylesheet())
        self.on_grid_size_changed(self.grid_size_spin.value())

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
        QSpinBox, QPushButton {
            min-height: 36px;
            border-radius: 10px;
            border: 1px solid #9d8160;
            background: #f8efe4;
            selection-background-color: #cda96b;
            selection-color: #241a12;
            padding: 4px 10px;
        }
        QSpinBox {
            color: #241a12;
        }
        QPushButton:hover {
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
        """

    def on_grid_size_changed(self, grid_size: int) -> None:
        self.ball_count_spin.setMaximum(grid_size * grid_size)
        if self.ball_count_spin.value() > self.ball_count_spin.maximum():
            self.ball_count_spin.setValue(self.ball_count_spin.maximum())
        self.clues.clear()
        self.solution = None
        self.rebuild_board()
        self.status_label.setText("Board resized. Add new side clues for this puzzle.")
        self.update_clue_summary()

    def clear_clues(self) -> None:
        self.clues.clear()
        self.solution = None
        self.refresh_edge_buttons()
        self.refresh_cells()
        self.update_clue_summary()
        self.status_label.setText("Clues cleared.")

    def rebuild_board(self) -> None:
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        grid_size = self.grid_size_spin.value()
        board = QWidget()
        layout = QGridLayout(board)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.edge_buttons.clear()
        self.cell_labels.clear()

        for col in range(grid_size):
            self.add_edge_button(layout, EdgePosition("N", col), 0, col + 1)
            self.add_edge_button(layout, EdgePosition("S", col), grid_size + 1, col + 1)

        for row in range(grid_size):
            self.add_edge_button(layout, EdgePosition("W", row), row + 1, 0)
            self.add_edge_button(layout, EdgePosition("E", row), row + 1, grid_size + 1)

        for row in range(grid_size):
            for col in range(grid_size):
                cell = QLabel("")
                cell.setObjectName("cell")
                cell.setProperty("ball", False)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                layout.addWidget(cell, row + 1, col + 1)
                self.cell_labels[(row, col)] = cell

        for index in range(grid_size + 2):
            layout.setColumnStretch(index, 1)
            layout.setRowStretch(index, 1)

        self.board_layout.addWidget(board)
        self.refresh_edge_buttons()
        self.refresh_cells()

    def add_edge_button(
        self, layout: QGridLayout, edge: EdgePosition, row: int, col: int
    ) -> None:
        button = EdgeButton(edge, self)
        button.setObjectName("edgeButton")
        button.setToolTip("Left click: next clue. Right click: previous clue.")
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(button, row, col)
        self.edge_buttons[edge] = button

    def cycle_edge_value(self, edge: EdgePosition, step: int) -> None:
        current = self.clues.get(edge, "")
        next_value = self.next_clue_value(edge, current, step)
        if next_value:
            self.clues[edge] = next_value
        else:
            self.clues.pop(edge, None)
        self.solution = None
        self.refresh_edge_buttons()
        self.refresh_cells()
        self.update_clue_summary()

    def next_clue_value(self, edge: EdgePosition, current: str, step: int) -> str:
        counts = Counter(
            clue
            for clue_edge, clue in self.clues.items()
            if clue_edge != edge and clue.isdigit()
        )
        max_number = max(1, (self.grid_size_spin.value() * 4) // 2)
        available_numbers = [
            str(number)
            for number in range(1, max_number + 1)
            if counts[str(number)] < 2
        ]
        sequence = ["", "H", "R", *available_numbers]
        index = sequence.index(current) if current in sequence else 0
        return sequence[(index + step) % len(sequence)]

    def update_clue_summary(self) -> None:
        numbered = Counter(clue for clue in self.clues.values() if clue.isdigit())
        incomplete = sorted(value for value, count in numbered.items() if count != 2)
        paired = sum(1 for count in numbered.values() if count == 2)
        summary = f"{len(self.clues)} clues set"
        if numbered:
            summary += f" | {paired} numbered pairs complete"
        else:
            summary += " | no numbered pairs yet"
        if incomplete:
            summary += " | waiting on: " + ", ".join(incomplete)
        self.clue_summary_label.setText(summary)

    def serialize_clues(self) -> dict[str, object]:
        return {
            "grid_size": self.grid_size_spin.value(),
            "ball_count": self.ball_count_spin.value(),
            "clues": [
                {"side": edge.side, "index": edge.index, "value": value}
                for edge, value in sorted(
                    self.clues.items(), key=lambda item: (item[0].side, item[0].index)
                )
            ],
        }

    def save_clues(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save clues",
            "blackbox-clues.json",
            "JSON files (*.json)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(self.serialize_clues(), handle, indent=2)
        except OSError as exc:
            self.status_label.setText(f"Could not save clues: {exc}")
            return

        self.status_label.setText(f"Saved clues to {file_path}.")

    def load_clues(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load clues",
            "",
            "JSON files (*.json)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            grid_size = int(payload["grid_size"])
            ball_count = int(payload["ball_count"])
            loaded_clues = {
                EdgePosition(str(item["side"]), int(item["index"])): str(item["value"])
                for item in payload["clues"]
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
            self.status_label.setText(f"Could not load clues: {exc}")
            return

        self.grid_size_spin.setValue(grid_size)
        self.ball_count_spin.setValue(ball_count)
        self.clues = loaded_clues
        self.solution = None
        self.refresh_edge_buttons()
        self.refresh_cells()
        self.update_clue_summary()
        self.status_label.setText(f"Loaded clues from {file_path}.")

    def refresh_edge_buttons(self) -> None:
        for edge, button in self.edge_buttons.items():
            value = self.clues.get(edge, "")
            button.setText(value)
            button.setProperty("filled", bool(value))
            style = button.style()
            if style is not None:
                style.unpolish(button)
                style.polish(button)

    def refresh_cells(self) -> None:
        ball_positions = set(self.solution.ball_positions) if self.solution else set()
        for position, label in self.cell_labels.items():
            label.setText("O" if position in ball_positions else "")
            label.setProperty("ball", position in ball_positions)
            style = label.style()
            if style is not None:
                style.unpolish(label)
                style.polish(label)

    def solve(self) -> None:
        try:
            solution = solve_from_clues(
                grid_size=self.grid_size_spin.value(),
                ball_count=self.ball_count_spin.value(),
                clues=dict(self.clues),
            )
        except ValueError as exc:
            self.solution = None
            self.refresh_cells()
            self.status_label.setText(str(exc))
            return

        if solution is None:
            self.solution = None
            self.refresh_cells()
            self.status_label.setText(
                "No solution fits the current clues and ball count."
            )
            return

        self.solution = solution
        self.refresh_cells()
        self.status_label.setText(
            f"Solution found. Balls: {format_ball_positions(solution)}"
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = BlackBoxWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
