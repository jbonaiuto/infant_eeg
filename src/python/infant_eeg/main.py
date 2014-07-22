import copy
import sys
if sys.platform=='win32':
    import ctypes
    avbin_lib=ctypes.cdll.LoadLibrary('avbin')
    import psychopy.visual
from psychopy import visual, core
import os
from psychopy import data, gui, event, sound
from psychopy.visual import Window
from xml.etree import ElementTree as ET
from infant_eeg.config import MONITOR, SCREEN, NETSTATION_IP, DATA_DIR, CONF_DIR
#import egi.simple as egi
import egi.threaded as egi
import numpy as np

class Experiment:
    """
    A simple observation task - blocks of various movies presented with distractor images/sounds in between each block
    """
    def __init__(self, file_name):
        """
        file_name - name of XML file containing experiment definition
        """
        self.name=None
        self.num_blocks=0
        self.blocks={}

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

        # Compute distractor duration in frames based on frame rate
        distractor_duration_frames=int(2000.0/self.mean_ms_per_frame)

        # Initialize set of distractors
        self.distractor_set=DistractorSet(os.path.join(DATA_DIR,'images','distractors','space'),
            os.path.join(DATA_DIR,'sounds','distractors'),
            os.path.join(DATA_DIR,'images','distractors','star-cartoon.jpg'),distractor_duration_frames, self.win)

        self.read_xml(file_name)

    def run(self, ns):
        """
        Run task
        ns - netstation connection
        """
        # Create random block order
        n_repeats=int(self.num_blocks/len(self.blocks.keys()))
        self.block_order=[]
        for i in range(n_repeats):
            subblock_order=copy.copy(self.blocks.keys())
            np.random.shuffle(subblock_order)
            self.block_order.extend(subblock_order)

        for block_name in self.block_order:
            self.distractor_set.run()

            self.blocks[block_name].run(ns)

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

def sendEvent(ns, code, label, table):
    if ns is not None:
        ns.send_event(code, label=label, timestamp=egi.ms_localtime(), table=table)

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

    def run(self, ns):
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
        sendEvent(ns, 'blck', "block start", {'code' : self.code})

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
            self.win.callOnFlip(sendEvent, ns, 'mov1', 'movie start', {'code' : self.code, 'mvmt': self.stimuli[video_idx].movement, 'actr' : self.stimuli[video_idx].actor})
            while not self.stimuli[video_idx].stim.status==visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
                self.win.flip()

            all_keys=event.getKeys()

            # Tell netstation the movie has stopped
            sendEvent(ns, 'mov2', 'movie end', {})

            if len(all_keys):
                # Quit task
                if all_keys[0].upper() in ['Q','ESCAPE']:
                    self.win.close()
                    core.quit()
                # Pause block
                elif all_keys[0].upper()=='P':
                    self.pause()
                # End block
                elif all_keys[0].upper()=='E':
                    break

            # Black screen for delay
            for i in range(delay_frames):
                self.win.flip()

        # Stop netstation recording
        sendEvent(ns, 'blck', 'block end', {'code' : self.code} )


class MovieStimulus:
    """
    A movie stimulus
    """

    def __init__(self, win, movement, actor, file_name):
        """
        win - window to show movie in
        movement - movement being made in movie
        actor - ID of actor
        file_name - file containing movie
        """
        self.actor=actor
        self.movement=movement
        self.file_name=file_name
        self.stim=visual.MovieStim(win, os.path.join(DATA_DIR,'movies',self.file_name),size=(900,720))

    def reload(self, win):
        self.stim=visual.MovieStim(win, os.path.join(DATA_DIR,'movies',self.file_name),size=(900,720))


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
        #ns.connect(NETSTATION_IP, 55513)
            ns.initialize(NETSTATION_IP, 55513)
            ns.BeginSession()
            ns.StartRecording()
    except:
        print('Could not connect with NetStation!')
        ns=None

    # run task
    exp=Experiment(os.path.join(CONF_DIR,'emotion_faces_experiment.xml'))
    exp.run(ns)

    # close netstation connection
    if ns:
        ns.StopRecording()
        ns.EndSession()
        #ns.disconnect()
        ns.finalize()