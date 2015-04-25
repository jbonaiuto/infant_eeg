import copy
import os
from psychopy import event, visual
from infant_eeg.config import DATA_DIR
from infant_eeg.experiment import Experiment, Event
from xml.etree import ElementTree
import numpy as np
from infant_eeg.facial_movement_exp import FacialMovementExperiment
from infant_eeg.stim import MovieStimulus
from infant_eeg.util import send_event, draw_eye_debug
from egi import threaded as egi


class NineMonthFacialMovementExperiment(Experiment):
    """
    A simple observation task - blocks of various movies presented with distractor videos in between each block
    """

    def is_valid_block_order(self):
        last_block_key=None
        for block_key in self.block_order:
            block=self.blocks[block_key]
            if last_block_key is not None:
                last_block=self.blocks[last_block_key]
                for i in range(len(block.vid_order)):
                    if block.movie_stimuli[block.vid_order[i]].movement==last_block.movie_stimuli[last_block.vid_order[i]].movement:
                        return False
            last_block_key=block_key
        return True

    def initialize(self):
        Experiment.initialize(self)
        # Create random block order
        valid=False
        while not valid:
            self.block_order = []
            n_repeats = int(self.num_blocks/len(self.blocks.keys()))
            for i in range(n_repeats):
                subblock_order = copy.copy(self.blocks.keys())
                np.random.shuffle(subblock_order)
                self.block_order.extend(subblock_order)
            valid=self.is_valid_block_order()

    def run(self):
        """
        Run task
        """

        # Run blocks
        for block_name in self.block_order:

            # Show distractors
            self.distractor_set.show_video()

            # Run block
            resp=self.blocks[block_name].run(self.ns, self.eye_tracker, self.mouse, self.gaze_debug,
                                             self.distractor_set, self.debug_sq)
            if len(resp):
                # Quit experiment
                if resp[0].upper() in ['Q', 'ESCAPE']:
                    break

            # Write eyetracker data to file
            if self.eye_tracker is not None:
                self.eye_tracker.flushData()

        self.close()

    def read_xml(self, file_name):
        """
        Read experiment definition
        :param file_name: file to read definition from
        """
        root_element = ElementTree.parse(file_name).getroot()
        self.name = root_element.attrib['name']
        self.type = root_element.attrib['type']
        self.num_blocks = int(root_element.attrib['num_blocks'])

        # Read block info
        blocks_node = root_element.find('blocks')
        block_nodes = blocks_node.findall('block')
        for block_node in block_nodes:
            block_name = block_node.attrib['name']
            num_trials = int(block_node.attrib['num_trials'])
            min_iti_ms = float(block_node.attrib['min_iti'])
            max_iti_ms = float(block_node.attrib['max_iti'])
            actor_repeats = int(block_node.attrib['actor_repeats'])
            movement_repeats = int(block_node.attrib['movement_repeats'])
            min_init_frame_ms=float(block_node.attrib['min_init_frame'])
            max_init_frame_ms=float(block_node.attrib['max_init_frame'])

            # Compute delay in frames based on frame rate
            min_iti_frames = int(min_iti_ms/self.mean_ms_per_frame)
            max_iti_frames = int(max_iti_ms/self.mean_ms_per_frame)
            min_init_frame_frames = int(min_init_frame_ms/self.mean_ms_per_frame)
            max_init_frame_frames = int(max_init_frame_ms/self.mean_ms_per_frame)

            self.blocks[block_name] = Block(block_name, num_trials, min_iti_frames, max_iti_frames,
                                            min_init_frame_frames, max_init_frame_frames, actor_repeats,
                                            movement_repeats, self.win)

            # Read video info
            videos_node = block_node.find('videos')
            video_nodes = videos_node.findall('video')
            for video_node in video_nodes:
                size=(float(video_node.attrib['width_degrees']), float(video_node.attrib['height_degrees']))
                init_frame = video_node.attrib['init_frame']
                self.blocks[block_name].movie_stimuli.append(MovieStimulus(self.win, video_node.attrib['movement'],
                                                                     video_node.attrib['actor'],
                                                                     video_node.attrib['file_name'], size))
                self.blocks[block_name].init_frames.append(visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images',
                                                                                                   init_frame),
                                                                            units='deg', size=size))
            self.blocks[block_name].initialize()


