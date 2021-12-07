# Filename: radio-configurator.py

""" Simple Hello World example with PyQT5 """

import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtWidgets import QToolBar


class Window(QMainWindow):
	"""Main Window."""
	def __init__(self, parent=None):
		"""Initializer. Declaring that the Window class inherits from QMainWindow class."""
		super().__init__(parent)
		self.setWindowTitle('QMainWindow')
		self.setCentralWidget(QLabel("I'm the Central Widget"))
		self._createMenu()
		self._createToolBar()
		self._createStatusBar()


	def _createMenu(self):
		self.menu = self.menuBar().addMenu("&Menu")
		self.menu.addAction("&Exit", self.close)


	def _createToolBar(self):
		tools = QToolBar()
		self.addToolBar(tools)
		tools.addAction('Exit', self.close)


	def _createStatusBar(self):
		status = QStatusBar()
		status.showMessage("I'm the Status Bar")
		self.setStatusBar(status)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	win = Window()
	win.show()
	sys.exit(app.exec())


'''
app = QApplication([]) #Use sys.argv if you want to pass command-line arguments to script
window = QWidget()
window.setWindowTitle('PyQt5 App w/ QHBoxLayout')

helloMsg = QLabel('<h1>Hello World!</h1>')

layout = QHBoxLayout()							#QHBoxLayout, QVBoxLayout, QGridLayout, QFromLayout
layout.addWidget(QPushButton('OK'))
layout.addWidget(helloMsg)
layout.addWidget(QPushButton('OK'))
window.setLayout(layout)

window.show()
sys.exit(app.exec_())
'''