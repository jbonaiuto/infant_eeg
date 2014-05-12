import os
from psychopy import data, gui, event, visual, sound
from psychopy.visual import Window
from infant_eeg.config import MONITOR, SCREEN, NETSTATION_IP, DATA_DIR
import egi.simple as egi
import numpy as np

class Task:
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """

    def __init__(self, n_blocks, n_trials, distractor_duration_ms, min_delay_ms, max_delay_ms, ns):
        """
        n_blocks - number of blocks to run for
        n_trials - number of trials per block
        distractor_duration_ms - duration of each distractor image in ms
        min_delay_ms - minimum delay between movies in ms
        max_delay_ms - maximum delay between movies in ms
        ns - netstation connection
        """

        # Keep connection to netstation
        self.ns=ns

        # Window to use
        wintype='pyglet' # use pyglet if possible, it's faster at event handling
        self.win = Window(
            [1600,900],
            monitor=MONITOR,
            screen=SCREEN,
            units="deg",
            fullscr=True,
            color=[-1,-1,-1],
            winType=wintype)
        self.win.setMouseVisible(False)
        event.clearEvents()

        # Measure frame rate
        self.mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame=visual.getMsPerFrame(self.win, nFrames=60,
            showVisual=True)

        # Compute delay in frames based on frame rate
        min_delay_frames=int(min_delay_ms/self.mean_ms_per_frame)
        max_delay_frames=int(max_delay_ms/self.mean_ms_per_frame)

        # Initialize blocks
        self.blocks={
            'joy': Block('joy', n_trials, min_delay_frames, max_delay_frames, self.win, self.ns),
            'sad': Block('sad', n_trials, min_delay_frames, max_delay_frames, self.win, self.ns),
            'move': Block('move', n_trials, min_delay_frames, max_delay_frames, self.win, self.ns),
            'shuf': Block('shuf', n_trials, min_delay_frames, max_delay_frames, self.win, self.ns)
        }
        self.blocks['joy'].add_stimulus('f01','F01-Joy-Face Forward.mpg')
        self.blocks['joy'].add_stimulus('f03','F03-Joy-Face Forward.mpg')
        self.blocks['sad'].add_stimulus('f01','F01-Sadness-Face Forward.mpg')
        self.blocks['sad'].add_stimulus('f03','F03-Sadness-Face Forward.mpg')
        self.blocks['move'].add_stimulus('f06','F06-MouthOpening-Face Forward.mpg')
        self.blocks['move'].add_stimulus('f07','F07-MouthOpening-Face Forward.mpg')
        self.blocks['shuf'].add_stimulus('f01','F01-Joy-Face Forward.shuffled.mpg')
        self.blocks['shuf'].add_stimulus('f01','F01-Sadness-Face Forward.shuffled.mpg')
        self.blocks['shuf'].add_stimulus('f03','F03-Joy-Face Forward.shuffled.mpg')
        self.blocks['shuf'].add_stimulus('f03','F03-Sadness-Face Forward.shuffled.mpg')
        self.blocks['shuf'].add_stimulus('f06','F06-MouthOpening-Face Forward.shuffled.mpg')
        self.blocks['shuf'].add_stimulus('f07','F07-MouthOpening-Face Forward.shuffled.mpg')

        # Create random block order
        self.n_blocks=n_blocks
        self.block_order=[]
        while len(self.block_order)<n_blocks:
            self.block_order.extend(self.blocks.keys())
        np.random.shuffle(self.block_order)

        # Compute distractor duration in frames based on frame rate
        distractor_duration_frames=int(distractor_duration_ms/self.mean_ms_per_frame)

        # Initialize set of distractors
        self.distractor_set=DistractorSet(os.path.join(DATA_DIR,'images','distractors','space'),
            os.path.join(DATA_DIR,'sounds','distractors'),
            os.path.join(DATA_DIR,'images','distractors','star-cartoon.jpg'),distractor_duration_frames, self.win)

    def run(self):
        """
        Run task
        """
        for block_name in self.block_order:
            self.distractor_set.run()

            # Re-synch with netstation in between blocks
            if self.ns is not None:
                self.ns.sync()

            if not self.blocks[block_name].run():
                break


class Block:
    """
    A block of movies of the same type
    """

    def __init__(self, code, trials, min_delay_frames, max_delay_frames, win, ns):
        """
        code - code for block to send to netstation
        trials - number of trials to run
        min_delay_frames - minimum delay between movies in frames
        max_delay_frames - maximum delay between movies in frames
        win - psychopy window to use
        ns - connection to netstation
        """
        self.code=code
        self.trials=trials
        self.win=win
        self.min_delay_frames=min_delay_frames
        self.max_delay_frames=max_delay_frames
        self.ns=ns
        self.stimuli=[]        
    
    def add_stimulus(self, actor, file_name):
        """
        Add a stimulus movie to the block
        actor - actor ID
        file_name - movie file to load
        """
        stim=MovieStimulus(self.win, actor, file_name)
        self.stimuli.append(stim)

    def run(self):
        """
        Run the block
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
        if self.ns is not None:
            self.ns.StartRecording()
            self.ns.sync()
            self.ns.send_event( 'blck', label="block start", timestamp=egi.ms_localtime(), table = {'code' : self.code} )

        for t in range(self.trials):
            # Compute random delay period
            delay_frames=self.min_delay_frames+int(np.random.rand()*(self.max_delay_frames-self.min_delay_frames))

            # Reset movie to beginning
            video_idx=vid_order[t]
            self.stimuli[video_idx].stim.seek(0)
            self.stimuli[video_idx].stim.status=0

            # clear any keystrokes before starting
            event.clearEvents()
            all_keys=[]

            # Tell netstation the movie is starting
            if self.ns is not None:
                self.ns.send_event( 'mov_', label="movie start", timestamp=egi.ms_localtime(),
                    table = {'code' : self.code, 'actr' : self.stimuli[video_idx].actor} )

            # Play movie
            while not self.stimuli[video_idx].stim.status==visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
                self.win.flip()
            all_keys=event.getKeys()

            # Tell netstation the movie has stopped
            if self.ns is not None:
                self.ns.send_event( 'mov_', label="movie end", timestamp=egi.ms_localtime())

            # Quit block
            if len(all_keys) and all_keys[0].upper() in ['Q','ESCAPE']:
                return False

            # Black screen for delay
            for i in range(delay_frames):
                self.win.flip()

        # Stop netstation recording
        if self.ns is not None:
            self.ns.StopRecording()

        return True


