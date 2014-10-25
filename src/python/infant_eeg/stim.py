import os
from psychopy import visual
from infant_eeg.config import DATA_DIR

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