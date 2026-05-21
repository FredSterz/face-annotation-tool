from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)
from graphics.bbox_item import FaceBBoxItem
from graphics.bbox_item import BBoxHandleItem
from graphics.keypoint_item import (
    KeypointItem,
    KEYPOINT_COLORS,
)


class AnnotationCanvas(QGraphicsView):

    # Use object to preserve the original dict reference.
    # Signal(dict) can marshal/copy payloads and break in-place edits.
    annotation_selected = Signal(object)
    annotation_geometry_changed = Signal(object)
    keypoint_geometry_changed = Signal(object)
    replace_all_completed = Signal()

    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing, True)

        self.image_item = None
        self.current_image_path = None
        self.current_annotations = []

        self.bbox_items = []
        self.keypoint_items = []

        self.selected_bbox_item = None
        self.active_keypoint_index = None

        self.keypoint_editable = False
        self.bbox_editable = False
        self.zoom_factor = 1.0
        self.min_zoom_factor = 0.2
        self.max_zoom_factor = 20.0
        self._dragging_bbox_item = None
        self._bbox_drag_offset = None
        self.keypoint_replace_mode_index = None
        self.keypoint_replace_all_mode_active = False

    def load_image(self, image_path, annotations):
        self.current_image_path = image_path
        self.current_annotations = annotations
        self.refresh_scene()

    @staticmethod
    def _keypoint_radius_from_bbox(bbox):
        # Keep keypoints as true single-pixel markers in the main canvas.
        return 0.5

    def refresh_scene(self):
        self.scene.clear()
        self.bbox_items = []
        self.keypoint_items = []
        self.selected_bbox_item = None
        self.active_keypoint_index = None

        if not self.current_image_path:
            return

        pixmap = QPixmap(self.current_image_path)
        if pixmap.isNull():
            return

        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.setSceneRect(self.image_item.boundingRect())

        for annotation in self.current_annotations:
            bbox = annotation.get("bbox", [0, 0, 0, 0])
            x, y, w, h = bbox
            keypoint_radius = self._keypoint_radius_from_bbox(bbox)

            bbox_item = FaceBBoxItem(
                x,
                y,
                w,
                h,
                annotation=annotation,
                selection_callback=self.select_bbox_item,
                geometry_changed_callback=self._on_bbox_geometry_changed,
            )
            bbox_item.set_editable(self.bbox_editable)
            self.scene.addItem(bbox_item)
            self.bbox_items.append(bbox_item)

            keypoints = annotation.get("keypoints", [])
            for i in range(0, len(keypoints), 3):
                px = keypoints[i]
                py = keypoints[i + 1]
                vis = keypoints[i + 2]

                if vis == 0:
                    continue

                kp_item = KeypointItem(
                    x=px,
                    y=py,
                    annotation=annotation,
                    keypoint_index=i // 3,
                    radius=keypoint_radius,
                    color=KEYPOINT_COLORS[i // 3 % len(KEYPOINT_COLORS)],
                    geometry_changed_callback=self._on_keypoint_geometry_changed,
                )
                kp_item.set_editable(self.keypoint_editable)
                self.scene.addItem(kp_item)
                self.keypoint_items.append(kp_item)

        self._update_navigation_mode()
        self._update_keypoint_highlights()

    def _on_bbox_geometry_changed(self, annotation):

        self.annotation_geometry_changed.emit(annotation)

    def _on_keypoint_geometry_changed(self, annotation):

        self.keypoint_geometry_changed.emit(annotation)

    def refresh_keypoint_positions(self, annotation):

        for item in self.keypoint_items:

            if item.annotation is not annotation:
                continue

            offset = item.keypoint_index * 3
            keypoints = annotation.get("keypoints", [])

            if offset + 1 >= len(keypoints):
                continue

            item.setPos(
                keypoints[offset],
                keypoints[offset + 1],
            )

    def set_active_keypoint_index(self, keypoint_index):

        self.active_keypoint_index = keypoint_index
        self._update_keypoint_highlights()

    def clear_active_keypoint_index(self):

        self.active_keypoint_index = None
        self._update_keypoint_highlights()

    def set_keypoint_replace_mode(self, keypoint_index):

        self.keypoint_replace_mode_index = keypoint_index
        self._update_navigation_mode()

    def clear_keypoint_replace_mode(self):

        self.keypoint_replace_mode_index = None
        self._update_navigation_mode()

    def update_annotation_visuals(self, annotation):

        for bbox_item in self.bbox_items:
            if bbox_item.annotation is annotation:
                bbox_item.sync_from_annotation()

        for item in self.keypoint_items:

            if item.annotation is annotation:

                bbox = annotation.get("bbox", [0, 0, 0, 0])

                item.set_radius(
                    self._keypoint_radius_from_bbox(bbox)
                )

        self._update_keypoint_highlights()

    def refresh_keypoint_sizes(self):

        for item in self.keypoint_items:

            annotation = item.annotation

            bbox = annotation.get("bbox", [0, 0, 0, 0])

            item.set_radius(
                self._keypoint_radius_from_bbox(bbox)
            )

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, self.transform())

        if self.keypoint_replace_mode_index is not None:

            if self.selected_bbox_item is None:
                event.accept()
                return

            annotation = self.selected_bbox_item.annotation

            if annotation is not None:
                offset = self.keypoint_replace_mode_index * 3
                keypoints = annotation.get("keypoints", [])

                if offset + 2 < len(keypoints):
                    keypoints[offset] = scene_pos.x()
                    keypoints[offset + 1] = scene_pos.y()
                    keypoints[offset + 2] = 2

                    self.refresh_keypoint_positions(annotation)
                    self.keypoint_geometry_changed.emit(annotation)

            event.accept()
            return

        picked_bbox = None

        if isinstance(item, FaceBBoxItem):
            picked_bbox = item
        elif isinstance(item, BBoxHandleItem):
            picked_bbox = item.parent_bbox_item

        if picked_bbox is not None:
            self.select_bbox_item(picked_bbox)

        if (
            self.bbox_editable
            and isinstance(item, FaceBBoxItem)
        ):
            rect = item.rect()
            self._dragging_bbox_item = item
            self._bbox_drag_offset = (
                scene_pos.x() - rect.left(),
                scene_pos.y() - rect.top(),
            )
        else:
            self._dragging_bbox_item = None
            self._bbox_drag_offset = None

        super().mousePressEvent(event)

    def _update_keypoint_highlights(self):

        active_annotation = None

        if self.selected_bbox_item is not None:
            active_annotation = self.selected_bbox_item.annotation

        for item in self.keypoint_items:
            item.set_highlighted(
                active_annotation is not None
                and item.annotation is active_annotation
                and self.active_keypoint_index is not None
                and item.keypoint_index == self.active_keypoint_index
            )

    def mouseMoveEvent(self, event):

        scene_pos = self.mapToScene(event.pos())

        if self.selected_bbox_item is not None:

            active_handle = (
                self.selected_bbox_item.active_resize_handle()
            )

            if active_handle is not None:
                self.selected_bbox_item.resize_from_handle(
                    active_handle,
                    scene_pos,
                )
                event.accept()
                return

        if (
            self._dragging_bbox_item is not None
            and self._bbox_drag_offset is not None
        ):

            offset_x, offset_y = self._bbox_drag_offset

            self._dragging_bbox_item.move_to(
                scene_pos.x() - offset_x,
                scene_pos.y() - offset_y,
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        if self.selected_bbox_item is not None:
            self.selected_bbox_item.end_resize()

        self._dragging_bbox_item = None
        self._bbox_drag_offset = None

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):

        delta = event.angleDelta().y()

        if delta == 0:
            event.ignore()
            return

        zoom_step = 1.2 if delta > 0 else 1 / 1.2
        next_zoom = self.zoom_factor * zoom_step

        if next_zoom < self.min_zoom_factor:
            zoom_step = self.min_zoom_factor / self.zoom_factor
            next_zoom = self.min_zoom_factor
        elif next_zoom > self.max_zoom_factor:
            zoom_step = self.max_zoom_factor / self.zoom_factor
            next_zoom = self.max_zoom_factor

        if next_zoom == self.zoom_factor:
            event.accept()
            return

        self.scale(zoom_step, zoom_step)
        self.zoom_factor = next_zoom
        event.accept()

    def _update_navigation_mode(self):

        if (
            self.keypoint_editable
            or self.bbox_editable
            or self.keypoint_replace_mode_index is not None
        ):
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def select_bbox_item(self, bbox_item):
        if self.selected_bbox_item is not None:
            self.selected_bbox_item.set_selected_style(False)

        self.selected_bbox_item = bbox_item
        self.selected_bbox_item.set_selected_style(True)

        if self.selected_bbox_item.annotation is not None:
            self.annotation_selected.emit(
                self.selected_bbox_item.annotation
            )

        self._update_keypoint_highlights()

    def set_keypoint_editable(self, editable):
        self.keypoint_editable = editable
        for item in self.keypoint_items:
            item.set_editable(editable)

        self._update_navigation_mode()

    def set_bbox_editable(self, editable):
        self.bbox_editable = editable
        for item in self.bbox_items:
            item.set_editable(editable)

        self._update_navigation_mode()
