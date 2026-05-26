from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGridLayout,
    QDoubleSpinBox,
    QGroupBox,
)
from PySide6.QtGui import QPalette, QColor

from graphics.keypoint_item import (
    KEYPOINT_NAMES,
)


class AnnotationDetailsPanel(QWidget):

    keypoints_edit_requested = Signal(bool)

    bbox_edit_requested = Signal(bool)

    add_bbox_requested = Signal(bool)

    delete_bbox_requested = Signal()

    keypoint_replace_requested = Signal(int)

    replace_all_requested = Signal()

    replace_mode_cleared = Signal()

    annotation_changed = Signal(object)

    def __init__(self):

        super().__init__()

        self.current_annotation = None
        self._is_loading_annotation = False
        self.replace_mode_index = None

        self.keypoint_inputs = []
        self.keypoint_replace_buttons = []
        self.add_bbox_button = QPushButton(
            "Add Bbox (B)"
        )
        self.del_bbox_button = QPushButton(
            "Del Bbox (Delete)"
        )
        self.replace_all_button = QPushButton(
            "Replace All (R)"
        )

        self.replace_status_label = QLabel(
            "No buttons selected. Press [I] for shortcuts"
        )

        self.layout = QVBoxLayout()

        # =================================
        # TITLE
        # =================================
        self.title_label = QLabel(
            "Annotation Details"
        )

        self.layout.addWidget(
            self.title_label
        )

        self.bbox_count_label = QLabel(
            "Bboxes in frame: 0"
        )
        self.bbox_count_label.setStyleSheet(
            "color: #dcdcdc; font-weight: bold;"
        )

        self.layout.addWidget(
            self.bbox_count_label
        )

        # =================================
        # EDIT BUTTONS
        # =================================
        self.edit_keypoints_button = (
            QPushButton(
                "Edit Keypoints (C)"
            )
        )

        self.edit_bbox_button = (
            QPushButton(
                "Edit Bounding Box (V)"
            )
        )

        self.edit_keypoints_button.setCheckable(
            True
        )

        self.edit_bbox_button.setCheckable(
            True
        )

        self.layout.addWidget(
            self.edit_keypoints_button
        )

        self.layout.addWidget(
            self.edit_bbox_button
        )

        self.add_bbox_button.setCheckable(True)

        self.layout.addWidget(
            self.add_bbox_button
        )

        self.layout.addWidget(
            self.del_bbox_button
        )

        self.layout.addWidget(
            self.replace_status_label
        )

        # =================================
        # BBOX SECTION
        # =================================
        bbox_group = QGroupBox(
            "Bounding Box"
        )

        bbox_layout = QGridLayout()

        bbox_group.setLayout(
            bbox_layout
        )

        self.bbox_x = QDoubleSpinBox()
        self.bbox_y = QDoubleSpinBox()
        self.bbox_w = QDoubleSpinBox()
        self.bbox_h = QDoubleSpinBox()

        self.bbox_inputs = [
            self.bbox_x,
            self.bbox_y,
            self.bbox_w,
            self.bbox_h,
        ]

        labels = ["x", "y", "w", "h"]

        for i, widget in enumerate(
            self.bbox_inputs
        ):

            widget.setRange(
                -99999,
                99999,
            )

            widget.setDecimals(2)
            widget.setKeyboardTracking(False)

            widget.setEnabled(False)

            widget.valueChanged.connect(
                self.update_bbox
            )

            bbox_layout.addWidget(
                QLabel(labels[i]),
                i,
                0,
            )

            bbox_layout.addWidget(
                widget,
                i,
                1,
            )

        self.layout.addWidget(
            bbox_group
        )

        # =================================
        # KEYPOINTS SECTION
        # =================================
        self.keypoints_group = (
            QGroupBox("Keypoints")
        )

        self.keypoints_layout = (
            QGridLayout()
        )

        self.keypoints_group.setLayout(
            self.keypoints_layout
        )

        self.layout.addWidget(
            self.keypoints_group
        )

        self.layout.addWidget(
            self.replace_all_button
        )

        self.setLayout(self.layout)

        # =================================
        # BUTTON SIGNALS
        # =================================
        self.edit_keypoints_button.toggled.connect(
            self.toggle_keypoint_editing
        )

        self.edit_bbox_button.toggled.connect(
            self.toggle_bbox_editing
        )

        self.add_bbox_button.toggled.connect(
            self.add_bbox_requested.emit
        )

        self.del_bbox_button.clicked.connect(
            self.delete_bbox_requested.emit
        )

        self.replace_all_button.clicked.connect(
            self.replace_all_requested.emit
        )

    def set_add_bbox_checked(self, checked):

        was_blocked = self.add_bbox_button.blockSignals(True)
        self.add_bbox_button.setChecked(checked)
        self.add_bbox_button.blockSignals(was_blocked)

    def set_bbox_action_buttons_enabled(self, enabled):

        self.del_bbox_button.setEnabled(enabled)

    def set_bbox_count(self, count):

        self.bbox_count_label.setText(
            f"Bboxes in frame: {count}"
        )

    def set_add_bbox_enabled(self, enabled):

        self.add_bbox_button.setEnabled(enabled)

    def set_annotation(self, annotation):

        self.current_annotation = annotation
        self._is_loading_annotation = True

        bbox = annotation["bbox"]

        self.bbox_x.setValue(bbox[0])
        self.bbox_y.setValue(bbox[1])
        self.bbox_w.setValue(bbox[2])
        self.bbox_h.setValue(bbox[3])

        # Clear old widgets
        while (
            self.keypoints_layout.count()
        ):

            child = (
                self.keypoints_layout.takeAt(
                    0
                )
            )

            if child.widget():
                child.widget().deleteLater()

        self.keypoint_inputs.clear()
        self.keypoint_replace_buttons.clear()

        keypoints = annotation[
            "keypoints"
        ]

        for i in range(
            0,
            len(keypoints),
            3,
        ):

            px = keypoints[i]

            py = keypoints[i + 1]

            kp_index = i // 3

            x_input = QDoubleSpinBox()
            y_input = QDoubleSpinBox()
            replace_button = QPushButton("Replace")

            for widget in [
                x_input,
                y_input,
            ]:

                widget.setRange(
                    -99999,
                    99999,
                )

                widget.setDecimals(2)
                widget.setKeyboardTracking(False)

                widget.setEnabled(False)

                widget.valueChanged.connect(
                    self.update_keypoints
                )

            x_input.setValue(px)

            y_input.setValue(py)

            self.keypoint_inputs.append(
                (
                    x_input,
                    y_input,
                )
            )
            self.keypoint_replace_buttons.append(replace_button)

            replace_button.clicked.connect(
                lambda checked=False, index=kp_index: self.request_replace_mode(index)
            )

            row = kp_index

            if kp_index < len(KEYPOINT_NAMES):
                label_text = KEYPOINT_NAMES[kp_index]
            else:
                label_text = f"KP {kp_index}"

            self.keypoints_layout.addWidget(
                QLabel(label_text),
                row,
                0,
            )

            self.keypoints_layout.addWidget(
                x_input,
                row,
                1,
            )

            self.keypoints_layout.addWidget(
                y_input,
                row,
                2,
            )

            self.keypoints_layout.addWidget(
                replace_button,
                row,
                3,
            )

        self._is_loading_annotation = False
        self._update_replace_button_styles()

    def clear_annotation(self):

        self.current_annotation = None
        self._is_loading_annotation = True
        self.set_bbox_count(0)

        self.bbox_x.setValue(0)
        self.bbox_y.setValue(0)
        self.bbox_w.setValue(0)
        self.bbox_h.setValue(0)

        while self.keypoints_layout.count():
            child = self.keypoints_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.keypoint_inputs.clear()
        self.keypoint_replace_buttons.clear()

        self._is_loading_annotation = False
        self.replace_mode_index = None
        self.replace_status_label.setText(
            "No buttons selected. Press [I] for shortcuts"
        )
        self._update_replace_button_styles()

    def sync_bbox_from_annotation(self, annotation):

        if self.current_annotation is not annotation:
            return

        self._is_loading_annotation = True

        bbox = annotation["bbox"]

        self.bbox_x.setValue(bbox[0])
        self.bbox_y.setValue(bbox[1])
        self.bbox_w.setValue(bbox[2])
        self.bbox_h.setValue(bbox[3])

        self._is_loading_annotation = False

    def sync_keypoints_from_annotation(self, annotation):

        if self.current_annotation is not annotation:
            return

        self._is_loading_annotation = True

        keypoints = annotation["keypoints"]

        for i, (
            x_input,
            y_input,
        ) in enumerate(self.keypoint_inputs):

            offset = i * 3

            x_input.setValue(keypoints[offset])
            y_input.setValue(keypoints[offset + 1])

        self._is_loading_annotation = False

    def request_replace_mode(self, keypoint_index):

        self.replace_mode_index = keypoint_index
        self.keypoint_replace_requested.emit(keypoint_index)
        base = (
            f"Click on canvas to place {KEYPOINT_NAMES[keypoint_index]}"
            if keypoint_index < len(KEYPOINT_NAMES)
            else f"Click on canvas to place keypoint {keypoint_index}"
        )
        self.replace_status_label.setText(f"{base} Press E to exit.")
        self._update_replace_button_styles()

    def clear_replace_mode(self):

        self.replace_mode_index = None
        self.replace_mode_cleared.emit()
        self.replace_status_label.setText(
            "No buttons selected. Press [I] for shortcuts"
        )
        self._update_replace_button_styles()

    def set_controls_enabled(self, enabled, active_replace_index=None):

        self.edit_keypoints_button.setEnabled(enabled)
        self.edit_bbox_button.setEnabled(enabled)

        for widget in self.bbox_inputs:
            widget.setEnabled(enabled and self.edit_bbox_button.isChecked())

        for i, (
            x_input,
            y_input,
        ) in enumerate(self.keypoint_inputs):

            keypoint_enabled = enabled and self.edit_keypoints_button.isChecked()

            x_input.setEnabled(keypoint_enabled)
            y_input.setEnabled(keypoint_enabled)

        for i, button in enumerate(self.keypoint_replace_buttons):
            button.setEnabled(enabled)

        self.replace_all_button.setEnabled(enabled)

        self.replace_mode_index = active_replace_index
        if active_replace_index is not None:
            if active_replace_index < len(KEYPOINT_NAMES):
                self.replace_status_label.setText(
                    f"Click on canvas to place {KEYPOINT_NAMES[active_replace_index]}. Press E to exit."
                )
            else:
                self.replace_status_label.setText(
                    f"Click on canvas to place keypoint {active_replace_index}. Press E to exit."
                )
        else:
            self.replace_status_label.setText(
                "No buttons selected. Press [I] for shortcuts"
            )
        self._update_replace_button_styles()

    def set_replace_mode_index(self, keypoint_index):

        self.replace_mode_index = keypoint_index
        base = (
            f"Click on canvas to place {KEYPOINT_NAMES[keypoint_index]}"
            if keypoint_index < len(KEYPOINT_NAMES)
            else f"Click on canvas to place keypoint {keypoint_index}"
        )
        self.replace_status_label.setText(f"{base} Press E to exit.")
        self._update_replace_button_styles()

    def _update_replace_button_styles(self):

        active_style = (
            "background-color: #ffcc33; color: black; font-weight: bold; border: 2px solid #a66a00;"
        )

        normal_style = ""

        for i, button in enumerate(self.keypoint_replace_buttons):
            if self.replace_mode_index is not None and i == self.replace_mode_index:
                button.setStyleSheet(active_style)
            else:
                button.setStyleSheet(normal_style)

    def set_replace_status_message(self, message):

        self.replace_status_label.setText(message)

    def toggle_keypoint_editing(
        self,
        enabled,
    ):

        for (
            x_input,
            y_input,
        ) in self.keypoint_inputs:

            x_input.setEnabled(enabled)

            y_input.setEnabled(enabled)

        self.keypoints_edit_requested.emit(
            enabled
        )

    def toggle_bbox_editing(
        self,
        enabled,
    ):

        for widget in self.bbox_inputs:

            widget.setEnabled(enabled)

        self.bbox_edit_requested.emit(
            enabled
        )

    def update_bbox(self):

        if (
            self.current_annotation
            is None
        ):
            return

        if self._is_loading_annotation:
            return

        bbox = self.current_annotation[
            "bbox"
        ]

        bbox[0] = self.bbox_x.value()
        bbox[1] = self.bbox_y.value()
        bbox[2] = self.bbox_w.value()
        bbox[3] = self.bbox_h.value()

        self.annotation_changed.emit(self.current_annotation)

    def update_keypoints(self):

        if (
            self.current_annotation
            is None
        ):
            return

        if self._is_loading_annotation:
            return

        keypoints = (
            self.current_annotation[
                "keypoints"
            ]
        )

        for i, (
            x_input,
            y_input,
        ) in enumerate(
            self.keypoint_inputs
        ):

            offset = i * 3

            keypoints[offset] = (
                x_input.value()
            )

            keypoints[offset + 1] = (
                y_input.value()
            )

        self.annotation_changed.emit(self.current_annotation)