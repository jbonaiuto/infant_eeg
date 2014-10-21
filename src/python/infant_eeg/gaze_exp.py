import copy
import os
from psychopy import data, gui, visual, event, core
import psychopy
from psychopy.visual import Window
from xml.etree import ElementTree as ET
import egi.threaded as egi
from infant_eeg.config import NETSTATION_IP, CONF_DIR, DATA_DIR, MONITOR, SCREEN, EYETRACKER_CALIBRATION_POINTS, \
    EYETRACKER_NAME, \
    EYETRACKER_DEBUG
from infant_eeg.distractors import DistractorSet
import numpy as np
from infant_eeg.stim import MovieStimulus
from infant_eeg.tobii_controller import TobiiController
from infant_eeg.util import sendEvent, fixation_within_tolerance


class Experiment:
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """

    def __init__(self, exp_info, file_name):
        """
        file_name - name of XML file containing experiment definition
        """
        self.exp_info = exp_info
        self.name = None
        self.preferential_gaze = None
        self.num_blocks = 0
        self.blocks = {}
        self.congruent_actor = None
        self.incongruent_actor = None

        # Window to use
        wintype = 'pyglet'  # use pyglet if possible, it's faster at event handling
        self.win = Window(
            [1280, 1024],
            monitor=MONITOR,
            screen=SCREEN,
            units="deg",
            fullscr=True,
            # fullscr=False,
            color=[-1, -1, -1],
            winType=wintype)
        self.win.setMouseVisible(False)
        event.clearEvents()

        # Measure frame rate
        self.mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame = visual.getMsPerFrame(self.win, nFrames=60,
                                                                                             showVisual=True)

        # Compute distractor duration in frames based on frame rate
        distractor_duration_frames = int(2000.0 / self.mean_ms_per_frame)

        # Initialize set of distractors
        self.distractor_set = DistractorSet(os.path.join(DATA_DIR, 'images', 'distractors', 'space'),
                                            os.path.join(DATA_DIR, 'sounds', 'distractors'),
                                            os.path.join(DATA_DIR, 'images', 'distractors', 'star-cartoon.jpg'),
                                            distractor_duration_frames, self.win)

        self.eye_tracker = None

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
            eyetracking_logfile = os.path.join(DATA_DIR, 'logs', '%s_%s_%s.log' % (self.exp_info['child_id'],
                                                                                   self.exp_info['date'],
                                                                                   self.exp_info['session']))
            self.eye_tracker.setDataFile(eyetracking_logfile, self.exp_info)
            self.calibrate_eyetracker()

        # Create random block order
        n_repeats = int(self.num_blocks / len(self.blocks.keys()))
        self.block_order = []
        for i in range(n_repeats):
            subblock_order = copy.copy(self.blocks.keys())
            np.random.shuffle(subblock_order)
            self.block_order.extend(subblock_order)

        if self.eye_tracker is not None:
            self.eye_tracker.startTracking()

        self.preferential_gaze.run(ns, self.eye_tracker)

        for block_name in self.block_order:
            if self.distractor_set.run() and self.eye_tracker is not None:
                self.eye_tracker.stopTracking()
                self.calibrate_eyetracker()
                self.eye_tracker.startTracking()

            if not self.blocks[block_name].run(ns, self.eye_tracker):
                break

            if self.eye_tracker is not None:
                self.eye_tracker.flushData()

        self.preferential_gaze.run(ns, self.eye_tracker)

        if self.eye_tracker is not None:
            self.eye_tracker.stopTracking()
            self.eye_tracker.closeDataFile()
            self.eye_tracker.destroy()

        self.win.close()
        core.quit()

    def read_xml(self, file_name):
        root_element = ET.parse(file_name).getroot()
        self.name = root_element.attrib['name']
        self.type = root_element.attrib['type']
        self.num_blocks = int(root_element.attrib['num_blocks'])
        if int(root_element.attrib['eyetracking']) > 0:
            # Initialize eyetracker
            self.eye_tracker = TobiiController(self.win)
            self.eye_tracker.waitForFindEyeTracker()
            self.eye_tracker.activate(EYETRACKER_NAME)

        preferential_gaze_node = root_element.find('preferential_gaze')
        preferential_gaze_duration = float(preferential_gaze_node.attrib['duration'])
        actor_nodes = preferential_gaze_node.findall('actor')
        actor_images = []
        for actor_node in actor_nodes:
            actor_name = actor_node.attrib['name']
            filename = actor_node.attrib['file_name']
            actor_images.append(ActorImage(self.win, actor_name, filename))
        self.preferential_gaze = PreferentialGaze(self.win, actor_images,
                                                  int(preferential_gaze_duration / self.mean_ms_per_frame))
        if np.random.rand() < 0.5:
            self.congruent_actor = actor_images[0].actor
            self.incongruent_actor = actor_images[1].actor
        else:
            self.congruent_actor = actor_images[1].actor
            self.incongruent_actor = actor_images[0].actor
        self.exp_info['congruent_actor']=self.congruent_actor
        self.exp_info['incongruent_actor']=self.incongruent_actor

        blocks_node = root_element.find('blocks')
        block_nodes = blocks_node.findall('block')
        for block_node in block_nodes:
            block_name = block_node.attrib['name']
            num_trials = int(block_node.attrib['num_trials'])
            init_stim_ms = float(block_node.attrib['init_stim'])
            min_attending_ms = float(block_node.attrib['min_attending'])
            min_iti_ms = float(block_node.attrib['min_iti'])
            max_iti_ms = float(block_node.attrib['max_iti'])

            # Compute delay in frames based on frame rate
            init_stim_frames = int(init_stim_ms / self.mean_ms_per_frame)
            min_attending_frames = int(min_attending_ms / self.mean_ms_per_frame)
            min_iti_frames = int(min_iti_ms / self.mean_ms_per_frame)
            max_iti_frames = int(max_iti_ms / self.mean_ms_per_frame)

            block = Block(block_name, num_trials, init_stim_frames, min_iti_frames, max_iti_frames, self.win)

            videos_node = block_node.find('videos')
            video_nodes = videos_node.findall('video')
            for video_node in video_nodes:
                direction = video_node.attrib['direction']
                actor = video_node.attrib['actor']
                file_name = video_node.attrib['file_name']
                init_frame = video_node.attrib['init_frame']
                if not actor in block.videos:
                    block.videos[actor] = {}
                    block.video_init_frames[actor] = {}
                block.videos[actor][direction] = MovieStimulus(self.win, direction, actor, file_name)
                block.video_init_frames[actor][direction] = visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images',
                                                                                                    init_frame),
                                                                             units='pix', size=(900, 720))
            trials_node = block_node.find('trials')
            trial_nodes = trials_node.findall('trial')
            for trial_node in trial_nodes:
                code = trial_node.attrib['code']
                left_image = trial_node.attrib['left_image']
                right_image = trial_node.attrib['right_image']
                attention = trial_node.attrib['attention']
                gaze = trial_node.attrib['gaze']
                actor = None
                if gaze == 'cong':
                    actor = self.congruent_actor
                else:
                    actor = self.incongruent_actor
                trial = Trial(self.win, code, init_stim_frames, min_attending_frames, left_image, right_image, attention, gaze, actor)
                if trial.gaze == 'cong':
                    trial.init_frame = block.video_init_frames[self.congruent_actor][trial.attention]
                    trial.video_stim = block.videos[self.congruent_actor][trial.attention]
                else:
                    if trial.attention == 'l':
                        trial.init_frame = block.video_init_frames[self.incongruent_actor]['r']
                        trial.video_stim = block.videos[self.incongruent_actor]['r']
                    else:
                        trial.init_frame = block.video_init_frames[self.incongruent_actor]['l']
                        trial.video_stim = block.videos[self.incongruent_actor]['l']
                block.trials.append(trial)
            self.blocks[block_name] = block


class Trial:
    def __init__(self, win, code, init_stim_frames, min_attending_frames, left_image, right_image, attention, gaze, actor):
        self.win = win
        self.code = code
        self.init_stim_frames = init_stim_frames
        self.min_attending_frames = min_attending_frames
        self.images = {}
        self.images['l'] = visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images', left_image))
        self.images['l'].pos = [-20, 0]
        self.images['r'] = visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images', right_image))
        self.images['r'].pos = [20, 0]
        self.highlight = visual.Rect(self.win, width=self.images['l'].size[0] + 1, height=self.images['r'].size[1] + 1)
        self.highlight.lineColor = [1, 1, 0]
        self.highlight.lineWidth = 5
        self.attention = attention
        self.gaze = gaze
        self.init_frame = None
        self.video_stim = None
        self.actor = actor

    def run(self, ns, eyetracker):
        # Reset movie to beginning
        self.video_stim.reload(self.win)

        # Show stim
        self.win.callOnFlip(sendEvent, ns, eyetracker, 'ima1', 'stim start',
                            {'code': self.code,
                             'attn': self.attention,
                             'gaze': self.gaze,
                             'actr': self.actor})
        for i in range(self.init_stim_frames):
            self.init_frame.draw()
            for image in self.images.values():
                image.draw()
            self.win.flip()

        self.highlight.pos = self.images[self.attention].pos

        attending_frames = 0
        idx = 0
        self.win.callOnFlip(sendEvent, ns, eyetracker, 'ima2', 'attn start',
                            {'code': self.code,
                             'attn': self.attention,
                             'gaze': self.gaze,
                             'actr': self.actor})
        while attending_frames < self.min_attending_frames:
            if eyetracker is not None and EYETRACKER_DEBUG:
                gaze_position = eyetracker.getCurrentGazePosition()
                if fixation_within_tolerance(gaze_position, self.images[self.attention].pos,
                                             self.images[self.attention].size[0], self.win):
                    attending_frames += 1
                    if attending_frames==1:
                        self.win.callOnFlip(sendEvent, ns, eyetracker, 'att1', 'attn stim',
                            {'code': self.code,
                             'attn': self.attention,
                             'gaze': self.gaze,
                             'actr': self.actor})
                else:
                    attending_frames = 0
                self.init_frame.draw()
                for image in self.images.values():
                    image.draw()
                if not idx % 3 == 0:
                    self.highlight.draw()
                self.win.flip()
                idx += 1

        if attending_frames >= self.min_attending_frames:
            self.win.callOnFlip(sendEvent, ns, eyetracker, 'mov1', 'movie start',
                            {'code': self.code,
                             'attn': self.attention,
                             'gaze': self.gaze,
                             'actr': self.actor})
            attending_frames = 0
            while not self.video_stim.stim.status == visual.FINISHED:
                if eyetracker is not None and EYETRACKER_DEBUG:
                    gaze_position = eyetracker.getCurrentGazePosition()
                    if fixation_within_tolerance(gaze_position, self.images[self.attention].pos,
                                                 self.images[self.attention].size[0], self.win):
                        attending_frames += 1
                    else:
                        attending_frames=0
                if attending_frames==2:
                    self.win.callOnFlip(sendEvent, ns, eyetracker, 'att2', 'attn face',
                        {'code': self.code,
                         'attn': self.attention,
                         'gaze': self.gaze,
                         'actr': self.actor})
                self.video_stim.stim.draw()
                for image in self.images.values():
                    image.draw()
                self.win.flip()


class Block:
    """
    A block of movies of the same type
    """

    def __init__(self, name, num_trials, init_stim_frames, min_iti_frames, max_iti_frames, win):
        """
        code - code for block to send to netstation
        trials - number of trials to run
        min_delay_frames - minimum delay between movies in frames
        max_delay_frames - maximum delay between movies in frames
        win - psychopy window to use
        """
        self.code = name
        self.num_trials = num_trials
        self.win = win
        self.init_stim_frames = init_stim_frames
        self.min_iti_frames = min_iti_frames
        self.max_iti_frames = max_iti_frames
        self.videos = {}
        self.video_init_frames = {}
        self.trials = []

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
        n_trials = len(self.trials)
        trial_order = range(n_trials)
        if n_trials < self.num_trials:
            trial_order = []
            while len(trial_order) < self.num_trials:
                trial_order.extend(range(n_trials))
        np.random.shuffle(trial_order)

        # Start netstation recording
        sendEvent(ns, eyetracker, 'blk1', "block start", {'code': self.code})

        for t in range(self.num_trials):
            if ns is not None:
                # ns.StartRecording()
                ns.sync()

            # Compute random delay period
            delay_frames = self.min_iti_frames + int(np.random.rand() * (self.max_iti_frames - self.min_iti_frames))

            # clear any keystrokes before starting
            event.clearEvents()

            trial_idx = trial_order[t]
            self.trials[trial_idx].run(ns, eyetracker)

            all_keys = event.getKeys()

            if len(all_keys):
                # Quit task
                if all_keys[0].upper() in ['Q', 'ESCAPE']:
                    return False
                # Pause block
                elif all_keys[0].upper() == 'P':
                    self.pause()
                # End block
                elif all_keys[0].upper() == 'E':
                    break
                event.clearEvents()

            # Black screen for delay
            for i in range(delay_frames):
                self.win.flip()

        # Stop netstation recording
        sendEvent(ns, eyetracker, 'blk2', 'block end', {'code': self.code})
        return True


class ActorImage:
    def __init__(self, win, actor, filename):
        self.actor = actor
        self.filename = filename
        self.stim = visual.ImageStim(win, os.path.join(DATA_DIR, 'images', self.filename))


class PreferentialGaze:
    def __init__(self, win, actors, duration_frames):
        self.win = win
        self.actors = actors
        self.duration_frames = duration_frames
        self.run_idx = 1

    def run(self, ns, eyetracker):
        if self.run_idx==1:
            if np.random.rand() < 0.5:
                self.actors[0].stim.pos = [-10, 0]
                self.actors[1].stim.pos = [10, 0]
            else:
                self.actors[0].stim.pos = [10, 0]
                self.actors[1].stim.pos = [-10, 0]
        else:
            self.actors[0].stim.pos = [-1 * self.actors[0].stim.pos[0], 0]
            self.actors[1].stim.pos = [-1 * self.actors[1].stim.pos[0], 0]
        self.win.callOnFlip(sendEvent, ns, eyetracker, 'pgs%d' % self.run_idx, 'pg start', {})
        for i in range(self.duration_frames):
            for actor in self.actors:
                actor.stim.draw()
            self.win.flip()
        sendEvent(ns, eyetracker, 'pge%d' % self.run_idx, "pg end", {})
        self.run_idx+=1


if __name__ == '__main__':
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

    # present a dialogue to change params
    dlg = gui.DlgFromDict(
        expInfo,
        title='Gaze',
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
        ns = None

    # run task
    exp = Experiment(expInfo, os.path.join(CONF_DIR, 'gaze_experiment.xml'))
    exp.run(ns)

