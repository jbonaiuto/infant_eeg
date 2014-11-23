import os
from psychopy import data, gui
from infant_eeg.config import CONF_DIR
from infant_eeg.facial_movement_exp import FacialMovementExperiment
from infant_eeg.gaze_following_exp import GazeFollowingExperiment

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
        'experiment': ['FacialMovement','GazeFollowing'],
        'eye tracking': False,
        'debug mode': False
    }

    #present a dialogue to change params
    dlg = gui.DlgFromDict(
        expInfo,
        order=['experiment','experimenter_id','date','child_id','gender','diagnosis','age','session','eye tracking','debug mode'],
        title='Experiment Settings',
        fixed=['dateStr']
    )
    if dlg.OK:
        # run task
        exp=None
        if expInfo['experiment']=='FacialMovement':
            exp=FacialMovementExperiment(expInfo,os.path.join(CONF_DIR,'facial_movement_experiment.xml'))
        elif expInfo['experiment']=='GazeFollowing':
            exp=GazeFollowingExperiment(expInfo,os.path.join(CONF_DIR,'gaze_following_experiment.xml'))
        if exp is not None:
            exp.run()

