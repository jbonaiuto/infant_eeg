from ConfigParser import ConfigParser
import os

CONF_DIR = '../../conf'
DATA_DIR = '../../data'

config = ConfigParser()
config.read(os.path.join(CONF_DIR, 'config.properties'))

MONITOR=config.get('display','monitor')
SCREEN=int(config.get('display','screen'))
NETSTATION_IP=config.get('config','netstation_ip')