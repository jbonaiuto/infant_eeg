import numpy as np
import os
from psychopy import visual, sound, event

__author__ = 'jbonaiuto'


class DistractorSet:
    """
    A set of distractor images and sounds
    """

    def __init__(self, image_path, sound_path, reward_image_file, duration_frames, win):
        """
        image_path - path to load distractor images from
        sound_path - path to load distractor sounds from
        reward_image_file - file containing reward image
        duration_frames - duration of each distractor image in frames
        win - window to display images in
        """
        self.win = win

        # load images
        self.pictures = []
        image_files = [f for f in os.listdir(image_path) if os.path.isfile(os.path.join(image_path, f))]
        for f in image_files:
            self.pictures.append(visual.ImageStim(win, os.path.join(image_path, f)))

        # load sounds
        self.sounds = []
        sound_files = [f for f in os.listdir(sound_path) if os.path.isfile(os.path.join(sound_path, f))]
        for f in sound_files:
            self.sounds.append(sound.Sound(os.path.join(sound_path, f)))

        # load reward image
        self.reward_image = visual.ImageStim(win, reward_image_file)

        self.duration_frames = duration_frames

    def run(self):
        """
        Run distractor set
            returns True if calibration requested
            returns False otherwise
        """
        # clear any keystrokes before starting
        event.clearEvents()
        all_keys = []

        # wait for a keypress
        while len(all_keys) == 0:
            # Pick random picture and sound
            distractor_picture_idx = np.random.choice(range(len(self.pictures)))
            distractor_sound_idx = np.random.choice(range(len(self.sounds)))

            # Play sound
            self.sounds[distractor_sound_idx].play()
            # Show picture
            for i in range(self.duration_frames):
                self.pictures[distractor_picture_idx].draw()
                self.win.flip()

            # Look for key press
            all_keys = event.getKeys()

        # taking the first keypress in the list
        this_key = all_keys[0].upper()
        # show reward image if R pressed
        if this_key == 'R':
            # clear any keystrokes before starting
            event.clearEvents()
            all_keys = []

            # show reward image until keypress
            while len(all_keys) == 0:
                self.reward_image.draw()
                self.win.flip()
                all_keys = event.getKeys()