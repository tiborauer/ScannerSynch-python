import sys
from PyQt5.QtWidgets import QApplication
from pyniexp.stimulatordlg import StimulatorApp

app = QApplication(sys.argv)
app.setApplicationName('Stimulator')
app.setOrganizationName('PyNIExp')
app.setApplicationVersion('1.0')

stimdlg = StimulatorApp()

app.exec_()