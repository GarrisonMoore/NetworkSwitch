from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, Qt
from PySide6.QtCore import QPoint
from GUI.Port import PortWidget

LED_ACTIVE = "#00ff00"  # Bright green traffic LED
ACCENT_WAN = "#d97706"  # Amber / orange WAN stripe
CABLE_STANDBY = "#38bdf8"  # Cyan connected-but-disabled wire



class CableOverlay(QWidget):
    def __init__(self, parent_container: QWidget, cables_ref: list):
        super().__init__(parent_container)
        self.cables = cables_ref
        self.drag_start_widget: PortWidget | None = None
        self.drag_cursor_pos: QPoint | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _draw_bezier_cable(self, painter: QPainter, p1: QPoint, p2: QPoint, color: QColor):
        dx = abs(p2.x() - p1.x())
        sag = max(40.0, dx * 0.25)

        path = QPainterPath()
        path.moveTo(p1)
        ctrl1_x = p1.x() + (p2.x() - p1.x()) * 0.35
        ctrl2_x = p1.x() + (p2.x() - p1.x()) * 0.65
        path.cubicTo(ctrl1_x, p1.y() + sag, ctrl2_x, p2.y() + sag, p2.x(), p2.y())

        # Dark outer insulation + colored inner wire
        painter.setPen(QPen(QColor("#0d0e11"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        painter.setPen(QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

    def paintEvent(self, event):
        if not self.cables and not self.drag_start_widget:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw all permanent connected cables
        for src_widget, dst_widget, cable in self.cables:
            p1 = src_widget.mapTo(self.parentWidget(), src_widget.rect().center())
            p2 = dst_widget.mapTo(self.parentWidget(), dst_widget.rect().center())
            color = QColor(LED_ACTIVE if cable.source_jack.enabled else CABLE_STANDBY)
            self._draw_bezier_cable(painter, p1, p2, color)

        # 2. Draw live amber preview wire while holding left mouse button
        if self.drag_start_widget and self.drag_cursor_pos:
            p1 = self.drag_start_widget.mapTo(self.parentWidget(), self.drag_start_widget.rect().center())
            p2 = self.parentWidget().mapFromGlobal(self.drag_cursor_pos)
            self._draw_bezier_cable(painter, p1, p2, QColor(ACCENT_WAN))
