from infant_eeg.facial_movement_exp import FacialMovementExperiment
from infant_eeg.gaze_following_exp import GazeFollowingExperiment
import os
from psychopy import data, gui
from infant_eeg.config import CONF_DIR
from infant_eeg.nine_month_facial_movement_exp import NineMonthFacialMovementExperiment

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
        'monitor': ['viewsonic','tobii'],
        'monitor distance': '65',
        'experiment': ['FacialMovement','GazeFollowing','9mo FacialMovement'],
        'congruent actor': ['CG', 'FO'],
        'incongruent actor': ['CG', 'FO'],
        'preferential gaze': False,
        'eeg': True,
        'eyetracking source': ['tobii', 'mouse', 'none'],
        'debug mode': False
    }

    #present a dialogue to change params
    dlg = gui.DlgFromDict(
        expInfo,
        order=['experiment', 'experimenter_id', 'date', 'child_id', 'gender', 'diagnosis', 'age', 'session',
               'congruent actor', 'incongruent actor', 'preferential gaze', 'monitor','monitor distance', 'eeg',
               'eyetracking source', 'debug mode'],
        title='Experiment Settings',
        fixed=['dateStr']
    )
    if dlg.OK:
        # run experiment
        exp = None
        if expInfo['experiment'] == 'FacialMovement':
            exp = FacialMovementExperiment(expInfo, os.path.join(CONF_DIR, 'facial_movement_experiment.xml'))
        elif expInfo['experiment'] == '9mo FacialMovement':
            exp = NineMonthFacialMovementExperiment(expInfo, os.path.join(CONF_DIR, '9m_facial_movement_experiment.xml'))
        elif expInfo['experiment'] == 'GazeFollowing':
            exp = GazeFollowingExperiment(expInfo, os.path.join(CONF_DIR, 'gaze_following_experiment.xml'))
        if exp is not None:
            exp.run()