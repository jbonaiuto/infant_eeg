import os
from psychopy import visual
from infant_eeg.config import DATA_DIR


class MovieStimulus:
    """
    A movie stimulus
    """

    def __init__(self, win, movement, actor, file_name, size, code=None):
        """
        Initialize class
        :param: win - window to show movie in
        :param: movement - movement being made in movie
        :param: actor - ID of actor
        :param: file_name - file containing movie
        """
        self.actor = actor
        self.movement = movement
        self.file_name = file_name
        self.stim = None
        self.size = size
        self.code=code
        self.reload(win)

    def reload(self, win):
        """
        Reload video - set to beginning
        :param win: window movie is playing in
        """
        self.stim = visual.MovieStim(win, os.path.join(DATA_DIR, 'movies', self.file_name), units='deg', size=self.size)