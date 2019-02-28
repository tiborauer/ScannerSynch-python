import math
import sys
from time import time
from multiprocessing import Process, Value, Array

import pyniexp.utils as utils

try:
    import nidaqmx
except ImportError:
    print('WARNING: nidaqmx module is not available --> ', end='')
    print('You can run ScannerSynch only in emulation mode')

try:
    import pyniexp.kbutils as kbutils
except ImportError:
    print('WARNING: kbutils module is not available --> ', end='')
    print('You cannot emulate buttons')

MAX_SIGNAL = 1000

#### Emulation class for DAQ
class simDAQ:

    ## Properies
    di_channels = []

#### Main class
class scanner_synch:
    
    ## Properties 
    # Private constants
    _button_list_LT = (1, 2, 4, 8) # Lumitouch Photon Control (1 hand, 4 buttons)
    _button_list_NATA = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39) # NATA (2 hands, 10 buttons)

    # Public properties
    buttonbox_timeout = math.inf # second (timeout for WaitForButtonPress)
    is_inverted = False

    # Public read-only properties
    __emul_synch = False
    @property
    def emul_synch(self):
        return self.__emul_synch   
    __emul_buttons = False
    @property
    def emul_buttons(self):
        return self.__emul_buttons   

    # Private properties
    __DAQ = None
    __Kb = None
        
    __t0 = Value('d',time()) # internal timer
        
    __buttonbox_readout = False
    __process = Process()
    
    __readout_time = [0] # sec to store data before refresh 1*n
    @property
    def readout_time(self):
        return self.__readout_time
        
    __isDAQ = 'nidaqmx' in sys.modules
    __isKb = 'pyniexp.kbutils' in sys.modules # Button emulation (keyboard)

    # Dependent properties
    @property
    def is_valid(self):
        valid = True
        valid = valid and (not(self.__DAQ is None)) and (not(self.emul_buttons) or (self.emul_buttons and self.__isKb))
        if self.emul_synch and not(self.TR):
            print('Emulation: Scanner synch pulse is not in use --> ', end='')
            print('You need to set TR!')
            valid = valid and False
        if self.emul_buttons and not(len(self.buttons)):
            print('Emulation: Buttonbox is not in use           --> ', end='')
            print('You need to set Buttons!')
            valid = valid and False
        
        if not(valid): print('WARNING: Scanner Synch is not open!')

        return valid

    ## Constructor
    def __init__(self,emul_synch=False,emul_buttons=False):
        DEV = 'Dev1'

        print('Initialising Scanner Synch...')
        self.__emul_synch = emul_synch
        self.__emul_buttons = emul_buttons

        # test environment
        try:
            D = nidaqmx.system.System.local().devices
            D = [d for d in D if d.name == DEV]
            D = D[0]
            D.self_test_device()
        except:
            print('WARNING: ', sys.exc_info()[0])
            self.__isDAQ = False

        self.start_process()

    ## Destructor
    def __del__(self):
        print('Scanner Synch is closing...')
        if self.__process.is_alive():
            self.__process.terminate()
        if self.__isDAQ and not(self.__DAQ is None):
            self.__DAQ.close()
        
        if self.__Kb:
            self.__Kb.stop()

        print('Done')

    ## Utils
    def start_process(self,max_pulses=MAX_SIGNAL):
        print('Starting process...')
        if not(self.is_valid): 
            print('You have to start the process manually by calling <object>.start_process()!')
            return
        if self.__process.is_alive():
            self.__process.terminate()
        self._time_of_synch_pulses = Array('d', [float(math.nan)]*max_pulses)
        self._state_of_buttonpresses = Array('d', [float(math.nan)]*self.number_of_buttons)
        self._time_of_buttonpresses = [Array('d', [float(math.nan)]*max_pulses) for n in range(0,self.number_of_buttons)]
        self.__readout_time = [self.__readout_time[0]] + [self.__readout_time[1]]*self.number_of_buttons
        self.__process = Process(target=self._run)
        self.__process.start()
        print('Done')

    @property
    def clock(self):
        return time() - self.__t0

    def reset_clock(self):
        self.__t0.value = time()

    __TR = 0    # emulated pulse frequency
    @property
    def TR(self):
        return self.__TR

    @TR.setter
    def TR(self,val):
        if self.__process.is_alive():
            self.__process.terminate()
        
        self.__TR = val

    __buttons = []
    @property
    def buttons(self):
        return self.__buttons

    @buttons.setter
    def buttons(self,val):
        if self.__isKb:
            if self.__process.is_alive():
                self.__process.terminate()
                
            kbutils.kbLayout
            if not all(utils.ismember(val,kbutils.kbLayout)):
                print('WARNING: Some buttons are not recognised in...')
                print(kbutils.kbLayout)
                return

            self.__buttons = val
            self.__readout_time = [self.__readout_time[0]] + [self.__readout_time[1]]*(self.number_of_buttons)

        else:
            print('WARNING: "kbutils" is not available')
    
    @property
    def number_of_buttons(self):
        if self.emul_buttons: return len(self.buttons)
        else: return len(self._button_list_LT)+len(self._button_list_NATA)

    ## Scanner Pulse
    @property
    def synch_count(self):
        return sum([not(math.isnan(i)) for i in self._time_of_synch_pulses])

    def reset_synch_count(self,max_pulses=MAX_SIGNAL):
        self.start_process(max_pulses)

    def set_synch_readout_time(self,t):
        self.__readout_time[0] = t
    
    def wait_for_synch(self):
        pass
    
    ## Buttons
    def set_button_readout_time(self,t):
        self.__readout_time = [self.__readout_time[0]] + [t]*(len(self.__readout_time)-1)
        self.__buttonbox_readout = False
    
    @property
    def _last_button_indices(self):
        ind = [None]*self.number_of_buttons
        for n in range(0,self.number_of_buttons):
            i = sum([not(math.isnan(i)) for i in self._time_of_buttonpresses[n]])
            if i > 0: ind[n] = i-1

    def set_buttonbox_readout_time(self,t):
        self.__readout_time = [self.__readout_time[0]] + [t]*(len(self.__readout_time)-1)
        self.__buttonbox_readout = True

    def wait_for_buttonpress(self,timeout=None,ind_button=None):
        pass

    def wait_for_buttonrelease(self,timeout=None,ind_button=None):
        pass

    ## Low level methods
    def _run(self):
        # Start DAQ
        if not(self.emul_synch) and self.__isDAQ:
            self.__DAQ = nidaqmx.Task()
            # Add channels for scanner pulse
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line0') # manual
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line1') # scanner
            # Add channels for Lumitouch
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line2')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line3')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line4')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line5')
            # Add channels for NATA
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line0')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line1')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line2')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line3')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line4')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line5')
        else:
            self.__isDAQ = False
            self.__emul_synch = True
            self.__emul_buttons = True
                
            self.__DAQ = simDAQ()
            self.__DAQ.di_channels = range(1, 1+len(self.__buttons) +1)

            print('')
            print('WARNING: DAQ card is not in use!')
        
        # Start KB
        if self.emul_buttons: self.__Kb = kbutils.Kb()
    
        self.reset_clock()
    
        while True:
            t = self.clock

            # get data
            if self.__isDAQ:
                data = [self.is_inverted^d for d in self.__DAQ.read()]
                data[0] = any(data[0:2]); del(data[1])
                data[2] = False # CAVE - Lumitouch: button two is not working
                if all([data[i] for i in [1, 3, 4]]): # CAVE - Lumitouch: random signal on all channels
                    for i in range(1,5): data[i] = False
    #             for i in range(1,5): data[i] = False # TEMP: Lumitouch not connected
    #             for i in range(5,11): data[i] = False # TEMP: NATA not connected
            else:
                data = [0] * len(self.__DAQ.di_channels)

            data = [data[0]] + [utils.binvec2dec(data[1:5]) == b for b in self._button_list_LT] + [utils.binvec2dec(data[5:11]) == b for b in self._button_list_NATA]

            # scanner synch pulse emulation
            if self.emul_synch and self.TR:
                data[0] = (not self.synch_count) or (t-self._time_of_synch_pulses[self.synch_count-1] >= self.TR)
    
            # button press emulation (keyboard)
            if self.emul_buttons:
                nbuttons = len(self.buttons)
                if self.__isKb and nbuttons:
                    kbdata = self.__Kb.kbCheck(); keyCode = [k[0] for k in kbdata if k[1] == 'down']
                    data = [data[0]] + utils.ismember(self.buttons,keyCode)

            #if self.__buttonbox_readout: 
            #    self.__TOA = [self.__TOA[0]] + [max(self.__TOA[1:len(self.__TOA)])] * (len(self.__TOA)-1)
            #ind = [t-self.__TOA[i] > self.__ReadoutTime[i] for i in range(0,len(self.__ReadoutTime))]
            #self.__Datap = self.__Data
            #self.__Data = [data[i] if ind[i] else self.__Data[i] for i in range(0,len(self.__Data))]
            #self.__TOAp = self.__TOA
            #self.__TOA = [t if self.__Data[i] else self.__TOA[i] for i in range(0,len(self.__TOA))]