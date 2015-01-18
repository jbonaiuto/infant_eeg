from infant_eeg.experiment import Experiment
import os
from psychopy import visual, event
from xml.etree import ElementTree
from infant_eeg.config import DATA_DIR
import numpy as np
from infant_eeg.stim import MovieStimulus
from infant_eeg.util import send_event, fixation_within_tolerance, draw_eye_debug


class GazeFollowingExperiment(Experiment):
    """
    Gaze following experiment - prefential gaze trials separated by distractors, blocks of gaze-contingent movies
    presented with distractor images/sounds in between each block
    """

    def __init__(self, exp_info, file_name):
        """
        Initialize class
        :param exp_info - experiment info
        :param file_name - file to read experiment definition from
        """
        self.preferential_gaze = None
        self.preferential_gaze_trials = 1
        self.congruent_actor = None
        self.incongruent_actor = None
        self.videos = {}
        self.video_init_frames = {}

        Experiment.__init__(self, exp_info, file_name)

    def pause(self):
        """
        Pause block
        """
        event.clearEvents()
        self.win.flip()
        event.waitKeys()

    def run(self):
        """
        Run experiment
        """

        cont = True

        # Run preferential gaze trials
        for i in range(self.preferential_gaze_trials):
            self.distractor_set.run()

            # clear any keystrokes before starting
            event.clearEvents()

            self.preferential_gaze.run(self.ns, self.eye_tracker, self.mouse, self.gaze_debug)

            # Check user input
            all_keys = event.getKeys()
            if len(all_keys):
                # Quit experiment
                if all_keys[0].upper() in ['Q', 'ESCAPE']:
                    cont=False
                    break
                # Pause block
                elif all_keys[0].upper() == 'P':
                    self.pause()
                # End block
                elif all_keys[0].upper() == 'E':
                    break
                event.clearEvents()

        # Run blocks
        if cont:
            for block_name in self.block_order:

                # Show distractors
                self.distractor_set.run()

                # Run block
                if not self.blocks[block_name].run(self.ns, self.eye_tracker, self.mouse, self.gaze_debug):
                    cont = False
                    break

                # Write eytracking data to file
                if self.eye_tracker is not None:
                    self.eye_tracker.flushData()

        # Run preferential gaze trials
        if cont:
            for i in range(self.preferential_gaze_trials):
                self.distractor_set.run()

                # clear any keystrokes before starting
                event.clearEvents()

                self.preferential_gaze.run(self.ns, self.eye_tracker, self.mouse, self.gaze_debug)

                # Check user input
                all_keys = event.getKeys()
                if len(all_keys):
                    # Quit experiment
                    if all_keys[0].upper() in ['Q', 'ESCAPE'] or all_keys[0].upper()=='E':
                        break
                    # Pause block
                    elif all_keys[0].upper() == 'P':
                        self.pause()
                    event.clearEvents()

        # End experiment
        self.close()

    def read_xml(self, file_name):
        """
        Read experiment definition file
        :param file_name - file to read definition from
        """
        root_element = ElementTree.parse(file_name).getroot()
        self.name = root_element.attrib['name']
        self.type = root_element.attrib['type']
        self.num_blocks = int(root_element.attrib['num_blocks'])

        # Read prefential gaze trial info
        preferential_gaze_node = root_element.find('preferential_gaze')
        preferential_gaze_duration = float(preferential_gaze_node.attrib['duration'])
        self.preferential_gaze_trials = int(preferential_gaze_node.attrib['num_trials'])
        actor_nodes = preferential_gaze_node.findall('actor')
        actor_images = []
        for actor_node in actor_nodes:
            actor_name = actor_node.attrib['name']
            filename = actor_node.attrib['file_name']
            actor_images.append(ActorImage(self.win, actor_name, filename))
        self.preferential_gaze = PreferentialGaze(self.win, actor_images,
                                                  int(preferential_gaze_duration / self.mean_ms_per_frame))
        self.congruent_actor = self.exp_info['congruent actor']
        self.incongruent_actor = self.exp_info['incongruent actor']

        # Read video info
        videos_node = root_element.find('videos')
        video_nodes = videos_node.findall('video')
        for video_node in video_nodes:
            direction = video_node.attrib['direction']
            actor = video_node.attrib['actor']
            file_name = video_node.attrib['file_name']
            init_frame = video_node.attrib['init_frame']
            shuffled = int(video_node.attrib['shuffled'])
            if not actor in self.videos:
                self.videos[actor] = {}
                self.video_init_frames[actor] = {}
            if not direction in self.videos[actor]:
                self.videos[actor][direction] = {}
                self.video_init_frames[actor][direction] = {}
            self.videos[actor][direction][shuffled] = MovieStimulus(self.win, direction, actor, file_name)
            self.video_init_frames[actor][direction][shuffled] = visual.ImageStim(self.win,
                                                                                  os.path.join(DATA_DIR, 'images',
                                                                                               init_frame),
                                                                                  units='pix', size=(900, 720))
            self.video_init_frames[actor][direction][shuffled].size *= 1.25

        # Read block info
        blocks_node = root_element.find('blocks')
        block_nodes = blocks_node.findall('block')
        for block_node in block_nodes:
            block_name = block_node.attrib['name']
            num_trials = int(block_node.attrib['num_trials'])
            init_stim_ms = float(block_node.attrib['init_stim'])
            min_attending_ms = float(block_node.attrib['min_attending'])
            max_attending_ms = float(block_node.attrib['max_attending'])
            min_iti_ms = float(block_node.attrib['min_iti'])
            max_iti_ms = float(block_node.attrib['max_iti'])

            # Compute delay in frames based on frame rate
            init_stim_frames = int(init_stim_ms / self.mean_ms_per_frame)
            min_attending_frames = int(min_attending_ms / self.mean_ms_per_frame)
            max_attending_frames = int(max_attending_ms / self.mean_ms_per_frame)
            min_iti_frames = int(min_iti_ms / self.mean_ms_per_frame)
            max_iti_frames = int(max_iti_ms / self.mean_ms_per_frame)

            block = Block(block_name, num_trials, min_iti_frames, max_iti_frames, self.win)

            # Read trial info
            trials_node = block_node.find('trials')
            trial_nodes = trials_node.findall('trial')
            for trial_node in trial_nodes:
                code = trial_node.attrib['code']
                left_image = trial_node.attrib['left_image']
                right_image = trial_node.attrib['right_image']
                attention = trial_node.attrib['attention']
                gaze = trial_node.attrib['gaze']
                shuffled = int(trial_node.attrib['shuffled'])
                if gaze == 'cong':
                    actor = self.congruent_actor
                else:
                    actor = self.incongruent_actor
                trial = Trial(self.win, code, init_stim_frames, min_attending_frames, max_attending_frames, left_image,
                              right_image, attention, gaze, actor, shuffled)
                if trial.gaze == 'cong':
                    trial.init_frame = self.video_init_frames[self.congruent_actor][trial.attention][shuffled]
                    trial.video_stim = self.videos[self.congruent_actor][trial.attention][shuffled]
                else:
                    if trial.attention == 'l':
                        trial.init_frame = self.video_init_frames[self.incongruent_actor]['r'][shuffled]
                        trial.video_stim = self.videos[self.incongruent_actor]['r'][shuffled]
                    else:
                        trial.init_frame = self.video_init_frames[self.incongruent_actor]['l'][shuffled]
                        trial.video_stim = self.videos[self.incongruent_actor]['l'][shuffled]
                block.trials.append(trial)
            self.blocks[block_name] = block


