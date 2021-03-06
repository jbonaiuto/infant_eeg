#!/usr/bin/python
#
# Tobii controller for PsychoPy
# authors: Hiroyuki Sogo, Horea Christian
# - Tobii SDK 3.0 is required
#

import datetime
import os
from math import degrees, atan2
# from psychopy.tools.monitorunittools import pix2deg
from psychopy.misc import pix2deg

import tobii.sdk.mainloop
import tobii.sdk.time.clock
import tobii.sdk.time.sync
import tobii.sdk.browsing
import tobii.sdk.eyetracker

import psychopy.visual
import psychopy.event

import Image
import ImageDraw
from tobii.sdk.types import Point2D
from infant_eeg.config import DATA_DIR


class TobiiController:
    def __init__(self, win):
        self.eyetracker = None
        self.eyetrackers = {}
        self.win = win
        self.gazeData = []
        self.eventData = []
        self.datafile = None

        tobii.sdk.init()
        self.clock = tobii.sdk.time.clock.Clock()
        self.mainloop_thread = tobii.sdk.mainloop.MainloopThread()
        self.browser = tobii.sdk.browsing.EyetrackerBrowser(self.mainloop_thread,
                                                            lambda t, n, i: self.on_eyetracker_browser_event(t, n, i))
        self.mainloop_thread.start()

    def waitForFindEyeTracker(self):
        while len(self.eyetrackers.keys()) == 0:
            pass

    def on_eyetracker_browser_event(self, event_type, event_name, eyetracker_info):
        # When a new eyetracker is found we add it to the treeview and to the 
        # internal list of eyetracker_info objects
        if event_type == tobii.sdk.browsing.EyetrackerBrowser.FOUND:
            self.eyetrackers[eyetracker_info.product_id] = eyetracker_info
            return False

        # Otherwise we remove the tracker from the treeview and the eyetracker_info list...
        del self.eyetrackers[eyetracker_info.product_id]

        # ...and add it again if it is an update message
        if event_type == tobii.sdk.browsing.EyetrackerBrowser.UPDATED:
            self.eyetrackers[eyetracker_info.product_id] = eyetracker_info
        return False

    def destroy(self):
        self.eyetracker = None
        self.browser.stop()
        self.browser = None
        self.mainloop_thread.stop()

    ############################################################################
    # activation methods
    ############################################################################
    def activate(self, eyetracker):
        eyetracker_info = self.eyetrackers[eyetracker]
        print "Connecting to:", eyetracker_info
        tobii.sdk.eyetracker.Eyetracker.create_async(self.mainloop_thread,
                                                     eyetracker_info,
                                                     lambda error, eyetracker: self.on_eyetracker_created(error,
                                                                                                          eyetracker,
                                                                                                          eyetracker_info))

        while self.eyetracker is None:
            pass
        self.syncmanager = tobii.sdk.time.sync.SyncManager(self.clock, eyetracker_info, self.mainloop_thread)

    def on_eyetracker_created(self, error, eyetracker, eyetracker_info):
        if error:
            print "  Connection to %s failed because of an exception: %s" % (eyetracker_info, error)
            if error == 0x20000402:
                print "The selected unit is too old, a unit which supports protocol version 1.0 is required.\n\n<b>Details:</b> <i>%s</i>" % error
            else:
                print "Could not connect to %s" % eyetracker_info
            return False

        self.eyetracker = eyetracker

    ############################################################################
    # calibration methods
    ############################################################################

    def calibratePoint(self, clock, last_pos, p):
        clock.reset()
        currentTime = clock.getTime()
        x_diff = p.x - last_pos.x
        y_diff = p.y - last_pos.y
        angle = degrees(atan2(y_diff, x_diff)) + 90
        self.rocket_img.setOri(angle)
        while currentTime <= 1.5:
            rel_pos = Point2D()
            rel_pos.x = last_pos.x + ((currentTime / 1.5) * (p.x - last_pos.x))
            rel_pos.y = last_pos.y + ((currentTime / 1.5) * (p.y - last_pos.y))
            self.rocket_img.setPos((pix2deg((rel_pos.x - 0.5) * self.win.size[0], self.win.monitor),
                                    pix2deg((0.5 - rel_pos.y) * self.win.size[1], self.win.monitor)))
            self.rocket_img.setSize((pix2deg(110.67 * (1.5 - currentTime) + 4, self.win.monitor),
                                     pix2deg(196 * (1.5 - currentTime) + 4, self.win.monitor)))
            psychopy.event.getKeys()
            self.rocket_img.draw()
            self.win.flip()
            currentTime = clock.getTime()
        self.add_point_completed = False
        self.eyetracker.AddCalibrationPoint(p, lambda error, r: self.on_add_completed(error, r))
        while not self.add_point_completed:
            psychopy.event.getKeys()
            self.rocket_img.draw()
            self.win.flip()

    def doCalibration(self, calibrationPoints, calib=None):
        # Can only calibrate with eyetracker
        if self.eyetracker is None:
            return

        # Points to calibrate
        self.points = calibrationPoints
        self.point_index = -1

        # Rocket image
        self.rocket_img = psychopy.visual.ImageStim(self.win, os.path.join(DATA_DIR, 'images', 'rocket.png'))
        # Results image
        img = Image.new('RGB', self.win.size)
        draw = ImageDraw.Draw(img)
        self.calresult = psychopy.visual.SimpleImageStim(self.win, img)
        # Results message
        self.calresultmsg = psychopy.visual.TextStim(self.win, pos=(pix2deg(0, self.win.monitor),
                                                                    pix2deg(-self.win.size[1] / 4, self.win.monitor)))
        # Calibration point labels
        if calib is None:
            self.point_labels=[]

        # Start calibration instruction
        self.calresultmsg.setText('Start calibration:SPACE')
        # Left eye status
        self.left_eye_status = psychopy.visual.Circle(self.win, radius=pix2deg(40, self.win.monitor),
                                                      pos=(pix2deg(-50, self.win.monitor),
                                                           pix2deg(-self.win.size[1] / 3, self.win.monitor)))
        # Right eye status
        self.right_eye_status = psychopy.visual.Circle(self.win, radius=pix2deg(40, self.win.monitor),
                                                       pos=(pix2deg(50, self.win.monitor),
                                                            pix2deg(-self.win.size[1] / 3, self.win.monitor)))

        # Reset gaze and event data and start tracking
        self.gazeData = []
        self.eventData = []
        self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
        self.eyetracker.StartTracking()

        # Wait until space key is hit
        waitkey = True
        while waitkey:
            for key in psychopy.event.getKeys():
                if key == 'space':
                    waitkey = False
            self.rocket_img.draw()
            self.calresultmsg.draw()
            self.left_eye_status.fillColor = 'red'
            self.right_eye_status.fillColor = 'red'
            if len(self.gazeData):
                if self.gazeData[-1].LeftValidity != 4:
                    self.left_eye_status.fillColor = 'green'
                if self.gazeData[-1].RightValidity != 4:
                    self.right_eye_status.fillColor = 'green'
            self.left_eye_status.draw()
            self.right_eye_status.draw()
            self.win.flip()

        # Stop tracking and reset gaze data
        self.eyetracker.StopTracking()
        self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata
        self.gazeData = []
        self.eventData = []

        # Initialize calibration
        self.initcalibration_completed = False
        print "Init calibration"
        self.eyetracker.StartCalibration(lambda error, r: self.on_calib_start(error, r))
        while not self.initcalibration_completed:
            pass

        # If we're updating a calibration
        if calib is not None:
            # Set calibration
            self.setcalibration_completed=False
            self.eyetracker.SetCalibration(self.calib,lambda error, r: self.on_calib_set(error, r))
            while not self.setcalibration_completed:
                pass

        # Calibrate each point
        clock = psychopy.core.Clock()
        last_pos = Point2D(x=0.5, y=0.5)
        for self.point_index in range(len(self.points)):
            p = Point2D()
            p.x, p.y = self.points[self.point_index]
            self.calibratePoint(clock, last_pos, p)
            last_pos = Point2D(x=p.x, y=p.y)

        # Compute calibration
        self.computeCalibration_completed = False
        self.computeCalibration_succeeded = False
        self.eyetracker.ComputeCalibration(lambda error, r: self.on_calib_compute(error, r))
        while not self.computeCalibration_completed:
            pass
        # Stop calibration
        self.eyetracker.StopCalibration(None)

        self.win.flip()

        # Get calibration
        self.getcalibration_completed = False
        self.calib = self.eyetracker.GetCalibration(lambda error, calib: self.on_calib_response(error, calib))
        while not self.getcalibration_completed:
            pass

        draw.rectangle(((0, 0), tuple(self.win.size)), fill=(128, 128, 128))

        can_accept=False
        if not self.computeCalibration_succeeded:
            #computeCalibration failed.
            self.calresultmsg.setText('Not enough data was collected (Retry:r/Abort:ESC)')

        elif self.calib == None:
            #no calibration data
            self.calresultmsg.setText('No calibration data (Retry:r/Abort:ESC)')
        else:
            can_accept=True
            point_list = []
            points = {}
            for data in self.calib.plot_data:
                points[data.true_point] = {'left': data.left, 'right': data.right}
                point_list.append(data.true_point)

            if len(point_list) == 0:
                self.calresultmsg.setText('No true calibration data (Retry:r/Abort:ESC)')

            else:
                for idx,(x,y) in enumerate(self.points):
                    draw.ellipse(((x * self.win.size[0] - 10,
                                   y * self.win.size[1] - 10),
                                  (x * self.win.size[0] + 10,
                                   y * self.win.size[1] + 10)),
                                 outline=(0, 0, 0))
                    if calib is None:
                        num_txt=psychopy.visual.TextStim(self.win, pos=(pix2deg((x-0.5) * self.win.size[0] - 10, self.win.monitor),
                                                                        pix2deg((0.5-y) * self.win.size[1] - 20, self.win.monitor)))
                        num_txt.setText(str(idx+1))
                        self.point_labels.append(num_txt)
                for idx,p in enumerate(point_list):
                    d = points[p]
                    draw.ellipse(((p.x * self.win.size[0] - 10,
                                   p.y * self.win.size[1] - 10),
                                  (p.x * self.win.size[0] + 10,
                                   p.y * self.win.size[1] + 10)),
                                 outline=(0, 0, 0))
                    if d['left'].validity == 1:
                        draw.line(((p.x * self.win.size[0],
                                    p.y * self.win.size[1]),
                                   (d['left'].map_point.x * self.win.size[0],
                                    d['left'].map_point.y * self.win.size[1])), fill=(255, 0, 0))
                    if d['right'].validity == 1:
                        draw.line(((p.x * self.win.size[0],
                                    p.y * self.win.size[1]),
                                   (d['right'].map_point.x * self.win.size[0],
                                    d['right'].map_point.y * self.win.size[1])), fill=(0, 255, 0))

                self.calresultmsg.setText('Accept calibration results (Accept:a/Redo:#/Retry:r/Abort:ESC)')

            self.calresult.setImage(img)

        return can_accept


    def on_calib_start(self, error, r):
        if error:
            print "Could not start calibration because of error. (0x%0x)" % error
            return False
        self.initcalibration_completed = True

    def on_add_completed(self, error, r):
        if error:
            print "Add Calibration Point failed because of error. (0x%0x)" % error
            return False

        self.add_point_completed = True
        return False

    def on_remove_completed(self, error):
        if error:
            print "Remove Calibration Point failed because of error. (0x%0x)" % error
        self.remove_point_completed = True
        return False

    def on_calib_compute(self, error, r):
        if error == 0x20000502:
            print "CalibCompute failed because not enough data was collected:", error
            print "Not enough data was collected during calibration procedure."
            self.computeCalibration_succeeded = False
        elif error != 0:
            print "CalibCompute failed because of a server error:", error
            print "Could not compute calibration because of a server error.\n\n<b>Details:</b>\n<i>%s</i>" % error
            self.computeCalibration_succeeded = False
        else:
            print ""
            self.computeCalibration_succeeded = True

        self.computeCalibration_completed = True
        return False

    def on_calib_response(self, error, calib):
        if error:
            print "On_calib_response: Error =", error
            self.calib = None
            self.getcalibration_completed = True
            return False

        print "On_calib_response: Success"
        self.calib = calib
        self.getcalibration_completed = True
        return False

    def on_calib_set(self, error, r):
        if error:
            print "Set Calibration failed because of error. (0x%0x)" % error
            return False
        self.setcalibration_completed=True
        return False

    def on_calib_done(self, status, msg):
        # When the calibration procedure is done we update the calibration plot
        if not status:
            print msg

        self.calibration = None
        return False

    def startTracking(self):
        self.gazeData = []
        self.eventData = []
        self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
        self.eyetracker.StartTracking()

    def stopTracking(self):
        self.eyetracker.StopTracking()
        self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata
        self.flushData()
        self.gazeData = []
        self.eventData = []

    def on_gazedata(self, error, gaze):
        self.gazeData.append(gaze)

    def getGazePosition(self, gaze):
        return ((pix2deg((gaze.LeftGazePoint2D.x - 0.5) * self.win.size[0], self.win.monitor),
                 pix2deg((0.5 - gaze.LeftGazePoint2D.y) * self.win.size[1], self.win.monitor),
                 pix2deg((gaze.RightGazePoint2D.x - 0.5) * self.win.size[0], self.win.monitor),
                 pix2deg((0.5 - gaze.RightGazePoint2D.y) * self.win.size[1], self.win.monitor)))

    def getCurrentGazePosition(self):
        if len(self.gazeData) == 0:
            return (None, None, None, None)
        else:
            return self.getGazePosition(self.gazeData[-1])

    def setDataFile(self, filename, exp_info):
        self.datafile = open(filename, 'w')
        self.datafile.write('Recording date:\t' + datetime.datetime.now().strftime('%Y/%m/%d') + '\n')
        self.datafile.write('Recording time:\t' + datetime.datetime.now().strftime('%H:%M:%S') + '\n')
        self.datafile.write('Recording resolution\t%d x %d\n' % tuple(self.win.size))
        for key, data in exp_info.iteritems():
            self.datafile.write('%s:\t%s\n' % (key, data))
        self.datafile.write('\n')
        self.datafile.write('\t'.join(['TimeStamp',
                                       'GazePointXLeft',
                                       'GazePointYLeft',
                                       'PupilLeft',
                                       'ValidityLeft',
                                       'GazePointXRight',
                                       'GazePointYRight',
                                       'PupilRight'
                                       'ValidityRight',
                                       'GazePointX',
                                       'GazePointY',
                                       'Event']) + '\n')

    def closeDataFile(self):
        print 'datafile closed'
        if self.datafile is not None:
            self.flushData()
            self.datafile.close()

        self.datafile = None

    def recordEvent(self, event):
        t = self.syncmanager.convert_from_local_to_remote(self.clock.get_time())
        self.eventData.append((t, event.code, event.table))

    def flushData(self):
        if self.datafile is None:
            print 'data file is not set.'
            return

        if len(self.gazeData)==0:
            return

        timeStampStart = self.gazeData[0].Timestamp
        gaze_events=[]
        for g in self.gazeData:
            gaze_events.append([(g.Timestamp-timeStampStart)/1000.0,g])
        for e in self.eventData:
            gaze_events.append([(e[0]-timeStampStart)/1000.0,e[1],e[2]])

        gaze_events.sort(key=lambda tup: tup[0])

        for gaze_event in gaze_events:
            if len(gaze_event)==2:
                time_stamp,g=gaze_event
                self.datafile.write('%.1f\t%.4f\t%.4f\t%.4f\t%d\t%.4f\t%.4f\t%.4f\t%d' % (
                    time_stamp,
                    g.LeftGazePoint2D.x*self.win.size[0] if g.LeftValidity!=4 else -1.0,
                    g.LeftGazePoint2D.y*self.win.size[1] if g.LeftValidity!=4 else -1.0,
                g.LeftPupil,
                    g.LeftValidity,
                    g.RightGazePoint2D.x*self.win.size[0] if g.RightValidity!=4 else -1.0,
                    g.RightGazePoint2D.y*self.win.size[1] if g.RightValidity!=4 else -1.0,
                g.RightPupil,
                    g.RightValidity))
                if g.LeftValidity == 4 and g.RightValidity == 4: #not detected
                    ave = (-1.0,-1.0)
                elif g.LeftValidity == 4:
                    ave = (g.RightGazePoint2D.x,g.RightGazePoint2D.y)
                elif g.RightValidity == 4:
                    ave = (g.LeftGazePoint2D.x,g.LeftGazePoint2D.y)
                else:
                    ave = (.5*(g.LeftGazePoint2D.x+g.RightGazePoint2D.x)*self.win.size[0],
                           .5*(g.LeftGazePoint2D.y+g.RightGazePoint2D.y)*self.win.size[1])

                self.datafile.write('\t%.4f\t%.4f\t'%ave)
                self.datafile.write('\n')
            else:
                time_stamp,event_str,table=gaze_event
                formatstr = '%.1f'+'\t'*11+'%s,%s\n'
                table_str=','.join('%s:%s' % (key, val) for key, val in table.iteritems())
                self.datafile.write(formatstr % (time_stamp,event_str,table_str))

        self.gazeData = []
        self.eventData = []

        self.datafile.flush()
