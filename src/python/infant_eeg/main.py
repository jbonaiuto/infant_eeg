import sys
from infant_eeg.stim import MovieStimulus

if sys.platform=='win32':
    import ctypes
    avbin_lib=ctypes.cdll.LoadLibrary('avbin')
    import psychopy.visual
from infant_eeg.distractors import DistractorSet
from psychopy import visual, core
import copy
import os
from psychopy import data, gui, event
from psychopy.visual import Window
from xml.etree import ElementTree as ET
import egi.threaded as egi
import numpy as np
from infant_eeg.tobii_controller import TobiiController
from infant_eeg.util import sendEvent, fixation_within_tolerance
from infant_eeg.config import MONITOR, SCREEN, NETSTATION_IP, DATA_DIR, CONF_DIR, EYETRACKER_NAME, \
    EYETRACKER_CALIBRATION_POINTS, EYETRACKER_DEBUG

class Experiment:
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """
    def __init__(self, exp_info, file_name):
        """
        file_name - name of XML file containing experiment definition
        """
        self.exp_info=exp_info
        self.name=None
        self.num_blocks=0
        self.blocks={}

        # Window to use
        wintype='pyglet' # use pyglet if possible, it's faster at event handling
        self.win = Window(
            [1280,1024],
            monitor=MONITOR,
            screen=SCREEN,
            units="deg",
            fullscr=True,
            #fullscr=False,
            color=[-1,-1,-1],
            winType=wintype)
        self.win.setMouseVisible(False)
        event.clearEvents()

        # Measure frame rate
        self.mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame=visual.getMsPerFrame(self.win, nFrames=60,
            showVisual=True)

        # Compute distractor duration in frames based on frame rate
        distractor_duration_frames=int(2000.0/self.mean_ms_per_frame)

        # Initialize set of distractors
        self.distractor_set=DistractorSet(os.path.join(DATA_DIR,'images','distractors','space'),
            os.path.join(DATA_DIR,'sounds','distractors'),
            os.path.join(DATA_DIR,'images','distractors','star-cartoon.jpg'),distractor_duration_frames, self.win)

        self.eye_tracker=None

        self.read_xml(file_name)

    def calibrate_eyetracker(self):
        retval = 'retry'
        while retval == 'retry':
            retval = self.eye_tracker.doCalibration(EYETRACKER_CALIBRATION_POINTS)
        if retval == 'abort':
            self.eye_tracker.closeDataFile()
            self.win.close()
            core.quit()

    def run(self, ns):
        """
        Run task
        ns - netstation connection
        """
        # Calibrate eyetracker
        if self.eye_tracker is not None:
            eyetracking_logfile=os.path.join(DATA_DIR,'logs','%s_%s_%s.log' % (self.exp_info['child_id'],
                                                                               self.exp_info['date'],
                                                                               self.exp_info['session']))
            self.eye_tracker.setDataFile(eyetracking_logfile, self.exp_info)
            self.calibrate_eyetracker()

        # Create random block order
        n_repeats=int(self.num_blocks/len(self.blocks.keys()))
        self.block_order=[]
        for i in range(n_repeats):
            subblock_order=copy.copy(self.blocks.keys())
            np.random.shuffle(subblock_order)
            self.block_order.extend(subblock_order)

        if self.eye_tracker is not None:
            self.eye_tracker.startTracking()

        for block_name in self.block_order:
            if self.distractor_set.run() and self.eye_tracker is not None:#
                self.eye_tracker.stopTracking()
                self.calibrate_eyetracker()
                self.eye_tracker.startTracking()

            if not self.blocks[block_name].run(ns, self.eye_tracker):
                break

            if self.eye_tracker is not None:
                self.eye_tracker.flushData()

        if self.eye_tracker is not None:
            self.eye_tracker.stopTracking()
            self.eye_tracker.closeDataFile()
            self.eye_tracker.destroy()

        self.win.close()
        core.quit()

    def read_xml(self, file_name):
        root_element=ET.parse(file_name).getroot()
        self.name=root_element.attrib['name']
        self.type=root_element.attrib['type']
        self.num_blocks=int(root_element.attrib['num_blocks'])
        if int(root_element.attrib['eyetracking'])>0:
            #Initialize eyetracker
            self.eye_tracker=TobiiController(self.win)
            self.eye_tracker.waitForFindEyeTracker()
            self.eye_tracker.activate(EYETRACKER_NAME)

        blocks_node=root_element.find('blocks')
        block_nodes=blocks_node.findall('block')
        for block_node in block_nodes:
            block_name=block_node.attrib['name']
            num_trials=int(block_node.attrib['num_trials'])
            min_iti_ms=float(block_node.attrib['min_iti'])
            max_iti_ms=float(block_node.attrib['max_iti'])

            # Compute delay in frames based on frame rate
            min_iti_frames=int(min_iti_ms/self.mean_ms_per_frame)
            max_iti_frames=int(max_iti_ms/self.mean_ms_per_frame)

            block=Block(block_name, num_trials, min_iti_frames, max_iti_frames, self.win)

            videos_node=block_node.find('videos')
            video_nodes=videos_node.findall('video')
            for video_node in video_nodes:
                movement=video_node.attrib['movement']
                actor=video_node.attrib['actor']
                file_name=video_node.attrib['file_name']
                block.stimuli.append(MovieStimulus(self.win, movement, actor, file_name))
            self.blocks[block_name]=block

class Block:
    """
    A block of movies of the same type
    """

    def __init__(self, name, trials, min_iti_frames, max_iti_frames, win):
        """
        code - code for block to send to netstation
        trials - number of trials to run
        min_delay_frames - minimum delay between movies in frames
        max_delay_frames - maximum delay between movies in frames
        win - psychopy window to use
        """
        self.code=name
        self.trials=trials
        self.win=win
        self.min_iti_frames=min_iti_frames
        self.max_iti_frames=max_iti_frames
        self.stimuli=[]

    def pause(self):
        event.clearEvents()
        self.win.flip()
        event.waitKeys()

    def run(self, ns, eyetracker):
        """
        Run the block
        ns - connection to netstation
        returns True if task should continue, False if should quit
        """
        # Compute trial order
        n_movies=len(self.stimuli)
        vid_order=range(n_movies)
        if n_movies<self.trials:
            vid_order=[]
            while len(vid_order)<self.trials:
                vid_order.extend(range(n_movies))
        np.random.shuffle(vid_order)

        # Start netstation recording
        sendEvent(ns, eyetracker, 'blk1', "block start", {'code' : self.code})

        for t in range(self.trials):
            if ns is not None:
                #ns.StartRecording()
                ns.sync()

            # Compute random delay period
            delay_frames=self.min_iti_frames+int(np.random.rand()*(self.max_iti_frames-self.min_iti_frames))

            # Reset movie to beginning
            video_idx=vid_order[t]
            self.stimuli[video_idx].reload(self.win)

            # clear any keystrokes before starting
            event.clearEvents()

            # Play movie
            self.win.callOnFlip(sendEvent, ns, eyetracker, 'mov1', 'movie start',
                                {'code' : self.code,
                                 'mvmt': self.stimuli[video_idx].movement,
                                 'actr' : self.stimuli[video_idx].actor})

            gaze=psychopy.visual.Circle(self.win,radius=1,fillColor=(1.0,0.0,0.0))
            while not self.stimuli[video_idx].stim.status==visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
                if eyetracker is not None and EYETRACKER_DEBUG:
                    gaze_position=eyetracker.getCurrentGazePosition()
                    mean_pos=(0.5*(gaze_position[0]+gaze_position[2]), 0.5*(gaze_position[1]+gaze_position[3]))
                    gaze.setPos(mean_pos)
                    if fixation_within_tolerance(gaze_position,(0,0),3,self.win):#
                        gaze.setFillColor((0.0,0.0,1.0))
                    else:
                        gaze.setFillColor((1.0,0.0,0.0))
                    gaze.draw()
                self.win.flip()

            all_keys=event.getKeys()

            # Tell netstation the movie has stopped
            sendEvent(ns, eyetracker, 'mov2', 'movie end', {})

            if len(all_keys):
                # Quit task
                if all_keys[0].upper() in ['Q','ESCAPE']:
                    return False
                # Pause block
                elif all_keys[0].upper()=='P':
                    self.pause()
                # End block
                elif all_keys[0].upper()=='E':
                    break
                event.clearEvents()

            # Black screen for delay
            for i in range(delay_frames):
                self.win.flip()

        # Stop netstation recording
        sendEvent(ns, eyetracker, 'blk2', 'block end', {'code' : self.code} )
        return True


if __name__=='__main__':
    # experiment parameters
    expInfo = {
        'child_id': '',
        'date': data.getDateStr(),
        'session': '',
        'diagnosis': '',
        'age': '',
        'gender': '',
        'experimenter_id': '',
    }

    #present a dialogue to change params
    dlg = gui.DlgFromDict(
        expInfo,
        title='Faces',
        fixed=['dateStr']
    )

    # connect to netstation
    ns = egi.Netstation()
    ms_localtime = egi.ms_localtime
    try:
        ns.initialize(NETSTATION_IP, 55513)
        ns.BeginSession()
        ns.StartRecording()
    except:
        print('Could not connect with NetStation!')
        ns=None

    # run task
    exp=Experiment(expInfo,os.path.join(CONF_DIR,'emotion_faces_experiment.xml'))
    exp.run(ns)

    # close netstation connection
    if ns:
        ns.StopRecording()
        ns.EndSession()
        ns.finalize()