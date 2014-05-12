import os
from psychopy import data, gui, event, visual, sound
from psychopy.visual import Window
from infant_eeg.config import MONITOR, SCREEN, NETSTATION_IP, DATA_DIR
import egi.simple as egi
import numpy as np

class Task:
    def __init__(self, n_blocks, n_trials, distractor_duration_ms, min_delay_ms, max_delay_ms, ns):
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

        min_delay_frames=int(min_delay_ms/self.mean_ms_per_frame)
        max_delay_frames=int(max_delay_ms/self.mean_ms_per_frame)

        self.blocks={
            'joy': Block('joy', n_trials, min_delay_frames, max_delay_frames, self.win),
            'sad': Block('sad', n_trials, min_delay_frames, max_delay_frames, self.win),
            'move': Block('move', n_trials, min_delay_frames, max_delay_frames, self.win),
            'shuf': Block('shuf', n_trials, min_delay_frames, max_delay_frames, self.win)
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

        self.n_blocks=n_blocks
        self.block_order=[]
        while len(self.block_order)<n_blocks:
            self.block_order.extend(self.blocks.keys())
        np.random.shuffle(self.block_order)

        distractor_duration_frames=int(distractor_duration_ms/self.mean_ms_per_frame)
        self.distractor_set=DistractorSet(os.path.join(DATA_DIR,'images','distractors','space'),
            os.path.join(DATA_DIR,'sounds','distractors'),distractor_duration_frames, self.win)

    def run(self):
        for block_name in self.block_order:
            self.distractor_set.run()
            if self.ns is not None:
                self.ns.sync()
            self.blocks[block_name].run()


class Block:
    def __init__(self, code, trials, min_delay_frames, max_delay_frames, win, ns):
        self.code=code
        self.trials=trials
        self.win=win
        self.min_delay_frames=min_delay_frames
        self.max_delay_frames=max_delay_frames
        self.ns=ns
        self.stimuli=[]        
    
    def add_stimulus(self, actor, file_name):
        stim=MovieStimulus(self.win, actor, file_name)
        self.stimuli.append(stim)

    def run(self):
        n_movies=len(self.stimuli)
        vid_order=range(n_movies)
        if n_movies<self.trials:
            vid_order=[]
            while len(vid_order)<self.trials:
                vid_order.extend(range(n_movies))
        np.random.shuffle(vid_order)

        self.ns.StartRecording()
        self.ns.sync()
        self.ns.send_event( 'blck', label="block start", timestamp=egi.ms_localtime(), table = {'code' : self.code} )

        for t in range(self.trials):
            delay_frames=self.min_delay_frames+int(np.random.rand()*(self.max_delay_frames-self.min_delay_frames))
            video_idx=vid_order[t]
            self.stimuli[video_idx].stim.seek(0)
            self.stimuli[video_idx].stim.status=0
            self.ns.send_event( 'mov_', label="movie start", timestamp=egi.ms_localtime(),
                table = {'code' : self.code, 'actr' : self.stimuli[video_idx].actor} )
            while not self.stimuli[video_idx].stim.status==visual.FINISHED:
                self.stimuli[video_idx].stim.draw()
                self.win.flip()
            self.ns.send_event( 'mov_', label="movie end", timestamp=egi.ms_localtime())
            for i in range(delay_frames):
                self.win.flip()

        self.ns.StopRecording()


class MovieStimulus:
    def __init__(self, win, actor, file_name):
        self.actor=actor
        self.file_name=file_name
        self.stim=visual.MovieStim(win, os.path.join(DATA_DIR,'movies',self.file_name))


class DistractorSet:
    def __init__(self, image_path, sound_path, duration_frames, win):
        self.win=win
        self.pictures=[]
        image_files = [ f for f in os.listdir(image_path) if os.path.isfile(os.path.join(image_path,f)) ]
        for file in image_files:
            self.pictures.append(visual.ImageStim(win, os.path.join(image_path,file)))

        self.sounds=[]
        sound_files = [ f for f in os.listdir(sound_path) if os.path.isfile(os.path.join(sound_path,f)) ]
        for file in sound_files:
            self.sounds.append(sound.Sound(os.path.join(sound_path,file)))

        self.star_picture=visual.ImageStim(win,os.path.join(DATA_DIR,'images','distractors','star-cartoon.jpg'))

        self.duration_frames=duration_frames

    def run(self):
        # clear any keystrokes before starting
        event.clearEvents()
        all_keys=[]

        # wait for a keypress
        while len(all_keys)==0:
            distractor_picture_idx=np.random.choice(range(len(self.pictures)))
            distractor_sound_idx=np.random.choice(range(len(self.sounds)))
            self.sounds[distractor_sound_idx].play()
            for i in range(self.duration_frames):
                self.pictures[distractor_picture_idx].draw()
                self.win.flip()
            all_keys=event.getKeys()

        # clear any keystrokes before starting
        event.clearEvents()
        all_keys=[]
        # wait for a keypress
        while len(all_keys)==0:
            self.star_picture.draw()
            self.win.flip()
            all_keys=event.getKeys()


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

ns = egi.Netstation()
ms_localtime = egi.ms_localtime
try:
    ns.connect(NETSTATION_IP, 55513)
    ns.BeginSession()
    ns.sync()
except:
    print('Could not connect with NetStation!')
    ns=None

task=Task(20, 6, 2000.0, 800.0, 1200.0, ns)
task.run()

if ns:
    ns.EndSession()
    ns.disconnect()