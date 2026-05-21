import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.coco_loader import (
    load_coco_annotations,
)

from gui.annotation_canvas import (
    AnnotationCanvas,
)
from graphics.keypoint_item import (
    KEYPOINT_NAMES,
    KEYPOINT_COLORS,
)

from widgets.annotation_details_panel import (
    AnnotationDetailsPanel,
)


class MainWindow(QMainWindow):

    @staticmethod
    def _rebuild_bbox_from_keypoints(annotation):
        keypoints = annotation.get("keypoints", [])

        visible_points = []
        for i in range(0, len(keypoints), 3):
            x = keypoints[i]
            y = keypoints[i + 1]
            vis = keypoints[i + 2]
            if vis > 0:
                visible_points.append((x, y))

        if not visible_points:
            return False

        min_x = min(p[0] for p in visible_points)
        min_y = min(p[1] for p in visible_points)
        max_x = max(p[0] for p in visible_points)
        max_y = max(p[1] for p in visible_points)

        width = max_x - min_x
        height = max_y - min_y

        # Keep bbox valid even when all visible keypoints collapse to one pixel.
        if width <= 0:
            width = 1.0
        if height <= 0:
            height = 1.0

        annotation["bbox"] = [
            round(min_x, 2),
            round(min_y, 2),
            round(width, 2),
            round(height, 2),
        ]
        return True

    def __init__(self, video_title=None):

        super().__init__()

        self.setWindowTitle(
            "Face Annotation Tool"
        )

        self.resize(1600, 900)

        # Resolve project paths relative to this file so launching from any
        # working directory still loads/saves the expected dataset files.
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_root = self.project_root / "data"

        available_video_titles = sorted(
            path.name
            for path in self.data_root.iterdir()
            if path.is_dir()
        ) if self.data_root.exists() else []

        if video_title is None:
            if not available_video_titles:
                raise FileNotFoundError(
                    f"No video folders found under {self.data_root}"
                )

            video_title = available_video_titles[0]

        self.video_title = video_title
        self.video_dir = self.data_root / self.video_title

        if not self.video_dir.is_dir():
            available_text = ", ".join(available_video_titles) or "<none>"
            raise FileNotFoundError(
                f"Video folder not found: {self.video_dir}. Available titles: {available_text}"
            )

        self.annotations_path = self.video_dir / "annotations.json"

        self.coco_data = (
            load_coco_annotations(
                self.annotations_path
            )
        )

        # Repair invalid bbox records (w/h <= 0) using visible keypoints.
        for annotation in self.coco_data.get("annotations", []):
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            if len(bbox) < 4 or bbox[2] <= 0 or bbox[3] <= 0:
                self._rebuild_bbox_from_keypoints(annotation)

        self.frames_dir = self.video_dir / "frames"

        self.setWindowTitle(
            f"Face Annotation Tool - {self.video_title}"
        )

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QHBoxLayout()

        central_widget.setLayout(
            main_layout
        )

        # LEFT PANEL
        self.frame_list = QListWidget()

        self.frame_list.setMaximumWidth(
            250
        )

        main_layout.addWidget(
            self.frame_list
        )

        # CENTER PANEL
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_panel.setLayout(center_layout)

        self.canvas = AnnotationCanvas()

        self.replace_hint_label = QLabel(
            "Replace mode inactive"
        )
        self.replace_hint_label.setAlignment(
            Qt.AlignCenter
        )
        self.replace_hint_label.setStyleSheet(
            "color: #f0f0f0; background-color: #2a2a2a; padding: 6px;"
        )

        center_layout.addWidget(
            self.canvas,
            1,
        )
        center_layout.addWidget(
            self.replace_hint_label,
            0,
        )

        main_layout.addWidget(
            center_panel,
            1,
        )

        # RIGHT PANEL
        right_panel = QWidget()

        right_layout = QVBoxLayout()

        right_panel.setLayout(
            right_layout
        )

        self.annotation_details = (
            AnnotationDetailsPanel()
        )
        self.annotation_details.replace_status_label.setVisible(False)

        self.crop_preview = QLabel(
            "Crop Preview"
        )

        self.crop_preview.setMinimumHeight(
            250
        )

        self.crop_preview.setAlignment(
            Qt.AlignCenter
        )

        self.crop_preview.setStyleSheet("""
            border: 1px solid gray;
            background-color: #222;
            color: white;
        """)

        self.save_button = QPushButton(
            "Save Annotations"
        )

        self.save_button.clicked.connect(
            self.save_annotations
        )

        right_layout.addWidget(
            self.annotation_details
        )

        right_layout.addWidget(
            self.crop_preview
        )

        right_layout.addWidget(
            self.save_button
        )

        right_panel.setMaximumWidth(
            350
        )

        main_layout.addWidget(
            right_panel
        )

        # LOOKUP TABLES
        self.images_by_filename = {}

        for image_info in (
            self.coco_data["images"]
        ):

            filename = Path(
                image_info["file_name"]
            ).name

            self.images_by_filename[
                filename
            ] = image_info

        self.annotations_by_image_id = {}

        for annotation in (
            self.coco_data[
                "annotations"
            ]
        ):

            image_id = annotation[
                "image_id"
            ]

            if (
                image_id
                not in
                self.annotations_by_image_id
            ):

                self.annotations_by_image_id[
                    image_id
                ] = []

            self.annotations_by_image_id[
                image_id
            ].append(annotation)

        # FRAME LIST
        self.image_paths = sorted(
            self.frames_dir.glob("*.jpg")
        )

        for image_path in self.image_paths:

            self.frame_list.addItem(
                image_path.name
            )

        # SIGNALS
        self.frame_list.itemClicked.connect(
            self.load_selected_frame
        )

        self.canvas.annotation_selected.connect(
            self.on_annotation_selected
        )

        # ---------------------------------
        # Enable/disable canvas editing
        # ---------------------------------
        self.annotation_details.keypoints_edit_requested.connect(
            self.canvas.set_keypoint_editable
        )

        self.annotation_details.bbox_edit_requested.connect(
            self.canvas.set_bbox_editable
        )

        self.annotation_details.annotation_changed.connect(
            self.on_annotation_modified
        )

        self.annotation_details.keypoint_replace_requested.connect(
            self.on_keypoint_replace_requested
        )

        self.annotation_details.replace_all_requested.connect(
            self.on_replace_all_requested
        )

        self.annotation_details.replace_mode_cleared.connect(
            self.exit_keypoint_replace_mode
        )

        self.canvas.annotation_geometry_changed.connect(
            self.on_annotation_modified
        )

        self.canvas.keypoint_geometry_changed.connect(
            self.on_annotation_modified
        )

        self.canvas.replace_all_completed.connect(
            self.exit_replace_all_mode
        )

        self.replace_all_shortcut = QShortcut(
            QKeySequence("E"),
            self,
        )
        self.replace_all_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        # Route the single-key 'E' shortcut through a centric handler so
        # it can either advance Replace-All or exit a single-key replace
        # mode depending on current state.
        self.replace_all_shortcut.activated.connect(
            self._on_e_pressed
        )

        self.previous_replace_shortcut = QShortcut(
            QKeySequence("Q"),
            self,
        )
        self.previous_replace_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.previous_replace_shortcut.activated.connect(
            self._on_q_pressed
        )

        self.active_replace_keypoint_index = None
        self.replace_all_mode_active = False

        # ---------------------------------
        # IMPORTANT:
        # Do NOT refresh entire scene
        # on every coordinate edit.
        #
        # Coordinate edits already modify
        # annotation data directly.
        #
        # Full refresh causes:
        # - selection resets
        # - edit mode resets
        # - unstable dragging
        # - poor UX
        # ---------------------------------

    def load_selected_frame(self, item):

        if self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()

        frame_name = item.text()

        image_path = (
            self.frames_dir / frame_name
        )

        self.current_image_path = image_path

        if (
            frame_name
            not in
            self.images_by_filename
        ):

            return

        image_info = (
            self.images_by_filename[
                frame_name
            ]
        )

        image_id = image_info["id"]

        annotations = (
            self.annotations_by_image_id.get(
                image_id,
                [],
            )
        )

        self.canvas.load_image(
            image_path=str(image_path),
            annotations=annotations,
        )

        if len(self.canvas.bbox_items) > 0:

            first_bbox_item = (
                self.canvas.bbox_items[0]
            )

            self.canvas.select_bbox_item(
                first_bbox_item
            )

    def on_annotation_selected(
        self,
        annotation,
    ):

        self.annotation_details.set_annotation(
            annotation
        )

        self.update_crop_preview(
            annotation
        )

    def on_annotation_modified(self, annotation):

        self.canvas.update_annotation_visuals(annotation)

        self.annotation_details.sync_keypoints_from_annotation(
            annotation
        )

        self.annotation_details.sync_bbox_from_annotation(
            annotation
        )

        self.update_crop_preview(
            annotation
        )

    def on_keypoint_replace_requested(self, keypoint_index):

        self.replace_all_mode_active = False
        self.active_replace_keypoint_index = keypoint_index

        self.canvas.set_keypoint_replace_mode(
            keypoint_index
        )
        self.canvas.set_active_keypoint_index(keypoint_index)
        self.canvas.keypoint_replace_all_mode_active = False

        self.annotation_details.edit_keypoints_button.setChecked(False)
        self.annotation_details.edit_bbox_button.setChecked(False)

        self.canvas.set_keypoint_editable(False)
        self.canvas.set_bbox_editable(False)

        self.annotation_details.set_controls_enabled(
            False,
            active_replace_index=keypoint_index,
        )
        self.set_replace_status_message(
            self._single_replace_prompt_text(keypoint_index)
        )

    def on_replace_all_requested(self):

        if self.annotation_details.current_annotation is None:
            return

        self.replace_all_mode_active = True
        self.active_replace_keypoint_index = 0

        self.canvas.keypoint_replace_all_mode_active = True
        self.canvas.set_keypoint_replace_mode(0)
        self.canvas.set_active_keypoint_index(0)

        self.annotation_details.edit_keypoints_button.setChecked(False)
        self.annotation_details.edit_bbox_button.setChecked(False)

        self.canvas.set_keypoint_editable(False)
        self.canvas.set_bbox_editable(False)

        self.annotation_details.set_controls_enabled(
            False,
            active_replace_index=0,
        )
        self.set_replace_status_message(
            self._replace_prompt_text(0)
        )

    def advance_replace_all_mode(self):

        if not self.replace_all_mode_active:
            return

        if self.active_replace_keypoint_index is None:
            return

        next_index = self.active_replace_keypoint_index + 1

        keypoint_count = len(
            self.annotation_details.current_annotation["keypoints"]
        ) // 3

        if next_index >= keypoint_count:
            self.exit_replace_all_mode()
            return

        self.active_replace_keypoint_index = next_index
        self.canvas.set_keypoint_replace_mode(next_index)
        self.canvas.set_active_keypoint_index(next_index)
        self.annotation_details.set_controls_enabled(
            False,
            active_replace_index=next_index,
        )
        self.set_replace_status_message(
            self._replace_prompt_text(next_index)
        )

    def _on_q_pressed(self):
        # In Replace-All, Q moves back to the previous keypoint if possible.
        # The first keypoint has no previous step, so Q is a no-op there.
        if not self.replace_all_mode_active:
            return

        if self.active_replace_keypoint_index is None:
            return

        if self.active_replace_keypoint_index == 0:
            return

        previous_index = self.active_replace_keypoint_index - 1
        self.active_replace_keypoint_index = previous_index
        self.canvas.set_keypoint_replace_mode(previous_index)
        self.canvas.set_active_keypoint_index(previous_index)
        self.annotation_details.set_controls_enabled(
            False,
            active_replace_index=previous_index,
        )
        self.set_replace_status_message(
            self._replace_prompt_text(previous_index)
        )

    def _on_e_pressed(self):
        # If Replace-All is active, E advances the sequence. Otherwise,
        # if we're in a single-key replace mode, E should exit that mode.
        if self.replace_all_mode_active:
            self.advance_replace_all_mode()
            return

        if self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()
            # update status to show inactive
            self.set_replace_status_message(
                "Replace mode inactive"
            )

    def exit_replace_all_mode(self):

        if not self.replace_all_mode_active:
            return

        self.replace_all_mode_active = False
        self.exit_keypoint_replace_mode()

    @staticmethod
    def _single_replace_prompt_text(keypoint_index):

        if keypoint_index < len(KEYPOINT_NAMES):
            label = KEYPOINT_NAMES[keypoint_index]
        else:
            label = f"keypoint {keypoint_index}"

        return f"Click on canvas to place {label}. Press E to exit."

    @staticmethod
    def _replace_prompt_text(keypoint_index):

        if keypoint_index < len(KEYPOINT_NAMES):
            label = KEYPOINT_NAMES[keypoint_index]
        else:
            label = f"keypoint {keypoint_index}"

        next_index = keypoint_index + 1

        if keypoint_index > 0:
            prev_label = KEYPOINT_NAMES[keypoint_index - 1]
            if next_index < len(KEYPOINT_NAMES):
                next_label = KEYPOINT_NAMES[next_index]
                return (
                    f"Click on canvas to place {label}. Press Q for {prev_label}. "
                    f"Press E for {next_label}."
                )

            return (
                f"Click on canvas to place {label}. Press Q for {prev_label}. "
                "Press E to exit."
            )

        if next_index < len(KEYPOINT_NAMES):
            next_label = KEYPOINT_NAMES[next_index]
            return f"Click on canvas to place {label}. Press E for {next_label}."

        return f"Click on canvas to place {label}. Press E to exit."

    def exit_keypoint_replace_mode(self):

        self.active_replace_keypoint_index = None
        self.canvas.clear_keypoint_replace_mode()
        self.canvas.clear_active_keypoint_index()

        self.annotation_details.set_controls_enabled(True)
        self.set_replace_status_message("Replace mode inactive")

    def set_replace_status_message(self, message):

        self.replace_hint_label.setText(message)
        self.annotation_details.set_replace_status_message(message)

    def update_crop_preview(
        self,
        annotation,
    ):

        from PySide6.QtGui import (
            QPainter,
            QColor,
            QPen,
            QFont,
        )

        pixmap = QPixmap(
            str(self.current_image_path)
        )

        bbox = annotation["bbox"]

        x, y, w, h = bbox

        # =================================
        # Crop face region
        # =================================
        cropped = pixmap.copy(
            int(x),
            int(y),
            int(w),
            int(h),
        )

        # =================================
        # Draw keypoints on crop
        # =================================
        painter = QPainter(cropped)

        pen = QPen(QColor("red"))
        pen.setWidth(1)
        pen.setCosmetic(True)

        painter.setPen(pen)

        font = QFont()

        font.setPointSize(10)

        painter.setFont(font)

        keypoints = annotation["keypoints"]

        for i in range(
            0,
            len(keypoints),
            3,
        ):

            px = keypoints[i]

            py = keypoints[i + 1]

            vis = keypoints[i + 2]

            if vis == 0:
                continue

            # Convert to crop-relative coords
            local_x = px - x

            local_y = py - y

            color = KEYPOINT_COLORS[
                (i // 3) % len(KEYPOINT_COLORS)
            ]
            pen.setColor(color)
            painter.setPen(pen)

            # Draw a single-pixel keypoint exactly at its coordinate.
            painter.drawPoint(
                int(local_x),
                int(local_y),
            )

        painter.end()

        # =================================
        # Scale preview
        # =================================
        scaled = cropped.scaled(
            250,
            250,
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )

        self.crop_preview.setPixmap(
            scaled
        )

    def save_annotations(self):
        try:
            with open(
                self.annotations_path,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    self.coco_data,
                    f,
                    indent=2,
                )

            QMessageBox.information(
                self,
                "Save Complete",
                f"Annotations saved to:\n{self.annotations_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Could not save annotations:\n{exc}",
            )
        finally:
            if self.active_replace_keypoint_index is not None:
                self.exit_keypoint_replace_mode()