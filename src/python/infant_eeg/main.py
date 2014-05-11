from psychopy import data, gui, event, visual
from psychopy.visual import Window
from infant_eeg.config import MONITOR, SCREEN

# experiment parameters
expInfo = {
    'subject': '',
    'dateStr': data.getDateStr(),
    'condition': ''
}

#present a dialogue to change params
dlg = gui.DlgFromDict(
    expInfo,
    title='RDMD',
    fixed=['dateStr']
)

# Window to use
wintype='pyglet' # use pyglet if possible, it's faster at event handling
win = Window(
    [1280,1024],
    monitor=MONITOR,
    screen=SCREEN,
    units="deg",
    fullscr=True,
    color=[-1,-1,-1],
    winType=wintype)
win.setMouseVisible(False)
event.clearEvents()

# Measure frame rate
mean_ms_per_frame, std_ms_per_frame, median_ms_per_frame=visual.getMsPerFrame(win, nFrames=60, showVisual=True)