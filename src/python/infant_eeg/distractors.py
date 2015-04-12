import numpy as np
import os
from psychopy import visual, sound, event

class DistractorSet:
    """
    A set of distractor images and sounds
    """

    def __init__(self, image_path, sound_path, video_path, reward_image_file, duration_frames, win):
        """
        image_path - path to load distractor images from
        sound_path - path to load distractor sounds from
        video_path - path to load distractor videos from
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

        # find videos
        self.video_files = [os.path.join(video_path,f) for f in os.listdir(video_path) if os.path.isfile(os.path.join(video_path, f))]

        # load reward image
        self.reward_image = visual.ImageStim(win, reward_image_file)

        self.last_video_played=-1
        self.last_picture_shown=-1
        self.last_sound_played=-1

        self.duration_frames = duration_frames

    def show_pictures_and_sounds(self):
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
            valid=False
            while not valid:
                distractor_picture_idx = np.random.choice(range(len(self.pictures)))
                distractor_sound_idx = np.random.choice(range(len(self.sounds)))
                if not distractor_picture_idx==self.last_picture_shown and not distractor_sound_idx==self.last_sound_played:
                    valid=True
            self.last_picture_shown=distractor_picture_idx
            self.last_sound_played=distractor_sound_idx

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
        elif this_key == 'V':
            self.show_video()

    def show_video(self):
        # clear any keystrokes before starting
        event.clearEvents()
        all_keys = []

        # Pick a video at random
        valid=False
        while not valid:
            video_idx=np.random.choice(range(len(self.video_files)))
            if not video_idx==self.last_video_played:
                valid=True
        self.last_video_played=video_idx

        video = visual.MovieStim(self.win, self.video_files[video_idx], size=[1280, 1024])

        # wait for a keypress
        while len(all_keys) == 0 and not video.status==visual.FINISHED:
            video.draw()
            self.win.flip()
            # Look for key press
            all_keys = event.getKeys()
        video.stop()