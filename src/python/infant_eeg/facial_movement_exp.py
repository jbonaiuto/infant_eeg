from infant_eeg.experiment import Experiment, Event
from xml.etree import ElementTree
import numpy as np
from psychopy import event, visual
from infant_eeg.stim import MovieStimulus
from infant_eeg.util import send_event, draw_eye_debug
from egi import threaded as egi

class FacialMovementExperiment(Experiment):
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """

    def run(self):
        """
        Run task
        """

        # Run blocks
        for block_name in self.block_order:

            # Show distractors
            self.distractor_set.show_pictures_and_sounds()

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

            # Compute delay in frames based on frame rate
            min_iti_frames = int(min_iti_ms/self.mean_ms_per_frame)
            max_iti_frames = int(max_iti_ms/self.mean_ms_per_frame)

            self.blocks[block_name] = Block(block_name, num_trials, min_iti_frames, max_iti_frames, self.win)

            # Read video info
            videos_node = block_node.find('videos')
            video_nodes = videos_node.findall('video')
            for video_node in video_nodes:
                size=(float(video_node.attrib['width_degrees']), float(video_node.attrib['height_degrees']))
                self.blocks[block_name].stimuli.append(MovieStimulus(self.win, video_node.attrib['movement'],
                                                                     video_node.attrib['actor'],
                                                                     video_node.attrib['file_name'], size))


class Block:
    """
    A block of movies of the same type
    """

    def __init__(self, code, trials, min_iti_frames, max_iti_frames, win):
        """
        Initialize class
        :param: code - code for block to send to netstation
        :param: trials - number of trials to run
        :param: min_delay_frames - minimum delay between movies in frames
        :param: max_delay_frames - maximum delay between movies in frames
        :param: win - psychopy window to use
        """
        self.code = code
        self.trials = trials
        self.win = win
        self.min_iti_frames = min_iti_frames
        self.max_iti_frames = max_iti_frames
        self.stimuli = []
        self.trial_events=[]

    def pause(self):
        """
        Pause block
        """
        event.clearEvents()
        self.win.flip()
        event.waitKeys()

    def add_trial_event(self, ns, eye_tracker, code, label, table):
        self.trial_events.append(Event(code, label, table))
        if eye_tracker is not None:
            eye_tracker.recordEvent(code, label, table)

    def run(self, ns, eyetracker, mouse, gaze_debug, distractor_set, debug_sq):
        """
        Run the block
        :param ns: connection to netstation
        :param eyetracker: connection to eyetracker
        :returns True if task should continue, False if should quit
        """

        # Compute trial order
        n_movies = len(self.stimuli)
        vid_order = range(n_movies)
        if n_movies < self.trials:
            vid_order = []
            while len(vid_order) < self.trials:
                vid_order.extend(range(n_movies))
        np.random.shuffle(vid_order)

        # Start netstation recording
        send_event(ns, eyetracker, 'blk1', "block start", {'code': self.code})

        # Run trials
        for t in range(self.trials):

            # Synch with netstation in between trials
            if ns is not None:
                ns.sync()

            # Compute random delay period
            iti_frames = self.min_iti_frames+int(np.random.rand()*(self.max_iti_frames-self.min_iti_frames))

            # Reset movie to beginning
            video_idx = vid_order[t]
            self.stimuli[video_idx].reload(self.win)

            # clear any keystrokes before starting
            event.clearEvents()

            # Play movie
            self.win.callOnFlip(self.add_trial_event, ns, eyetracker, 'mov1', 'movie start',
                                {'code': self.code,
                                 'mvmt': self.stimuli[video_idx].movement,
                                 'actr': self.stimuli[video_idx].actor})
            while not self.stimuli[video_idx].stim.status == visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
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
                    ns.send_event(trial_event.code, label=trial_event.label, timestamp=trial_event.timestamp[0], table=trial_event.table)
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