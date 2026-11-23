import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFrame

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()


        self.layout = QVBoxLayout()

        container = QFrame()
        container.setLayout(self.layout)

        # self.setFixedSize(400, 400)

        self.setCentralWidget(container)

    def create_interface(self, quant = 1):

        for i in range(quant):
            # 1. Create the box widget
            chassis_box = QFrame()
            chassis_box.setStyleSheet("""
                    QFrame {
                        background-color: #262a32;
                        border: 2px solid #5a626e;
                        border-radius: 6px;
                    }
                """)

            # 2. Give the box a layout so it holds items inside it
            box_layout = QVBoxLayout(chassis_box)
            box_layout.addWidget(QLabel("interface"))

            # 3. Add the box to your main window's layout
            self.layout.addWidget(chassis_box)


if __name__ == "__main__":
    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)

    # Create a Qt widget, which will be our window.
    window = MainWindow()

    MainWindow.create_interface(window, 3)
    # windows are hidden by default
    window.show()

    app.exec()
