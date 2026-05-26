import json
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
            "No buttons selected. Press [I] for shortcuts"
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
            "Save Annotations (Ctrl+S)"
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
        self.images_by_id = {}

        for image_info in (
            self.coco_data["images"]
        ):

            filename = Path(
                image_info["file_name"]
            ).name

            self.images_by_filename[
                filename
            ] = image_info
            self.images_by_id[image_info["id"]] = image_info

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
            self.on_keypoints_edit_toggled
        )

        self.annotation_details.bbox_edit_requested.connect(
            self.on_bbox_edit_toggled
        )

        self.annotation_details.annotation_changed.connect(
            self.on_annotation_modified
        )

        self.annotation_details.keypoint_replace_requested.connect(
            self.on_keypoint_replace_requested
        )

        self.annotation_details.add_bbox_requested.connect(
            self.on_add_bbox_requested
        )

        self.annotation_details.delete_bbox_requested.connect(
            self.on_delete_bbox_requested
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

        self.previous_frame_shortcut = QShortcut(
            QKeySequence("W"),
            self,
        )
        self.previous_frame_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.previous_frame_shortcut.activated.connect(
            self.go_to_previous_frame
        )

        self.next_frame_shortcut = QShortcut(
            QKeySequence("S"),
            self,
        )
        self.next_frame_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.next_frame_shortcut.activated.connect(
            self.go_to_next_frame
        )

        self.new_bbox_shortcut = QShortcut(
            QKeySequence("B"),
            self,
        )
        self.new_bbox_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.new_bbox_shortcut.activated.connect(
            self.annotation_details.add_bbox_button.click
        )

        self.delete_bbox_shortcut = QShortcut(
            QKeySequence(Qt.Key_Delete),
            self,
        )
        self.delete_bbox_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.delete_bbox_shortcut.activated.connect(
            self.annotation_details.del_bbox_button.click
        )

        self.replace_all_mode_shortcut = QShortcut(
            QKeySequence("R"),
            self,
        )
        self.replace_all_mode_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.replace_all_mode_shortcut.activated.connect(
            self.annotation_details.replace_all_button.click
        )

        self.edit_keypoints_shortcut = QShortcut(
            QKeySequence("C"),
            self,
        )
        self.edit_keypoints_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.edit_keypoints_shortcut.activated.connect(
            self.annotation_details.edit_keypoints_button.click
        )

        self.edit_bbox_shortcut = QShortcut(
            QKeySequence("V"),
            self,
        )
        self.edit_bbox_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.edit_bbox_shortcut.activated.connect(
            self.annotation_details.edit_bbox_button.click
        )

        self.save_shortcut = QShortcut(
            QKeySequence.Save,
            self,
        )
        self.save_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.save_shortcut.activated.connect(
            self.save_button.click
        )

        self.shortcuts_help_shortcut = QShortcut(
            QKeySequence("I"),
            self,
        )
        self.shortcuts_help_shortcut.setContext(
            Qt.WidgetWithChildrenShortcut
        )
        self.shortcuts_help_shortcut.activated.connect(
            self.show_shortcuts_help
        )

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

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
        self.add_bbox_mode_active = False
        self.current_frame_index = None

        self._update_bbox_action_buttons_state()

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

        if self.add_bbox_mode_active:
            self.exit_add_bbox_mode(commit=False)

        if self.replace_all_mode_active:
            self.exit_replace_all_mode()
        elif self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()

        self.load_frame_by_name(item.text())

    def load_frame_by_name(self, frame_name):

        image_path = self.frames_dir / frame_name

        self.current_image_path = image_path

        if frame_name not in self.images_by_filename:
            return

        self.current_frame_index = next(
            (i for i, path in enumerate(self.image_paths) if path.name == frame_name),
            None,
        )

        self._reload_current_frame()

    def load_frame_by_index(self, frame_index):

        if frame_index < 0 or frame_index >= len(self.image_paths):
            return

        self.current_frame_index = frame_index
        self.load_frame_by_name(self.image_paths[frame_index].name)

    def go_to_previous_frame(self):

        if self.current_frame_index is None:
            if self.image_paths:
                self.load_frame_by_index(0)
            return

        previous_index = self.current_frame_index - 1
        if previous_index < 0:
            return

        self.frame_list.setCurrentRow(previous_index)
        self.load_frame_by_index(previous_index)

    def go_to_next_frame(self):

        if self.current_frame_index is None:
            if self.image_paths:
                self.load_frame_by_index(0)
            return

        next_index = self.current_frame_index + 1
        if next_index >= len(self.image_paths):
            return

        self.frame_list.setCurrentRow(next_index)
        self.load_frame_by_index(next_index)

    def select_next_bbox(self):

        if not self.canvas.bbox_items:
            return

        if self.canvas.selected_bbox_item not in self.canvas.bbox_items:
            self.canvas.select_bbox_item(self.canvas.bbox_items[0])
            return

        current_index = self.canvas.bbox_items.index(
            self.canvas.selected_bbox_item
        )
        next_index = (current_index + 1) % len(self.canvas.bbox_items)
        self.canvas.select_bbox_item(self.canvas.bbox_items[next_index])

    def eventFilter(self, watched, event):

        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            self.select_next_bbox()
            return True

        return super().eventFilter(watched, event)

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

        self._update_bbox_action_buttons_state()

    def on_annotation_modified(self, annotation):

        self._sync_annotation_metadata(annotation)

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

    def _sync_annotation_metadata(self, annotation):

        bbox = annotation.get("bbox", [0, 0, 0, 0])
        annotation["area"] = round(float(bbox[2]) * float(bbox[3]), 2)

        keypoints = annotation.get("keypoints", [])
        annotation["num_keypoints"] = sum(
            1 for i in range(2, len(keypoints), 3) if keypoints[i] > 0
        )

    def _incomplete_annotations(self):

        incomplete = []

        for annotation in self.coco_data.get("annotations", []):
            image_info = self.images_by_id.get(annotation.get("image_id"))
            frame_name = Path(image_info["file_name"]).name if image_info else "<unknown frame>"
            keypoints = annotation.get("keypoints", [])
            visible_count = sum(
                1 for i in range(2, len(keypoints), 3) if keypoints[i] > 0
            )

            if visible_count < len(KEYPOINT_NAMES):
                incomplete.append((annotation, visible_count, frame_name))

        return incomplete

    def _next_annotation_id(self):

        return (
            max(
                (annotation.get("id", 0) for annotation in self.coco_data.get("annotations", [])),
                default=0,
            )
            + 1
        )

    def _create_face_annotation(self, image_info, bbox):

        x, y, w, h = bbox
        category_id = self.coco_data.get("categories", [{"id": 1}])[0].get("id", 1)
        keypoints = [0.0, 0.0, 0] * len(KEYPOINT_NAMES)

        return {
            "id": self._next_annotation_id(),
            "image_id": image_info["id"],
            "category_id": category_id,
            "bbox": [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
            "area": round(float(w) * float(h), 2),
            "iscrowd": 0,
            "confidence": 1.0,
            "keypoints": keypoints,
            "num_keypoints": 0,
        }

    def _reload_current_frame(self, select_annotation=None):

        if self.current_image_path is None:
            self.annotation_details.clear_annotation()
            self._clear_crop_preview()
            self._update_bbox_action_buttons_state()
            return

        frame_name = self.current_image_path.name
        image_info = self.images_by_filename.get(frame_name)

        if image_info is None:
            self.annotation_details.clear_annotation()
            self._clear_crop_preview()
            self._update_bbox_action_buttons_state()
            return

        image_id = image_info["id"]
        annotations = self.annotations_by_image_id.get(image_id, [])

        self.annotation_details.set_bbox_count(len(annotations))

        self.canvas.load_image(
            image_path=str(self.current_image_path),
            annotations=annotations,
        )

        selected_item = None

        if select_annotation is not None:
            select_id = select_annotation.get("id")

            for bbox_item in self.canvas.bbox_items:
                if bbox_item.annotation is select_annotation or bbox_item.annotation.get("id") == select_id:
                    selected_item = bbox_item
                    break

        if selected_item is None and len(self.canvas.bbox_items) > 0:
            selected_item = self.canvas.bbox_items[0]

        if selected_item is not None:
            self.canvas.select_bbox_item(selected_item)
        else:
            self.annotation_details.clear_annotation()
            self._clear_crop_preview()

        self._update_bbox_action_buttons_state()

    def _update_bbox_action_buttons_state(self):

        has_selection = self.canvas.selected_bbox_item is not None

        if self.add_bbox_mode_active:
            self.annotation_details.add_bbox_button.setEnabled(True)
            self.annotation_details.del_bbox_button.setEnabled(False)
            self.annotation_details.replace_all_button.setEnabled(False)
            return

        if self.active_replace_keypoint_index is not None:
            self.annotation_details.add_bbox_button.setEnabled(False)
            self.annotation_details.del_bbox_button.setEnabled(False)
            self.annotation_details.replace_all_button.setEnabled(False)
            return

        self.annotation_details.add_bbox_button.setEnabled(True)
        self.annotation_details.del_bbox_button.setEnabled(has_selection)
        self.annotation_details.replace_all_button.setEnabled(has_selection)

    def on_keypoints_edit_toggled(self, enabled):

        self.canvas.set_keypoint_editable(enabled)

        if enabled:
            self._set_mode_hint(
                "Edit Keypoints: drag the points."
            )
        elif not self.add_bbox_mode_active and self.active_replace_keypoint_index is None and not self.replace_all_mode_active:
            self.set_replace_status_message(self._inactive_hint())

    def on_bbox_edit_toggled(self, enabled):

        self.canvas.set_bbox_editable(enabled)

        if enabled:
            self._set_mode_hint(
                "Edit Bounding Box: drag the box or handles."
            )
        elif not self.add_bbox_mode_active and self.active_replace_keypoint_index is None and not self.replace_all_mode_active:
            self.set_replace_status_message(self._inactive_hint())

    def _set_mode_hint(self, message):

        self.set_replace_status_message(message)

    def _inactive_hint(self):

        return "No buttons selected. Press [I] for shortcuts"

    def show_shortcuts_help(self):

        shortcuts_text = (
            "Keyboard Shortcuts\n\n"
            "I - show this shortcut list.\n"
            "W / S - move to previous / next frame.\n"
            "Tab - cycle to the next bbox in the current frame.\n"
            "B - trigger Add Bbox.\n"
            "Delete - trigger Del Bbox.\n"
            "R - trigger Replace All.\n"
            "C - toggle Edit Keypoints.\n"
            "V - toggle Edit Bounding Box.\n"
            "Ctrl+S - trigger Save Annotations.\n"
            "E - exit the current mode when replacing keypoints/adding bbox."
        )

        QMessageBox.information(
            self,
            "Keyboard Shortcuts",
            shortcuts_text,
        )

    def on_add_bbox_requested(self, checked):

        if checked:
            self.enter_add_bbox_mode()
        else:
            self.exit_add_bbox_mode(
                commit=False,
                start_replace_all=False,
            )

    def enter_add_bbox_mode(self):

        if self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()

        self.add_bbox_mode_active = True
        self.canvas.set_add_bbox_mode(True)
        self.annotation_details.set_add_bbox_checked(True)

        self.annotation_details.edit_keypoints_button.setChecked(False)
        self.annotation_details.edit_bbox_button.setChecked(False)

        self.canvas.set_keypoint_editable(False)
        self.canvas.set_bbox_editable(False)

        self.annotation_details.set_controls_enabled(False)
        self.annotation_details.add_bbox_button.setEnabled(True)
        self.annotation_details.del_bbox_button.setEnabled(False)
        self._set_mode_hint(
            "Add Bbox: drag to draw. Press E or Add Bbox again to finish."
        )
        self._update_bbox_action_buttons_state()

    def exit_add_bbox_mode(self, commit=False, start_replace_all=False):

        if not self.add_bbox_mode_active and not self.canvas.add_bbox_mode_active:
            return None

        self.add_bbox_mode_active = False

        new_annotation = None

        if commit:
            new_annotation = self._commit_pending_add_bbox()

        self.canvas.clear_add_bbox_mode()
        self.annotation_details.set_add_bbox_checked(False)

        self.annotation_details.set_controls_enabled(True)
        self.set_replace_status_message(self._inactive_hint())

        if new_annotation is not None:
            self._reload_current_frame(select_annotation=new_annotation)

        self._update_bbox_action_buttons_state()

        if commit and start_replace_all and new_annotation is not None:
            self.on_replace_all_requested()

        return new_annotation

    def _commit_pending_add_bbox(self):

        pending_rect = self.canvas.pending_add_bbox_rect()

        if pending_rect is None:
            return None

        if pending_rect.width() < 1 or pending_rect.height() < 1:
            return None

        image_info = self.images_by_filename.get(
            self.current_image_path.name if self.current_image_path is not None else ""
        )

        if image_info is None:
            return None

        scene_rect = self.canvas.sceneRect()
        final_rect = pending_rect.intersected(scene_rect)

        if final_rect.width() < 1 or final_rect.height() < 1:
            return None

        new_annotation = self._create_face_annotation(
            image_info,
            (
                final_rect.x(),
                final_rect.y(),
                final_rect.width(),
                final_rect.height(),
            ),
        )

        self.coco_data["annotations"].append(new_annotation)
        self.annotations_by_image_id.setdefault(image_info["id"], []).append(
            new_annotation
        )

        return new_annotation

    def on_delete_bbox_requested(self):

        if self.add_bbox_mode_active:
            self.exit_add_bbox_mode(commit=False)

        if self.replace_all_mode_active:
            self.exit_replace_all_mode()
        elif self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()

        selected_item = self.canvas.selected_bbox_item

        if selected_item is None or selected_item.annotation is None:
            return

        annotation = selected_item.annotation
        image_id = annotation.get("image_id")

        self.coco_data["annotations"] = [
            item for item in self.coco_data.get("annotations", [])
            if item is not annotation
        ]

        if image_id in self.annotations_by_image_id:
            self.annotations_by_image_id[image_id] = [
                item for item in self.annotations_by_image_id[image_id]
                if item is not annotation
            ]

        self._reload_current_frame()

    def on_keypoint_replace_requested(self, keypoint_index):

        if self.add_bbox_mode_active:
            self.exit_add_bbox_mode(commit=False)

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
        self._set_mode_hint(
            f"Keypoint Replace: click {KEYPOINT_NAMES[keypoint_index] if keypoint_index < len(KEYPOINT_NAMES) else 'the keypoint'}. Press E to exit."
        )
        self._update_bbox_action_buttons_state()

    def on_replace_all_requested(self):

        if self.annotation_details.current_annotation is None:
            return

        if self.add_bbox_mode_active:
            self.exit_add_bbox_mode(commit=False)

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
        self._set_mode_hint(
            "Replace All: click keypoints in order. E next, Q previous."
        )
        self._update_bbox_action_buttons_state()

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
        self._set_mode_hint(
            "Replace All: click keypoints in order. E next, Q previous."
        )
        self._update_bbox_action_buttons_state()

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
        self._set_mode_hint(
            "Replace All: click keypoints in order. E next, Q previous."
        )
        self._update_bbox_action_buttons_state()

    def _on_e_pressed(self):
        if self.add_bbox_mode_active:
            self.exit_add_bbox_mode(
                commit=True,
                start_replace_all=True,
            )
            return

        # If Replace-All is active, E advances the sequence. Otherwise,
        # if we're in a single-key replace mode, E should exit that mode.
        if self.replace_all_mode_active:
            self.advance_replace_all_mode()
            return

        if self.active_replace_keypoint_index is not None:
            self.exit_keypoint_replace_mode()
            # update status to show inactive
            self.set_replace_status_message(self._inactive_hint())

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
        self.set_replace_status_message(self._inactive_hint())
        self._update_bbox_action_buttons_state()

    def set_replace_status_message(self, message):

        self.replace_hint_label.setText(message)
        self.annotation_details.set_replace_status_message(message)

    def update_crop_preview(
        self,
        annotation,
    ):

        if annotation is None:
            self._clear_crop_preview()
            return

        bbox = annotation.get("bbox")

        if not bbox or len(bbox) < 4:
            self._clear_crop_preview()
            return

        x, y, w, h = bbox

        if w <= 0 or h <= 0:
            self._clear_crop_preview()
            return

        from PySide6.QtGui import (
            QPainter,
            QColor,
            QPen,
            QFont,
        )

        pixmap = QPixmap(
            str(self.current_image_path)
        )

        if pixmap.isNull():
            self._clear_crop_preview()
            return

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

    def _clear_crop_preview(self):

        self.crop_preview.setPixmap(QPixmap())
        self.crop_preview.setText("")

    def save_annotations(self):
        try:
            for annotation in self.coco_data.get("annotations", []):
                self._sync_annotation_metadata(annotation)

            incomplete = self._incomplete_annotations()

            if incomplete:
                missing_by_frame = {}

                for _annotation, visible_count, frame_name in incomplete:
                    missing_by_frame.setdefault(frame_name, []).append(visible_count)

                missing_lines = []

                for frame_name in sorted(missing_by_frame):
                    counts = missing_by_frame[frame_name]
                    missing_lines.append(
                        f"- {frame_name}: {len(counts)} incomplete bbox(s), visible keypoints: {', '.join(str(count) + '/5' for count in counts)}"
                    )

                QMessageBox.critical(
                    self,
                    "Save Failed",
                    (
                        "Cannot save yet. Each bounding box must have all 5 keypoints placed.\n\n"
                        "Frames missing keypoints:\n"
                        + "\n".join(missing_lines)
                    ),
                )
                return

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