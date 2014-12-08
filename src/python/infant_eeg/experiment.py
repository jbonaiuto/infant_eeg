import copy
import sys
# Import AVbin first
if sys.platform == 'win32':
    import ctypes
    avbin_lib = ctypes.cdll.LoadLibrary('avbin')
    import psychopy.visual
from psychopy.visual import Window
from psychopy import visual, core, event
import numpy as np
import egi.threaded as egi
# Try to import tobii sdk
try:
    from infant_eeg.tobii_controller import TobiiController
except:
    pass
from infant_eeg.distractors import DistractorSet
from infant_eeg.config import *


class Experiment:
    """
    Base experiment class
    """

    def __init__(self, exp_info, file_name):
        """
        Initialize experiment - read XML file, setup window, connect to netstation and tobii
        exp_info - experiment information
        file_name - name of XML file containing experiment definition
        """
        self.exp_info = exp_info
        self.name = None
        self.type = None
        self.num_blocks = 0
        self.blocks = {}
        self.block_order = []

        # Window to use
        wintype = 'pyglet'  # use pyglet if possible, it's faster at event handling
        self.win = Window(
            [1280, 1024],
            monitor=MONITOR,
            screen=SCREEN,
            units="deg",
            fullscr=True,
            color=[-1, -1, -1],
            winType=wintype)
        self.win.setMouseVisible(False)
        event.clearEvents()

        # Measure frame rate
        self.mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame = visual.getMsPerFrame(self.win, nFrames=60,
                                                                                             showVisual=True)

        # Compute distractor duration in frames based on frame rate
        distractor_duration_frames = int(2000.0/self.mean_ms_per_frame)

        # Initialize set of distractors
        self.distractor_set = DistractorSet(os.path.join(DATA_DIR, 'images', 'distractors', 'space'),
                                            os.path.join(DATA_DIR, 'sounds', 'distractors'),
                                            os.path.join(DATA_DIR, 'images', 'distractors', 'star-cartoon.jpg'),
                                            distractor_duration_frames, self.win)

        # Connect to nestation
        self.ns = None
        if exp_info['eeg']:
            # connect to netstation
            self.ns = egi.Netstation()
            ms_localtime = egi.ms_localtime

        self.eye_tracker = None
        self.mouse = None
        if exp_info['eyetracking source'] == 'tobii':
            # Initialize eyetracker
            self.eye_tracker = TobiiController(self.win)
            self.eye_tracker.waitForFindEyeTracker()
            self.eye_tracker.activate(EYETRACKER_NAME)
        elif exp_info['eyetracking source'] == 'mouse':
            # Initialize mouse
            self.mouse = event.Mouse(win=self.win)

        self.read_xml(file_name)

    def calibrate_eyetracker(self):
        """
        Run eyetracker calibration routine
        """
        retval = 'retry'
        while retval == 'retry':
            retval = self.eye_tracker.doCalibration(EYETRACKER_CALIBRATION_POINTS)
        if retval == 'abort':
            self.eye_tracker.closeDataFile()
            self.eye_tracker.destroy()
            self.win.close()
            core.quit()

    def initialize(self):
        """
        Start netstation recording, calibrate eyetracker
        """
        if self.ns is not None:
            try:
                self.ns.initialize(NETSTATION_IP, 55513)
                self.ns.BeginSession()
                self.ns.StartRecording()
            except:
                print('Could not connect with NetStation!')

        # Calibrate eyetracker
        if self.eye_tracker is not None:
            eyetracking_logfile = os.path.join(DATA_DIR, 'logs', '%s_%s_%s.log' % (self.exp_info['child_id'],
                                                                                   self.exp_info['date'],
                                                                                   self.exp_info['session']))
            self.eye_tracker.setDataFile(eyetracking_logfile, self.exp_info)
            self.calibrate_eyetracker()

        # Create random block order
        n_repeats = int(self.num_blocks/len(self.blocks.keys()))
        for i in range(n_repeats):
            subblock_order = copy.copy(self.blocks.keys())
            np.random.shuffle(subblock_order)
            self.block_order.extend(subblock_order)

        if self.eye_tracker is not None:
            self.eye_tracker.startTracking()

    def close(self):
        """
        Disconnect from eyetracker and netstation
        """
        if self.eye_tracker is not None:
            self.eye_tracker.stopTracking()
            self.eye_tracker.closeDataFile()

        # close netstation connection
        if self.ns:
            self.ns.StopRecording()
            self.ns.EndSession()
            self.ns.finalize()

        self.win.close()
        core.quit()
        if self.eye_tracker is not None:
            self.eye_tracker.destroy()

    def run(self):
        """
        Run task
        ns - netstation connection
        """
        pass

    def read_xml(self, file_name):
        """
        Read experiment definition file
        :param file_name: file to read definition from
        """
        pass
