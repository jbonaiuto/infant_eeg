import math
from psychopy.tools.monitorunittools import deg2pix
from egi import threaded as egi

def sendEvent(ns, eye_tracker, code, label, table):
    if ns is not None:
        ns.send_event(code, label=label, timestamp=egi.ms_localtime(), table=table)
    if eye_tracker is not None:
        eye_tracker.recordEvent(code)


def deg2norm_x(position, window):
    pix=deg2pix(position,window.monitor)
    return pix2norm_x(pix, window)

def deg2norm_y(position, window):
    pix=deg2pix(position,window.monitor)
    return pix2norm_y(pix, window)

def pix2norm_x(position, window):
    scrSizePix=window.size
    return position/(scrSizePix[0]*.5)

def pix2norm_y(position, window):
    scrSizePix=window.size
    return position/(scrSizePix[1]*.5)

def get_dist(pos1, pos2, aspect=1.0):
    return math.sqrt((pos1[0]-pos2[0])**2.0+((pos1[1]-pos2[1])/aspect)**2.0)

def fixation_within_tolerance(gaze_position, position, tolerance, win):
    aspect=float(win.size[0]/win.size[1])
    tolerance_norm=deg2norm_x(tolerance,win)
    gaze_norm=(deg2norm_x(gaze_position[0],win),deg2norm_y(gaze_position[1],win))
    pos_norm=(deg2norm_x(position[0],win),deg2norm_y(position[1],win))
    fixation_dist=get_dist(gaze_norm, pos_norm, aspect=aspect)
    return fixation_dist<tolerance_norm