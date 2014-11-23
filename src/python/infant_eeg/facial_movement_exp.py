from xml.etree import ElementTree as ET
import numpy as np
from psychopy import event, visual
from infant_eeg.experiment import Experiment
from infant_eeg.stim import MovieStimulus
from infant_eeg.util import sendEvent

class FacialMovementExperiment(Experiment):
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """

    def run(self):
        """
        Run task
        ns - netstation connection
        """
        self.initialize()

        for block_name in self.block_order:
            if self.distractor_set.run() and self.eye_tracker is not None:#
                self.eye_tracker.stopTracking()
                self.calibrate_eyetracker()
                self.eye_tracker.startTracking()

            if not self.blocks[block_name].run(self.ns, self.eye_tracker):
                break

            if self.eye_tracker is not None:
                self.eye_tracker.flushData()

        self.close()

    def read_xml(self, file_name):
        root_element=ET.parse(file_name).getroot()
        self.name=root_element.attrib['name']
        self.type=root_element.attrib['type']
        self.num_blocks=int(root_element.attrib['num_blocks'])

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
            iti_frames=self.min_iti_frames+int(np.random.rand()*(self.max_iti_frames-self.min_iti_frames))

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

            while not self.stimuli[video_idx].stim.status==visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
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
            for i in range(iti_frames):
                self.win.flip()

        # Stop netstation recording
        sendEvent(ns, eyetracker, 'blk2', 'block end', {'code' : self.code} )
        return True