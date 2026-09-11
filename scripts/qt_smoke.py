from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


app = QApplication([])
print("Qt GUI runtime OK", QIcon, app.applicationName())
