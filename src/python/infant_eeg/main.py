import os
from psychopy import data, gui, event, visual, sound
from psychopy.visual import Window
from infant_eeg.config import MONITOR, SCREEN, NETSTATION_IP, DATA_DIR
import egi.simple as egi
import numpy as np

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

# Window to use
wintype='pyglet' # use pyglet if possible, it's faster at event handling
win = Window(
    [1600,900],
    monitor=MONITOR,
    screen=SCREEN,
    units="deg",
    fullscr=True,
    color=[-1,-1,-1],
    winType=wintype)
win.setMouseVisible(False)
event.clearEvents()

distractor_picture_file_names=[
    'alien1.jpg','alien2.jpg','alien3.jpg','alien5.jpg','alien6.jpg','moon3.jpg','planet2.jpg','planet3.jpg',
    'rocket1.jpg','rocket2.jpg','sun1.jpg'
]
distractor_pictures=[]
for file in distractor_picture_file_names:
    distractor_pictures.append(visual.ImageStim(win, os.path.join(DATA_DIR,'images',file)))

distractor_sound_file_names=[
    'ascend.wav','descend.wav','sound1.wav','sound2.wav','sound3.wav','sound4.wav','sound5.wav','whistle.wav'
]
distractor_sounds=[]
for file in distractor_sound_file_names:
    distractor_sounds.append(sound.Sound(os.path.join(DATA_DIR,'sounds',file)))

star_picture=visual.ImageStim(win,os.path.join(DATA_DIR,'images','star-cartoon.jpg'))

block_movie_file_names={
    'joy': ['F01-Joy-Face Forward.mpg','F03-Joy-Face Forward.mpg'],
    'sad': ['F01-Sadness-Face Forward.mpg','F03-Sadness-Face Forward.mpg'],
    'move': ['F06-MouthOpening-Face Forward.mpg','F07-MouthOpening-Face Forward.mpg'],
    'shuffled': ['F01-Joy-Face Forward.shuffled.mpg','F01-Sadness-Face Forward.shuffled.mpg',
                 'F03-Joy-Face Forward.shuffled.mpg','F03-Sadness-Face Forward.shuffled.mpg',
                 'F06-MouthOpening-Face Forward.shuffled.mpg','F07-MouthOpening-Face Forward.shuffled.mpg']
}

block_movies={}
for block_name, files in block_movie_file_names.iteritems():
    block_movies[block_name]=[]
    for file in files:
        block_movies[block_name].append(visual.MovieStim(win, os.path.join(DATA_DIR,'movies',file),
            size=(win.size[0],win.size[1])))

n_blocks=20
block_order=[]
while len(block_order)<n_blocks:
    block_order.extend(block_movie_file_names.keys())
np.random.shuffle(block_order)

def run_block(block_name, trials, min_delay_frames, max_delay_frames):
    n_movies=len(block_movies[block_name])
    vid_order=range(n_movies)
    if n_movies<trials:
        vid_order=[]
        while len(vid_order)<trials:
            vid_order.extend(range(n_movies))
    np.random.shuffle(vid_order)
    for t in range(trials):
        delay_frames=min_delay_frames+int(np.random.rand()*(max_delay_frames-min_delay_frames))
        video_idx=vid_order[t]
        video_stim=block_movies[block_name][video_idx]
        video_stim.seek(0)
        video_stim.status=0
        while not video_stim.status==visual.FINISHED:
            video_stim.draw()
            win.flip()
        for i in range(delay_frames):
            win.flip()

def run_distractor(distractor_duration_frames):
    # clear any keystrokes before starting
    event.clearEvents()
    all_keys=[]

    # wait for a keypress
    while len(all_keys)==0:
        distractor_picture_idx=np.random.choice(range(len(distractor_pictures)))
        distractor_sound_idx=np.random.choice(range(len(distractor_sounds)))
        distractor_sounds[distractor_sound_idx].play()
        for i in range(distractor_duration_frames):
            distractor_pictures[distractor_picture_idx].draw()
            win.flip()
        all_keys=event.getKeys()

    # clear any keystrokes before starting
    event.clearEvents()
    all_keys=[]
    # wait for a keypress
    while len(all_keys)==0:
        star_picture.draw()
        win.flip()
        all_keys=event.getKeys()

# Measure frame rate
mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame=visual.getMsPerFrame(win, nFrames=60, showVisual=True)
min_delay_ms=800.0
max_delay_ms=1200.0
min_delay_frames=int(min_delay_ms/mean_ms_per_frame)
max_delay_frames=int(max_delay_ms/mean_ms_per_frame)
distractor_duration_ms=2000.0
distractor_duration_frames=int(distractor_duration_ms/mean_ms_per_frame)

egi_connected=False
ns = egi.Netstation()
ms_localtime = egi.ms_localtime
#try:
#    ns.connect(NETSTATION_IP, 55513)
#    ns.BeginSession()
#
#    ns.sync()
#
#
#    ns.StartRecording()
#    egi_connected=True
#except:
#    print('Could not connect with NetStation!')
#    egi_connected=False



#if egi_connected:
#    ## # optionally can perform additional synchronization
#    ## ns.sync()
#    ns.send_event( 'evt_', label="event", timestamp=egi.ms_localtime(), table = {'fld1' : 123, 'fld2' : "abc", 'fld3' : 0.042} )

for block_name in block_order:
    run_distractor(distractor_duration_frames)
    run_block(block_name,6,min_delay_frames,max_delay_frames)

#video_stim=visual.MovieStim(win, os.path.join(DATA_DIR,'movies','nat-oxen.mpg.avi'),size=(win.size[0],win.size[1]))
#video_stim.seek(0)
#while not video_stim.status==visual.FINISHED:
#    video_stim.draw()
#    win.flip()

# >>> we have sent all we wanted, time to go home >>>
if egi_connected:
    ns.StopRecording()


    ns.EndSession()
    ns.disconnect()