class MovieStimulus:
    """
    A movie stimulus
    """

    def __init__(self, win, actor, file_name):
        """
        win - window to show movie in
        actor - ID of actor
        file_name - file containing movie
        """
        self.actor=actor
        self.file_name=file_name
        self.stim=visual.MovieStim(win, os.path.join(DATA_DIR,'movies',self.file_name))


class DistractorSet:
    """
    A set of distractor images and sounds
    """

    def __init__(self, image_path, sound_path, reward_image_file, duration_frames, win):
        """
        image_path - path to load distractor images from
        sound_path - path to load distractor sounds from
        reward_image_file - file containing reward image
        duration_frames - duration of each distractor image in frames
        win - window to display images in
        """
        self.win=win

        # load images
        self.pictures=[]
        image_files = [ f for f in os.listdir(image_path) if os.path.isfile(os.path.join(image_path,f)) ]
        for file in image_files:
            self.pictures.append(visual.ImageStim(win, os.path.join(image_path,file)))

        # load sounds
        self.sounds=[]
        sound_files = [ f for f in os.listdir(sound_path) if os.path.isfile(os.path.join(sound_path,f)) ]
        for file in sound_files:
            self.sounds.append(sound.Sound(os.path.join(sound_path,file)))

        # load reward image
        self.reward_image=visual.ImageStim(win,reward_image_file)

        self.duration_frames=duration_frames

    def run(self):
        """
        Run distractor set
        """
        # clear any keystrokes before starting
        event.clearEvents()
        all_keys=[]

        # wait for a keypress
        while len(all_keys)==0:
            # Pick random picture and sound
            distractor_picture_idx=np.random.choice(range(len(self.pictures)))
            distractor_sound_idx=np.random.choice(range(len(self.sounds)))

            # Play sound
            self.sounds[distractor_sound_idx].play()
            # Show picture
            for i in range(self.duration_frames):
                self.pictures[distractor_picture_idx].draw()
                self.win.flip()

            # Look for key press
            all_keys=event.getKeys()

        # taking the first keypress in the list
        thisKey=all_keys[0].upper()
        # show reward image if R pressed
        if thisKey=='R':
            # clear any keystrokes before starting
            event.clearEvents()
            all_keys=[]

            # show reward image until keypress
            while len(all_keys)==0:
                self.reward_image.draw()
                self.win.flip()
                all_keys=event.getKeys()


if __name__=='__main__':
    # experiment parameters
    expInfo = {
        'subject': '',
        'dateStr': data.getDateStr(),
        'condition': ''
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
        ns.connect(NETSTATION_IP, 55513)
        ns.BeginSession()
        ns.sync()
    except:
        print('Could not connect with NetStation!')
        ns=None

    # run task
    task=Task(20, 6, 2000.0, 800.0, 1200.0, ns)
    task.run()

    # close netstation connection
    if ns:
        ns.EndSession()
        ns.disconnect()