class Block:
    """
    A block of movies of the same type
    """

    def __init__(self, code, trials, min_iti_frames, max_iti_frames, min_init_frame_frames, max_init_frame_frames,
                 actor_repeats, movement_repeats, win):
        """
        Initialize class
        :param: code - code for block to send to netstation
        :param: trials - number of trials to run
        :param: min_delay_frames - minimum delay between movies in frames
        :param: max_delay_frames - maximum delay between movies in frames
        :param: min_init_frame_frames - minimum time to show the initial movie frame in frames
        :param: max_init_frame_frames - maximum time to show the initial movie frame in frames
        :param: actor_repeats - max number of times to show the same actor
        :param: movement_repeats - max number of times to show the same movement
        :param: win - psychopy window to use
        """
        self.code = code
        self.trials = trials
        self.win = win
        self.min_iti_frames = min_iti_frames
        self.max_iti_frames = max_iti_frames
        self.min_init_frame_frames = min_init_frame_frames
        self.max_init_frame_frames = max_init_frame_frames
        self.actor_repeats=actor_repeats
        self.movement_repeats=movement_repeats
        self.movie_stimuli = []
        self.init_frames=[]
        self.trial_events=[]

    def pause(self):
        """
        Pause block
        """
        event.clearEvents()
        self.win.flip()
        event.waitKeys()

    def add_trial_event(self, ns, eye_tracker, code, label, table):
        trial_event=Event(code, label, table)
        self.trial_events.append(trial_event)
        if eye_tracker is not None:
            eye_tracker.recordEvent(trial_event)

    def is_valid_trial_order(self):
        actor_counts={}
        movement_counts={}
        for vid_idx in self.vid_order:
            movement=self.movie_stimuli[vid_idx].movement
            actor=self.movie_stimuli[vid_idx].actor

            if not movement in movement_counts:
                movement_counts[movement]=0
            if not actor in actor_counts:
                actor_counts[actor]=0

            movement_counts[movement]+=1
            actor_counts[actor]+=1

        for movement,count in movement_counts.iteritems():
            if count>self.movement_repeats:
                return False

        for actor,count in actor_counts.iteritems():
            if count>self.actor_repeats:
                return False

    def initialize(self):
        # Compute trial order
        valid=False
        while not valid:
            n_movies = len(self.movie_stimuli)
            self.vid_order = range(n_movies)
            if n_movies < self.trials:
                self.vid_order = []
                while len(self.vid_order) < self.trials:
                    self.vid_order.extend(range(n_movies))
            np.random.shuffle(self.vid_order)
            valid=self.is_valid_trial_order()

    def run(self, ns, eyetracker, mouse, gaze_debug, distractor_set, debug_sq):
        """
        Run the block
        :param ns: connection to netstation
        :param eyetracker: connection to eyetracker
        :returns True if task should continue, False if should quit
        """

        # Start netstation recording
        send_event(ns, eyetracker, 'blk1', "block start", {'code': self.code})

        # Compute random delay period
        iti_frames = self.min_iti_frames+int(np.random.rand()*(self.max_iti_frames-self.min_iti_frames))
        # Black screen for delay
        for i in range(iti_frames):
            self.win.flip()

        # Run trials
        for t in range(self.trials):

            # Synch with netstation in between trials
            if ns is not None:
                ns.sync()

            # Compute random delay period
            iti_frames = self.min_iti_frames+int(np.random.rand()*(self.max_iti_frames-self.min_iti_frames))

            # Compute random initial frame period
            init_frame_frames = self.min_init_frame_frames+int(np.random.rand()*(self.max_init_frame_frames-self.min_init_frame_frames))

            # Reset movie to beginning
            video_idx = self.vid_order[t]
            self.movie_stimuli[video_idx].reload(self.win)

            # clear any keystrokes before starting
            event.clearEvents()

            # Show initial frame
            self.win.callOnFlip(self.add_trial_event, ns, eyetracker, 'ima1', 'initial frame',
                                {'code': self.code,
                                 'mvmt': self.movie_stimuli[video_idx].movement,
                                 'actr': self.movie_stimuli[video_idx].actor})
            for i in range(init_frame_frames):
                self.init_frames[video_idx].draw()
                draw_eye_debug(gaze_debug, eyetracker, mouse)
                if debug_sq is not None:
                    debug_sq.draw()
                self.win.flip()

            # Play movie
            self.win.callOnFlip(self.add_trial_event, ns, eyetracker, 'mov1', 'movie start',
                                {'code': self.code,
                                 'mvmt': self.movie_stimuli[video_idx].movement,
                                 'actr': self.movie_stimuli[video_idx].actor})
            while not self.movie_stimuli[video_idx].stim.status == visual.FINISHED:
                self.movie_stimuli[video_idx].stim.draw()
                draw_eye_debug(gaze_debug, eyetracker, mouse)
                if debug_sq is not None:
                    debug_sq.draw()
                self.win.flip()

            # Tell netstation the movie has stopped
            self.add_trial_event(ns, eyetracker, 'mov2', 'movie end', {})

            # Black screen for delay
            for i in range(iti_frames):
                self.win.flip()

            for trial_event in self.trial_events:
                if ns is not None:
                    ns.send_event(trial_event.code, label=trial_event.label, timestamp=trial_event.timestamp, table=trial_event.table)
            self.trial_events=[]

            # Check user input
            all_keys = event.getKeys()
            if len(all_keys):
                # Quit experiment
                if all_keys[0].upper() in ['Q', 'ESCAPE']:
                    return all_keys[0].upper()
                # Pause block
                elif all_keys[0].upper() == 'P':
                    self.pause()
                # End block
                elif all_keys[0].upper() == 'E':
                    return all_keys[0].upper()
                # Show distractors
                elif all_keys[0].upper() == 'D':
                    distractor_set.show_pictures_and_sounds()
                # Show distractor video
                elif all_keys[0].upper() == 'V':
                    distractor_set.show_video()

                event.clearEvents()

        # Stop netstation recording
        send_event(ns, eyetracker, 'blk2', 'block end', {'code': self.code})
        return []