import sys

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Widgets App")

        layout = QVBoxLayout()
        widgets = [
            QCheckBox,
            QComboBox,
            QDateEdit,
            QDateTimeEdit,
            QDial,
            QDoubleSpinBox,
            QFontComboBox,
            QLCDNumber,
            QLabel,
            QLineEdit,
            QProgressBar,
            QPushButton,
            QRadioButton,
            QSlider,
            QSpinBox,
            QTimeEdit,
        ]

        for widget in widgets:
            layout.addWidget(widget())

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        def btn_click(self):
            print("Button Pressed")

        def button_toggle(self, checked):
            print("Toggled?", checked)

        def mouseMoveEvent(self, e):
            self.label.setText("mouseMoveEvent")

        def mousePressEvent(self, e):
            self.label.setText("mousePressEvent")

        def mouseReleaseEvent(self, e):
            self.label.setText("mouseReleaseEvent")

        def mouseDoubleClickEvent(self, e):
            self.label.setText("mouseDoubleClickEvent")

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()