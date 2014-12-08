from ConfigParser import ConfigParser
import os

CONF_DIR = '../../conf'
DATA_DIR = '../../data'

config = ConfigParser()
config.read(os.path.join(CONF_DIR, 'config.properties'))

MONITOR = config.get('display', 'monitor')
SCREEN = int(config.get('display', 'screen'))
NETSTATION_IP = config.get('config', 'netstation_ip')

EYETRACKER_NAME = config.get('eyetracker', 'name')
EYETRACKER_CALIBRATION_POINTS = []
for x in config.get('eyetracker', 'calibration_points').split(';'):
    x_parts = x.split(',')
    EYETRACKER_CALIBRATION_POINTS.append((float(x_parts[0]), float(x_parts[1])))
