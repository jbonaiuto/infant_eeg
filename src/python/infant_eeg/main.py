from infant_eeg.facial_movement_exp import FacialMovementExperiment
from infant_eeg.gaze_following_exp import GazeFollowingExperiment
import os
from psychopy import data, gui
from infant_eeg.config import CONF_DIR

if __name__ == '__main__':
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
        'congruent_actor': ['CG', 'FO'],
        'incongruent_actor': ['CG', 'FO'],
        'eeg': True,
        'eyetracking source': ['tobii', 'mouse', 'none'],
        'debug': False
    }

    #present a dialogue to change params
    dlg = gui.DlgFromDict(
        expInfo,
        order=['experiment','experimenter_id','date','child_id','gender','diagnosis','age','session','congruent_actor',
               'incongruent_actor','eeg', 'eye tracking_source','debug mode'],
        title='Experiment Settings',
        fixed=['dateStr']
    )
    if dlg.OK:
        # run experiment
        exp = None
        if expInfo['experiment'] == 'FacialMovement':
            exp = FacialMovementExperiment(expInfo, os.path.join(CONF_DIR, 'facial_movement_experiment.xml'))
        elif expInfo['experiment'] == 'GazeFollowing':
            exp = GazeFollowingExperiment(expInfo, os.path.join(CONF_DIR, 'gaze_following_experiment.xml'))
        if exp is not None:
            exp.run()