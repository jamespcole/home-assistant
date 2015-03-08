"""
homeassistant.components.sensor.sabnzbd
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monitors SABnzbd NZB client API

Configuration:

To use the SABnzbd sensor you will need to add something like the following to
your config/configuration.yaml

sensor:
    platform: sabnzbd
    name: SAB
    api_key: YOUR_API_KEY
    base_url: YOUR_SABNZBD_BASE_URL
    monitored_variables:
        - type: 'current_status'
        - type: 'speed'
        - type: 'queue_size'
        - type: 'queue_remaining'
        - type: 'disk_size'
        - type: 'disk_free'

VARIABLES:

base_url
*Required
This is the base URL of your SABnzbd instance including the port number if not
running on 80
Example: http://192.168.1.32:8124/


name
*Optional
The name to use when displaying this SABnzbd instance

monitored_variables
*Required
An array specifying the variables to monitor.

These are the variables for the monitored_variables array:

type
*Required
The variable you wish to monitor, see the configuration example above for a
list of all available variables


"""

from homeassistant.helpers.device import Device
# pylint: disable=no-name-in-module, import-error
from homeassistant.external.nzbclients.sabnzbd import SabnzbdApi
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, ATTR_FRIENDLY_NAME)
import logging


SENSOR_TYPES = {
    'current_status': ['Status', ''],
    'speed': ['Speed', 'MB/s'],
    'queue_size': ['Queue', 'MB'],
    'queue_remaining': ['Left', 'MB'],
    'disk_size': ['Disk', 'GB'],
    'disk_free': ['Disk Free', 'GB'],
}

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the sensors """
    api_key = config.get("api_key")
    base_url = config.get("base_url")
    name = config.get("name", "SABnzbd")
    if not base_url:
        _LOGGER.error('Missing config variable base_url')
        return False
    if not api_key:
        _LOGGER.error('Missing config variable api_key')
        return False

    sab_api = SabnzbdApi(base_url, api_key)
    dev = []
    for variable in config['monitored_variables']:
        if variable['type'] not in SENSOR_TYPES:
            _LOGGER.error('Sensor type: "%s" does not exist', variable['type'])
        else:
            dev.append(SabnzbdSensor(variable['type'], sab_api, name))

    add_devices(dev)


class SabnzbdSensor(Device):
    """ A Sabnzbd sensor """

    def __init__(self, sensor_type, sabnzb_client, client_name):
        self._name = SENSOR_TYPES[sensor_type][0]
        self.sabnzb_client = sabnzb_client
        self.type = sensor_type
        self.client_name = client_name
        self._state = None
        self.unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self.update()

    @property
    def name(self):
        return self.client_name + ' ' + self._name

    @property
    def state(self):
        """ Returns the state of the device. """
        return self._state

    @property
    def state_attributes(self):
        """ Returns the state attributes. """
        return {
            ATTR_FRIENDLY_NAME: self.name,
            ATTR_UNIT_OF_MEASUREMENT: self.unit_of_measurement,
        }

    def update(self):
        self.sabnzb_client.refresh_queue()
        if self.sabnzb_client.queue:
            if self.type == 'current_status':
                self._state = self.sabnzb_client.queue.get('status')
            elif self.type == 'speed':
                mb_spd = float(self.sabnzb_client.queue.get('kbpersec')) / 1024
                self._state = round(mb_spd, 1)
            elif self.type == 'queue_size':
                self._state = self.sabnzb_client.queue.get('mb')
            elif self.type == 'queue_remaining':
                self._state = self.sabnzb_client.queue.get('mbleft')
            elif self.type == 'disk_size':
                self._state = self.sabnzb_client.queue.get('diskspacetotal1')
            elif self.type == 'disk_free':
                self._state = self.sabnzb_client.queue.get('diskspace1')
            else:
                self._state = 'Unknown'
