import os, sys

import pyniexp
from pyniexp.stimulation import Waveform, Stimulator
from pyniexp.utils import Status

from numpy import arange, zeros

from PyQt5 import QtWidgets, QtCore, uic
import pyqtgraph as pg

class StimulatorDlg(QtWidgets.QWidget):
    _stimulator = None
    _plot = [None, None]
    _waves = [None, None]

    def __init__(self):
        super().__init__(parent=None, flags=QtCore.Qt.Window)
        uic.loadUi(os.path.join(list(pyniexp.__path__)[0],'stimulatordlg.ui'), self)    

        configFile = None
        if os.path.exists('config_stimulation.json'):
            configFile = 'config_stimulation.json'
        self.loadConfig(configFile)

        for i in [0, 1]:
            self._plot[i] = pg.PlotWidget(self)
            self._plot[i].setBackground((255, 255, 255))
            self.__getattribute__("plChannel{:d}".format(i+1)).addWidget(self._plot[i])
            p = self._plot[i].getPlotItem()
            p.setLabel('bottom',"Time [s]")
            p.setLabel('left', "Current [mA]")
            p.setMenuEnabled(enableMenu=False)
            p.setMouseEnabled(x=False, y=False)
            p.showGrid(x=True, y=True, alpha=1)
            p.installEventFilter(self)
            p.disableAutoRange(axis=pg.ViewBox.YAxis)
            p.disableAutoRange(axis=pg.ViewBox.XAxis)
            p.plot(x=arange(0,1,1/1000),
                y=zeros(1000),
                pen=pg.mkPen(color='r', width=2))

        self.cbStimType.currentTextChanged.connect(self.updateDlg)

        self.sbIntensity1.valueChanged.connect(self.updatePlots)
        self.sbIntensity2.valueChanged.connect(self.updatePlots)
        self.sbFrequency1.valueChanged.connect(self.updatePlots)
        self.sbFrequency2.valueChanged.connect(self.updatePlots)
        self.sbPhase1.valueChanged.connect(self.updatePlots)
        self.sbPhase2.valueChanged.connect(self.updatePlots)
        self.sbDuration.valueChanged.connect(self.updatePlots)
        self.sbRampUp.valueChanged.connect(self.updatePlots)
        self.sbRampDown.valueChanged.connect(self.updatePlots)
        self.sbSamplingRate.valueChanged.connect(self.updatePlots)

        self.btnLoadConfig.clicked.connect(lambda: self.loadConfig(None))
        self.btnLoadWaves.clicked.connect(self.loadWaves)
        self.btnRun.clicked.connect(self.run)
        self.btnStop.clicked.connect(self.stop)
        
        self.updateDlg()
        self.updatePlots()

        self.setWindowTitle("Stimulator")
        self.show()

    def closeEvent(self, event):
        self.hide()
        self._stimulator = None

    def loadConfig(self,configFile=None):
        if configFile is None:
            configFile = QtWidgets.QFileDialog.getOpenFileName(
                    caption="Select 'Configuration JSON file'", filter='ini files (*.json)')[0]
        self._stimulator = None
        self._stimulator = Stimulator(configFile)
        self.lblStatus.setText(self._stimulator.status.name)
        if self._stimulator.status.value > 0: self.btnLoadWaves.setEnabled(True)

    def loadWaves(self):
        self._stimulator.loadWaveform(self._waves)
        self.btnRun.setEnabled(True)

    def run(self):
        self._stimulator.stimulate()
        self.btnStop.setEnabled(True)

    def stop(self):
        self._stimulator.stop()

    def updateDlg(self):
        if self.cbStimType.currentText() == 'Dual-channel':
            chs = [True, True]
        else:
            chs = [False, False]
            chs[int(self.cbStimType.currentText()[-1:])-1] = True
        self.setChannel(chs)

    def updatePlots(self):
        self._waves[0] = Waveform(amplitude = self.sbIntensity1.value(), frequency = self.sbFrequency1.value(), phase=self.sbPhase1.value(), 
            duration = self.sbDuration.value(), rampUp = self.sbRampUp.value(), rampDown = self.sbRampDown.value(), 
            samplingRate = self.sbSamplingRate.value())
        self._waves[1] = Waveform(amplitude = self.sbIntensity2.value(), frequency = self.sbFrequency2.value(), phase=self.sbPhase2.value(), 
            duration = self.sbDuration.value(), rampUp = self.sbRampUp.value(), rampDown = self.sbRampDown.value(), 
            samplingRate = self.sbSamplingRate.value())

        for i in [0,1]:
            self._plot[i].getPlotItem().dataItems[0].setData(arange(0,self._waves[i].duration,1/self._waves[i].samplingRate),
                self._waves[i].signal)
            self._plot[i].getPlotItem().setXRange(0, self._waves[i].duration, padding=0.0)
            self._plot[i].getPlotItem().setYRange(-self._waves[i].amplitude*2, self._waves[i].amplitude*2, padding=0.0)

        self.progressBar.setMaximum(self._waves[0].duration*1000)
        self.progressBar.setValue(0)

    def setChannel(self,isVisible=[0,0]):
        for i in range(len(isVisible)):
            self._plot[i].setVisible(isVisible[i])
            self.__getattribute__("lblFrequency{:d}".format(i+1)).setVisible(isVisible[i])
            self.__getattribute__("sbFrequency{:d}".format(i+1)).setVisible(isVisible[i])
            self.__getattribute__("lblPhase{:d}".format(i+1)).setVisible(isVisible[i])
            self.__getattribute__("sbPhase{:d}".format(i+1)).setVisible(isVisible[i])
            self.__getattribute__("lblIntensity{:d}".format(i+1)).setVisible(isVisible[i])
            self.__getattribute__("sbIntensity{:d}".format(i+1)).setVisible(isVisible[i])

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('Stimulator')
    app.setOrganizationName('PyNIExp')
    app.setApplicationVersion('1.0')

    window = StimulatorDlg()
    
    app.exec_()