class Trial:
    """
    Single trial - initial frame of video shown in center with two stimuli on either side, after delay one stimulus
    is highlighted. After fixation on highlighted stimulus, movie starts
    """

    def __init__(self, win, code, init_stim_frames, min_attending_frames, max_attending_frames, left_image, right_image,
                 attention, gaze, actor, shuffled):
        """
        Initialize class
        :param win - window to use
        :param code - trial code to send to netstation
        :param init_stim_frames - number of frames to show stimulus before highlighting
        :param min_attending_frames - number of frames to require fixation on highlighted stimulus before starting movie
        :param max_attending_frames - max frames to wait for stimulus fixation before aborting trial
        :param left_image - stimulus on left
        :param right_image - stimulus on right
        :param attention - l or r - which stimulus to highlight
        :param gaze - cong or inco - congruent or incongruent gaze
        :param actor - which actor to show
        """
        self.win = win
        self.code = code
        self.init_stim_frames = init_stim_frames
        self.min_attending_frames = min_attending_frames
        self.max_attending_frames = max_attending_frames
        self.images = {
            'l': visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images', left_image)),
            'r': visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images', right_image))
        }
        self.images['l'].size *= .95
        self.images['r'].size *= .95
        self.images['l'].pos = [-22, 0]
        self.images['r'].pos = [22, 0]
        self.highlight = visual.Rect(self.win, width=self.images['l'].size[0] + 1, height=self.images['r'].size[1] + 1)
        self.highlight.lineColor = [1, -1, -1]
        self.highlight.lineWidth = 10
        self.attention = attention
        self.gaze = gaze
        self.init_frame = None
        self.video_stim = None
        self.actor = actor
        self.shuffled=shuffled
        self.code_table = {
            'code': self.code,
            'attn': self.attention,
            'gaze': self.gaze,
            'shuf': self.shuffled,
            'actr': str(self.actor)
        }

    def show_init_stimulus(self, ns, eyetracker, mouse, gaze_debug):
        # Show two stimuli and initial frame of movie
        self.win.callOnFlip(send_event, ns, eyetracker, 'ima1', 'stim start', self.code_table)
        for i in range(self.init_stim_frames):
            self.init_frame.draw()
            for image in self.images.values():
                image.draw()
            draw_eye_debug(gaze_debug, eyetracker, mouse)
            self.win.flip()

    def highlight_peripheral_stimulus(self, ns, eyetracker, mouse, gaze_debug):
        # Set which stimulus to highlight
        self.highlight.pos = self.images[self.attention].pos
        # Show initial frame of video until highlighted stimulus if fixated on or abort
        attending_frames = 0
        highlight_on = False
        idx = 0
        self.win.callOnFlip(send_event, ns, eyetracker, 'ima2', 'attn start', self.code_table)
        while attending_frames < self.min_attending_frames and idx < self.max_attending_frames:
            # Draw init frame of movie and two stimuli
            self.init_frame.draw()
            current_pos = self.images[self.attention].pos
            if idx % 5 == 0:
                new_pos = current_pos
                if current_pos[1] == 0 or current_pos[1] == -1:
                    new_pos[1] = 1
                else:
                    new_pos[1] = -1
                self.images[self.attention].setPos(new_pos)
                self.highlight.setPos(self.images[self.attention].pos)

            for image in self.images.values():
                image.draw()

            # Highlight stimulus
            if idx % 5 == 0:
                if highlight_on:
                    highlight_on = False
                else:
                    highlight_on = True
                if highlight_on:
                    self.highlight.draw()

            draw_eye_debug(gaze_debug, eyetracker, mouse)

            self.win.flip()
            idx += 1

            # Get gaze position from eyetracker or mouse
            gaze_position = (0, 0)
            if eyetracker is not None:
                gaze_position = eyetracker.getCurrentGazePosition()
                gaze_position = (0.5 * (gaze_position[0] + gaze_position[2]),
                                 0.5 * (gaze_position[1] + gaze_position[3]))
            elif mouse is not None:
                gaze_position = mouse.getPos()

            # Check if looking at right stimulus
            if fixation_within_tolerance(gaze_position, self.images[self.attention].pos,
                                         self.images[self.attention].size[0] / 2.0+2, self.win):
                attending_frames += 1
                if attending_frames == 1:
                    self.win.callOnFlip(send_event, ns, eyetracker, 'att1', 'attn stim', self.code_table)
            else:
                attending_frames = 0

        return attending_frames

    def play_movie(self, ns, eyetracker, mouse, gaze_debug):
        self.images['l'].pos = [-22, 0]
        self.images['r'].pos = [22, 0]

        # Play movie
        self.win.callOnFlip(send_event, ns, eyetracker, 'mov1', 'movie start', self.code_table)

        attending_frames = 0
        while not self.video_stim.stim.status == visual.FINISHED:

            # Draw video frames and stimuli
            self.video_stim.stim.draw()
            for image in self.images.values():
                image.draw()
            draw_eye_debug(gaze_debug, eyetracker, mouse)

            self.win.flip()

            # Get gaze position from eyetracker or mouse
            gaze_position = (0, 0)
            if eyetracker is not None:
                gaze_position = eyetracker.getCurrentGazePosition()
                gaze_position = (0.5 * (gaze_position[0] + gaze_position[2]),
                                 0.5 * (gaze_position[1] + gaze_position[3]))
            elif mouse is not None:
                gaze_position = mouse.getPos()

            # Check if looking at face
            if fixation_within_tolerance(gaze_position, self.init_frame.pos, 10, self.win):
                if gaze_debug is not None:
                    gaze_debug.fillColor = (-1, -1, 1)
                attending_frames += 1
                if attending_frames == 1:
                    self.win.callOnFlip(send_event, ns, eyetracker, 'att2', 'attn face', self.code_table)
            else:
                if gaze_debug is not None:
                    gaze_debug.fillColor = (1, -1, -1)
        if gaze_debug is not None:
            gaze_debug.fillColor = (1, -1, -1)

    def run(self, ns, eyetracker, mouse, gaze_debug):
        """
        Run trial
        :param ns - connection to netstation
        :param eyetracker - connection to eyetracker
        :param mouse - mouse
        """

        # Reset movie to beginning
        self.video_stim.reload(self.win)

        self.show_init_stimulus(ns, eyetracker, mouse, gaze_debug)

        attending_frames = self.highlight_peripheral_stimulus(ns, eyetracker, mouse, gaze_debug)

        if attending_frames >= self.min_attending_frames:
            self.play_movie(ns, eyetracker, mouse, gaze_debug)


