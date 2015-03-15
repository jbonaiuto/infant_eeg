import math
#from psychopy.tools.monitorunittools import deg2pix
from psychopy.misc import deg2pix
from egi import threaded as egi
from infant_eeg.experiment import Event


def send_event(ns, eye_tracker, code, label, table):
    trial_event=Event(code, label, table)
    if ns is not None:
        ns.send_event(trial_event.code, label=trial_event.label, timestamp=trial_event.timestamp, table=trial_event.table)
    if eye_tracker is not None:
        eye_tracker.recordEvent(trial_event)


def deg2norm_x(position, window):
    return pix2norm_x(deg2pix(position, window.monitor), window)


def deg2norm_y(position, window):
    return pix2norm_y(deg2pix(position, window.monitor), window)


def pix2norm_x(position, window):
    return position/(window.size[0]*.5)


def pix2norm_y(position, window):
    return position/(window.size[1]*.5)


def get_dist(pos1, pos2, aspect=1.0):
    return math.sqrt((pos1[0]-pos2[0])**2.0+((pos1[1]-pos2[1])/aspect)**2.0)


def fixation_within_tolerance(gaze_position, position, tolerance, win):
    aspect = float(win.size[0]/win.size[1])
    tolerance_norm = deg2norm_x(tolerance, win)
    gaze_norm = (deg2norm_x(gaze_position[0], win), deg2norm_y(gaze_position[1], win))
    pos_norm = (deg2norm_x(position[0], win), deg2norm_y(position[1], win))
    fixation_dist = get_dist(gaze_norm, pos_norm, aspect=aspect)
    return fixation_dist<tolerance_norm

def draw_eye_debug(gaze_debug, eyetracker, mouse):
    if gaze_debug is not None:
        gaze_position=None
        if eyetracker is not None:
            gaze_position = eyetracker.getCurrentGazePosition()
            if gaze_position[0] is not None:
                gaze_position=(0.5*(gaze_position[0]+gaze_position[2]), 0.5*(gaze_position[1]+gaze_position[3]))
        elif mouse is not None:
            gaze_position = mouse.getPos()
        if gaze_position[0] is not None:
            gaze_debug.setPos(gaze_position)
            gaze_debug.draw()