import copy
import os
from psychopy import data, gui, visual, event, core
from psychopy.visual import Window
from twisted.python._epoll import ET
import egi
from infant_eeg.config import NETSTATION_IP, CONF_DIR, DATA_DIR, MONITOR, SCREEN, EYETRACKER_CALIBRATION_POINTS, EYETRACKER_NAME
from infant_eeg.distractors import DistractorSet
import numpy as np
from infant_eeg.tobii_controller import TobiiController

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
        self.preferential_gaze=None
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
            eyetracking_logfile=os.path.join(DATA_DIR,'eye_tracking','%s_%s_%s.log' % (self.exp_info['child_id'],
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

        self.preferential_gaze.run()

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

        preferential_gaze_node=root_element.find('preferential_gaze')
        preferential_gaze_duration=float(preferential_gaze_node.attrib['duration'])
        actor_nodes=preferential_gaze_node.findall('actor')
        actor_images=[]
        for actor_node in actor_nodes:
            actor_name=actor_node.attrib['name']
            filename=actor_node.attrib['file_name']
            actor_images.append(ActorImage(self.win, actor_name, filename))
        self.preferential_gaze=PreferentialGaze(actor_images, int(preferential_gaze_duration/self.mean_ms_per_frame))

        blocks_node=root_element.find('blocks')
        block_nodes=blocks_node.findall('block')
#        for block_node in block_nodes:
#            block_name=block_node.attrib['name']
#            num_trials=int(block_node.attrib['num_trials'])
#            min_iti_ms=float(block_node.attrib['min_iti'])
#            max_iti_ms=float(block_node.attrib['max_iti'])
#
#            # Compute delay in frames based on frame rate
#            min_iti_frames=int(min_iti_ms/self.mean_ms_per_frame)
#            max_iti_frames=int(max_iti_ms/self.mean_ms_per_frame)
#
#            block=Block(block_name, num_trials, min_iti_frames, max_iti_frames, self.win)
#
#            videos_node=block_node.find('videos')
#            video_nodes=videos_node.findall('video')
#            for video_node in video_nodes:
#                movement=video_node.attrib['movement']
#                actor=video_node.attrib['actor']
#                file_name=video_node.attrib['file_name']
#                block.stimuli.append(MovieStimulus(self.win, movement, actor, file_name))
#            self.blocks[block_name]=block


class ActorImage:

    def __init__(self, win, actor, filename):
        self.actor=actor
        self.filename=filename
        self.stim=visual.ImageStim(win, os.path.join(DATA_DIR,'images',self.filename))


class PreferentialGaze:

    def __init__(self, actors, duration_frames):
        self.actors=actors
        self.duration_frames=duration_frames

    def run(self):
        if np.random.rand()<0.5:
            self.actors[0].stim.pos=[-10,0]
            self.actors[1].stim.pos=[10,0]
        else:
            self.actors[0].stim.pos=[10,0]
            self.actors[1].stim.pos=[-10,0]
        # Black screen for delay
        for i in range(self.duration_frames):
            for actor in self.actors:
                self.actor.stim.draw()
            self.win.flip()

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
    exp=Experiment(expInfo,os.path.join(CONF_DIR,'gaze_experiment.xml'))
    exp.run(ns)

    # close netstation connection
    if ns:
        ns.StopRecording()
        ns.EndSession()
        ns.finalize()