class Block:
    """
    A block of trials
    """

    def __init__(self, code, num_trials, min_iti_frames, max_iti_frames, win):
        """
        :param code - code for block to send to netstation
        :param num_trials - number of trials to run
        :param min_iti_frames - minimum delay between movies in frames
        :param max_iti_frames - maximum delay between movies in frames
        :param win - psychopy window to use
        """
        self.code = code
        self.num_trials = num_trials
        self.win = win
        self.min_iti_frames = min_iti_frames
        self.max_iti_frames = max_iti_frames
        self.trials = []

    def pause(self):
        """
        Pause block
        """
        event.clearEvents()
        self.win.flip()
        event.waitKeys()

    def run(self, ns, eyetracker, mouse, gaze_debug):
        """
        Run the block
        :param ns - connection to netstation
        :return True if task should continue, False if should quit
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
        send_event(ns, eyetracker, 'blk1', "block start", {'code': self.code})

        # Run trials
        for t in range(self.num_trials):
            # Synch with netstation in between trials
            if ns is not None:
                ns.sync()

            # Compute random delay period
            delay_frames = self.min_iti_frames + int(np.random.rand() * (self.max_iti_frames - self.min_iti_frames))

            # clear any keystrokes before starting
            event.clearEvents()

            # Run trial
            trial_idx = trial_order[t]
            self.trials[trial_idx].run(ns, eyetracker, mouse, gaze_debug)

            # Check user input
            all_keys = event.getKeys()
            if len(all_keys):
                # Quit experiment
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
        send_event(ns, eyetracker, 'blk2', 'block end', {'code': self.code})
        return True


class ActorImage:
    """
    Image of an actor for preferential gaze
    """
    def __init__(self, win, actor, filename):
        """
        Initialize class
        :param win: window to use
        :param actor: actor name
        :param filename: file to load image from
        """
        self.actor = actor
        self.filename = filename
        self.stim = visual.ImageStim(win, os.path.join(DATA_DIR, 'images', self.filename))
        self.stim.size *= 1.5


class PreferentialGaze:
    """
    Preferential gaze trial
    """

    def __init__(self, win, actors, duration_frames):
        """
        Initialize class
        :param win: window to use
        :param actors: actors to show
        :param duration_frames: how long to show (in frames)
        """
        self.win = win
        self.actors = actors
        self.duration_frames = duration_frames

    def run(self, ns, eyetracker, mouse, gaze_debug):
        """
        Run trial
        :param ns: netstation connection
        :param eyetracker: eyetracker
        :return:
        """

        # Show actors on random sides of screen
        left_actor = None
        right_actor = None
        if np.random.rand() < 0.5:
            self.actors[0].stim.pos = [-15, 0]
            self.actors[1].stim.pos = [15, 0]
            left_actor = self.actors[0].actor
            right_actor = self.actors[1].actor
        else:
            self.actors[0].stim.pos = [15, 0]
            self.actors[1].stim.pos = [-15, 0]
            left_actor = self.actors[1].actor
            right_actor = self.actors[0].actor

        # Draw images
        self.win.callOnFlip(send_event, ns, eyetracker, 'pgst', 'pg start', {'left': left_actor, 'rght': right_actor})
        for i in range(self.duration_frames):
            for actor in self.actors:
                actor.stim.draw()
            draw_eye_debug(gaze_debug, eyetracker, mouse)
            self.win.flip()
        send_event(ns, eyetracker, 'pgen', "pg end", {'left': left_actor, 'rght': right_actor})
