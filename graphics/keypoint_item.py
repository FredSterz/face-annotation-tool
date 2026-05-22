from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem


KEYPOINT_NAMES = [
    "left_eye",
    "right_eye",
    "nose",
    "left_mouth",
    "right_mouth",
]

KEYPOINT_COLORS = [
    QColor(0, 255, 255),
    QColor(255, 255, 0),
    QColor(0, 255, 0),
    QColor(255, 0, 255),
    QColor(0, 128, 255),
]


class KeypointItem(QGraphicsEllipseItem):

    def __init__(
        self,
        x,
        y,
        annotation,
        keypoint_index,
        radius=0.5,
        color=None,
        geometry_changed_callback=None,
    ):

        super().__init__(
            -radius,
            -radius,
            radius * 2,
            radius * 2,
        )

        self.annotation = annotation

        self.keypoint_index = keypoint_index
        self.base_color = color if color is not None else QColor("red")
        self.geometry_changed_callback = geometry_changed_callback
        self.is_highlighted = False
        self._suppress_geometry_notifications = True

        self.setPos(x, y)

        self.setBrush(
            QBrush(self.base_color)
        )

        self.setPen(
            QPen(Qt.NoPen)
        )

        self.setZValue(10)
        self.setFlag(
            QGraphicsEllipseItem.ItemSendsGeometryChanges,
            True,
        )

        # Initially locked
        self.radius = radius
        self.set_editable(False)
        self._suppress_geometry_notifications = False

    def set_radius(self, radius):

        self.radius = radius

        self.setRect(
            -radius,
            -radius,
            radius * 2,
            radius * 2,
        )

    def set_highlighted(self, highlighted):

        self.is_highlighted = highlighted

        if highlighted:
            pen = QPen(Qt.black)
            pen.setWidth(2)
            pen.setCosmetic(True)
            self.setPen(pen)
            self.setZValue(11)
        else:
            self.setPen(QPen(Qt.NoPen))
            self.setZValue(10)

    def set_editable(self, editable):

        self.setFlag(
            QGraphicsEllipseItem.ItemIsMovable,
            editable,
        )

        self.setBrush(
            QBrush(self.base_color)
        )

    def itemChange(self, change, value):

        if (
            change
            == QGraphicsEllipseItem.ItemPositionChange
        ):

            x = value.x()

            y = value.y()

            kp_offset = (
                self.keypoint_index * 3
            )

            self.annotation[
                "keypoints"
            ][kp_offset] = x

            self.annotation[
                "keypoints"
            ][kp_offset + 1] = y

            if (
                not self._suppress_geometry_notifications
                and self.geometry_changed_callback is not None
            ):
                self.geometry_changed_callback(
                    self.annotation
                )

        return super().itemChange(
            change,
            value,
        )