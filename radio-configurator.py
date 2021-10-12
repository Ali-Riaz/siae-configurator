# Filename: radio-configurator.py

""" Simple Hello World example with PyQT5 """

import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QWidget

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