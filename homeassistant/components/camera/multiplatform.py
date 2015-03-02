import mimetypes
import requests
import logging
import json

from homeassistant.components.camera import Camera
from homeassistant.components.camera.dlink import DlinkCamera

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):    
    try:
        
        device_data_str = config.get('device_data')        
        device_data = None
        if device_data_str:
            try:
                device_data = json.loads(device_data_str)
            except Exception as json_ex:
                _LOGGER.error('Camera device info, should be in the format [{"brand": "dlink", "model": "DCS-930L", "name": "Camera 1", "base_url": "http://ip_address:port", "username": "your_username", "password": "your_password"}]: %s', json_ex)

        cameras = []
        if device_data:                        
            for device in device_data:
                if device.get('brand') == 'dlink':
                    cameras.append(DlinkCamera(hass, device))
                else:
                    cameras.append(Camera(hass, device))

        add_devices_callback(cameras)
    except Exception as inst:
        _LOGGER.error("Could not find cameras: %s", inst)
        return False
