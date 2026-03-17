from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class UnequalPuzzleState:
    grid_size: int = 6
    variant: str = "Unequal"
    givens: dict[tuple[int, int], int] = field(default_factory=dict)
    horizontal_relations: dict[tuple[int, int], str] = field(default_factory=dict)
    vertical_relations: dict[tuple[int, int], str] = field(default_factory=dict)


class RelationButton(QPushButton):
    def __init__(
        self,
        owner: "UnequalEditor",
        axis: str,
        position: tuple[int, int],
    ) -> None:
        super().__init__("")
        self.owner = owner
        self.axis = axis
        self.position = position
        self.setObjectName("relationButton")
        self.setProperty("axis", axis)

    def mousePressEvent(self, e: QMouseEvent | None) -> None:
        if e is None:
            return
        if e.button() == Qt.MouseButton.RightButton:
            self.owner.cycle_relation(self.axis, self.position, -1)
            e.accept()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.owner.cycle_relation(self.axis, self.position, 1)
            e.accept()
            return
        super().mousePressEvent(e)


class DigitCell(QLineEdit):
    def __init__(
        self,
        owner: "UnequalEditor",
        position: tuple[int, int],
    ) -> None:
        super().__init__()
        self.owner = owner
        self.position = position
        self.setObjectName("digitCell")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.textChanged.connect(self.on_text_changed)

    def on_text_changed(self, text: str) -> None:
        cleaned = "".join(ch for ch in text if ch.isdigit())
        if cleaned != text:
            cursor = self.cursorPosition()
            self.blockSignals(True)
            self.setText(cleaned)
            self.setCursorPosition(min(cursor - 1, len(cleaned)))
            self.blockSignals(False)
            text = cleaned
        self.owner.update_given(self.position, text)


class UnequalEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = UnequalPuzzleState()
        self.given_inputs: dict[tuple[int, int], DigitCell] = {}
        self.horizontal_buttons: dict[tuple[int, int], RelationButton] = {}
        self.vertical_buttons: dict[tuple[int, int], RelationButton] = {}

        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(3, 9)
        self.grid_size_spin.setValue(self.state.grid_size)
        self.grid_size_spin.valueChanged.connect(self.on_grid_size_changed)

        self.variant_combo = QComboBox()
        self.variant_combo.addItems(["Unequal", "Adjacent"])
        self.variant_combo.currentTextChanged.connect(self.on_variant_changed)

        self.clear_button = QPushButton("Clear grid")
        self.clear_button.clicked.connect(self.clear_puzzle)

        self.solve_button = QPushButton("Solve")
        self.solve_button.clicked.connect(self.solve)

        intro = QLabel(
            "Enter givens in the Latin square. Click between cells to toggle relation hints for either Unequal or Adjacent mode."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary")
        self.summary_label.setWordWrap(True)

        controls = QHBoxLayout()
        controls.setSpacing(14)
        controls.addWidget(self.make_labeled_field("Grid", self.grid_size_spin))
        controls.addWidget(self.make_labeled_field("Hint mode", self.variant_combo))
        controls.addStretch(1)
        controls.addWidget(self.clear_button)
        controls.addWidget(self.solve_button)

        self.board_frame = QFrame()
        self.board_frame.setObjectName("boardFrame")
        self.board_layout = QVBoxLayout(self.board_frame)
        self.board_layout.setContentsMargins(22, 22, 22, 22)

        self.status_label = QLabel(
            "Build an Unequal or Adjacent puzzle; solving is not wired up yet."
        )
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(intro)
        layout.addWidget(self.summary_label)
        layout.addLayout(controls)
        layout.addWidget(self.board_frame, 1)
        layout.addWidget(self.status_label)

        self.rebuild_board()
        self.update_summary()

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

    def on_grid_size_changed(self, grid_size: int) -> None:
        self.state = UnequalPuzzleState(grid_size=grid_size, variant=self.state.variant)
        self.rebuild_board()
        self.update_summary()
        self.status_label.setText("Grid resized. Enter givens and relation hints.")

    def on_variant_changed(self, variant: str) -> None:
        self.state.variant = variant
        self.state.horizontal_relations.clear()
        self.state.vertical_relations.clear()
        self.refresh_relation_buttons()
        self.update_summary()
        self.status_label.setText(f"Hint mode switched to {variant}.")

    def clear_puzzle(self) -> None:
        self.state = UnequalPuzzleState(
            grid_size=self.grid_size_spin.value(),
            variant=self.variant_combo.currentText(),
        )
        self.refresh_digit_inputs()
        self.refresh_relation_buttons()
        self.update_summary()
        self.status_label.setText("Unequal grid cleared.")

    def rebuild_board(self) -> None:
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        board = QWidget()
        layout = QGridLayout(board)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        grid_size = self.state.grid_size
        self.given_inputs.clear()
        self.horizontal_buttons.clear()
        self.vertical_buttons.clear()

        for row in range(grid_size):
            for col in range(grid_size):
                cell = DigitCell(self, (row, col))
                cell.setText(
                    str(self.state.givens[(row, col)])
                    if (row, col) in self.state.givens
                    else ""
                )
                layout.addWidget(cell, row * 2, col * 2)
                self.given_inputs[(row, col)] = cell

                if col < grid_size - 1:
                    button = RelationButton(self, "horizontal", (row, col))
                    layout.addWidget(button, row * 2, col * 2 + 1)
                    self.horizontal_buttons[(row, col)] = button

                if row < grid_size - 1:
                    button = RelationButton(self, "vertical", (row, col))
                    layout.addWidget(button, row * 2 + 1, col * 2)
                    self.vertical_buttons[(row, col)] = button

        for index in range(grid_size * 2 - 1):
            stretch = 4 if index % 2 == 0 else 1
            layout.setColumnStretch(index, stretch)
            layout.setRowStretch(index, stretch)

        self.board_layout.addWidget(board)
        self.refresh_digit_inputs()
        self.refresh_relation_buttons()

    def relation_sequence(self, axis: str) -> list[str]:
        if self.state.variant == "Adjacent":
            return ["", "|" if axis == "horizontal" else "-"]
        if axis == "horizontal":
            return ["", "<", ">"]
        return ["", "^", "v"]

    def cycle_relation(self, axis: str, position: tuple[int, int], step: int) -> None:
        mapping = (
            self.state.horizontal_relations
            if axis == "horizontal"
            else self.state.vertical_relations
        )
        sequence = self.relation_sequence(axis)
        current = mapping.get(position, "")
        index = sequence.index(current) if current in sequence else 0
        next_value = sequence[(index + step) % len(sequence)]
        if next_value:
            mapping[position] = next_value
        else:
            mapping.pop(position, None)
        self.refresh_relation_buttons()
        self.update_summary()

    def update_given(self, position: tuple[int, int], text: str) -> None:
        if not text:
            self.state.givens.pop(position, None)
            self.update_summary()
            return
        value = int(text)
        max_value = self.state.grid_size
        if value < 1 or value > max_value:
            widget = self.given_inputs[position]
            widget.blockSignals(True)
            widget.setText(str(max_value) if value > max_value else "")
            widget.blockSignals(False)
            if value > max_value:
                self.state.givens[position] = max_value
            else:
                self.state.givens.pop(position, None)
        else:
            self.state.givens[position] = value
        self.update_summary()

    def refresh_digit_inputs(self) -> None:
        max_len = len(str(self.state.grid_size))
        for position, widget in self.given_inputs.items():
            widget.setMaxLength(max_len)
            widget.setText(
                str(self.state.givens[position])
                if position in self.state.givens
                else ""
            )

    def refresh_relation_buttons(self) -> None:
        for position, button in self.horizontal_buttons.items():
            value = self.state.horizontal_relations.get(position, "")
            button.setText(value)
            button.setProperty("active", bool(value))
            style = button.style()
            if style is not None:
                style.unpolish(button)
                style.polish(button)
        for position, button in self.vertical_buttons.items():
            value = self.state.vertical_relations.get(position, "")
            button.setText(value)
            button.setProperty("active", bool(value))
            style = button.style()
            if style is not None:
                style.unpolish(button)
                style.polish(button)

    def update_summary(self) -> None:
        givens = len(self.state.givens)
        relations = len(self.state.horizontal_relations) + len(
            self.state.vertical_relations
        )
        self.summary_label.setText(
            f"{self.state.variant} mode | {givens} givens | {relations} relation hints"
        )

    def solve(self) -> None:
        self.status_label.setText(
            f"{self.state.variant} solver is not implemented yet, but the puzzle state is ready."
        )
