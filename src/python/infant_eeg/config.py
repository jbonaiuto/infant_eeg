from ConfigParser import ConfigParser
import os

CONF_DIR = '../../conf'
DATA_DIR = '../../data'

config = ConfigParser()
config.read(os.path.join(CONF_DIR, 'config.properties'))

IO_CONFIG_FILE=os.path.join(CONF_DIR,config.get('config','io_config_file'))

MONITOR=config.get('display','monitor')
SCREEN=int(config.get('display','screen'))