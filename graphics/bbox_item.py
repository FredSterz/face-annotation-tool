from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem


class BBoxHandleItem(QGraphicsRectItem):

    HANDLE_SIZE = 8.0

    def __init__(self, handle_name, parent_bbox_item):

        super().__init__(
            -self.HANDLE_SIZE / 2,
            -self.HANDLE_SIZE / 2,
            self.HANDLE_SIZE,
            self.HANDLE_SIZE,
            parent_bbox_item,
        )

        self.handle_name = handle_name
        self.parent_bbox_item = parent_bbox_item

        self.setBrush(QBrush(QColor("white")))
        self.setPen(QPen(Qt.black))
        self.setZValue(30)
        self.setFlag(
            QGraphicsItem.ItemIgnoresTransformations,
            True,
        )
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(self._cursor_for_handle(handle_name))

    @staticmethod
    def _cursor_for_handle(handle_name):

        mapping = {
            "top_left": Qt.SizeFDiagCursor,
            "top": Qt.SizeVerCursor,
            "top_right": Qt.SizeBDiagCursor,
            "right": Qt.SizeHorCursor,
            "bottom_right": Qt.SizeFDiagCursor,
            "bottom": Qt.SizeVerCursor,
            "bottom_left": Qt.SizeBDiagCursor,
            "left": Qt.SizeHorCursor,
        }

        return QCursor(mapping[handle_name])

    def mousePressEvent(self, event):

        self.grabMouse()
        self.parent_bbox_item.request_selection()
        self.parent_bbox_item.begin_resize(self.handle_name)
        event.accept()

    def mouseMoveEvent(self, event):

        self.parent_bbox_item.resize_from_handle(
            self.handle_name,
            event.scenePos(),
        )
        event.accept()

    def mouseReleaseEvent(self, event):

        self.parent_bbox_item.end_resize()
        self.ungrabMouse()
        event.accept()


class FaceBBoxItem(QGraphicsRectItem):

    def __init__(
        self,
        x,
        y,
        w,
        h,
        annotation=None,
        selection_callback=None,
        geometry_changed_callback=None,
    ):

        super().__init__(x, y, w, h)

        self.annotation = annotation
        self.selection_callback = selection_callback
        self.geometry_changed_callback = geometry_changed_callback
        self.is_selected = False
        self.is_editable = False
        self.min_width = 4.0
        self.min_height = 4.0
        self._active_resize_handle = None

        self.default_pen = QPen(Qt.green)
        self.default_pen.setWidth(1)
        self.default_pen.setCosmetic(True)

        self.selected_pen = QPen(Qt.yellow)
        self.selected_pen.setWidth(1)
        self.selected_pen.setCosmetic(True)

        self.edit_pen = QPen(Qt.red)
        self.edit_pen.setWidth(1)
        self.edit_pen.setCosmetic(True)

        self.setPen(self.default_pen)
        self.setBrush(QBrush(Qt.NoBrush))

        self.setFlag(
            QGraphicsRectItem.ItemIsSelectable,
            True,
        )

        self.handles = {}
        self._create_handles()
        self.set_editable(False)
        self._update_handles()

    def _create_handles(self):

        handle_names = [
            "top_left",
            "top",
            "top_right",
            "right",
            "bottom_right",
            "bottom",
            "bottom_left",
            "left",
        ]

        for handle_name in handle_names:

            self.handles[handle_name] = BBoxHandleItem(
                handle_name,
                self,
            )
            self.handles[handle_name].hide()

    def _update_pen(self):

        if self.is_selected:
            self.setPen(self.selected_pen)
        elif self.is_editable:
            self.setPen(self.edit_pen)
        else:
            self.setPen(self.default_pen)

    def _update_handles(self):

        rect = self.rect()

        positions = {
            "top_left": QPointF(rect.left(), rect.top()),
            "top": QPointF(rect.center().x(), rect.top()),
            "top_right": QPointF(rect.right(), rect.top()),
            "right": QPointF(rect.right(), rect.center().y()),
            "bottom_right": QPointF(rect.right(), rect.bottom()),
            "bottom": QPointF(rect.center().x(), rect.bottom()),
            "bottom_left": QPointF(rect.left(), rect.bottom()),
            "left": QPointF(rect.left(), rect.center().y()),
        }

        for name, handle in self.handles.items():
            handle.setPos(positions[name])
            handle.setVisible(self.is_selected and self.is_editable)

    def _notify_geometry_changed(self):

        if self.geometry_changed_callback is not None:
            self.geometry_changed_callback(self.annotation)

    def request_selection(self):

        if self.selection_callback is not None:
            self.selection_callback(self)

    def begin_resize(self, handle_name):

        self._active_resize_handle = handle_name

    def end_resize(self):

        self._active_resize_handle = None

    def active_resize_handle(self):

        return self._active_resize_handle

    def set_selected_style(self, selected):

        self.is_selected = selected
        self._update_pen()
        self._update_handles()

    def sync_from_annotation(self):

        if self.annotation is None:
            return

        x, y, w, h = self.annotation["bbox"]
        self.setRect(x, y, w, h)
        self._update_pen()
        self._update_handles()

    def _apply_new_rect(self, left, top, right, bottom):

        width = right - left
        height = bottom - top

        self.setRect(left, top, width, height)

        if self.annotation is not None:
            self.annotation["bbox"] = [left, top, width, height]

        self._update_handles()
        self._notify_geometry_changed()

    def move_to(self, left, top):

        rect = self.rect()

        width = rect.width()
        height = rect.height()

        self._apply_new_rect(
            left,
            top,
            left + width,
            top + height,
        )

    def resize_from_handle(self, handle_name, scene_pos):

        rect = self.rect()

        left = rect.left()
        top = rect.top()
        right = rect.right()
        bottom = rect.bottom()

        x = scene_pos.x()
        y = scene_pos.y()

        if handle_name in ("top_left", "left", "bottom_left"):
            left = min(x, right - self.min_width)
        if handle_name in ("top_right", "right", "bottom_right"):
            right = max(x, left + self.min_width)
        if handle_name in ("top_left", "top", "top_right"):
            top = min(y, bottom - self.min_height)
        if handle_name in ("bottom_left", "bottom", "bottom_right"):
            bottom = max(y, top + self.min_height)

        self._apply_new_rect(left, top, right, bottom)

    def set_editable(self, editable):

        self.is_editable = editable

        self._update_pen()

        for handle in self.handles.values():
            handle.setVisible(self.is_selected and self.is_editable)