"""
homeassistant.components.camera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Component to interface with various cameras that can be monitored.
"""
import urllib3
import mimetypes
import requests
import logging
from homeassistant.helpers.entity import Entity
import time
from datetime import timedelta
import re
from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    HTTP_NOT_FOUND)


from homeassistant.helpers.entity_component import EntityComponent


DOMAIN = 'camera'
DEPENDENCIES = ['http']
GROUP_NAME_ALL_CAMERAS = 'all_cameras'
SCAN_INTERVAL = 30
ENTITY_ID_FORMAT = DOMAIN + '.{}'

# Maps discovered services to their platforms
DISCOVERY_PLATFORMS = {}


def setup(hass, config):
    """ Track states and offer events for sensors. """



    component = EntityComponent(
        logging.getLogger(__name__), DOMAIN, hass, SCAN_INTERVAL,
        DISCOVERY_PLATFORMS)

    component.setup(config)


    def _proxy_camera_image(handler, path_match, data):
        """ Proxies the camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            response = camera.get_camera_image()
            handler.wfile.write(response.content)
        else:
            handler.send_response(HTTP_NOT_FOUND)

    hass.http.register_path('GET', re.compile(r'/api/camera_proxy/(?P<entity_id>[a-zA-Z\._0-9]+)'), _proxy_camera_image, require_auth=True)


    def _proxy_camera_mjpeg_stream(handler, path_match, data):
        """ Proxies the camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            try:
                camera.is_streaming = True
                camera.update_ha_state()

                http = urllib3.PoolManager()
                handler.request.sendall(bytes('HTTP/1.1 200 OK\r\n', 'utf-8'))
                handler.request.sendall(bytes('Content-type: multipart/x-mixed-replace; boundary=--jpgboundary\r\n\r\n', 'utf-8'))
                handler.request.sendall(bytes('--jpgboundary\r\n', 'utf-8'))
                count = 0
                while True:

                    headers = urllib3.util.make_headers(basic_auth=camera.username + ':' + camera.password)
                    req = http.request('GET', camera.still_image_url, headers = headers)

                    headersStr = ''
                    headersStr = headersStr + 'Content-length: ' + str(len(req.data)) + '\r\n'
                    headersStr = headersStr + 'Content-type: image/jpeg\r\n'
                    headersStr = headersStr + '\r\n'

                    handler.request.sendall(bytes(headersStr, 'utf-8') + req.data + bytes('\r\n', 'utf-8'))
                    handler.request.sendall(bytes('--jpgboundary\r\n', 'utf-8'))
            except Exception:
                camera.is_streaming = False
                camera.update_ha_state()
        else:
            handler.send_response(HTTP_NOT_FOUND)

        camera.is_streaming = False
        camera.update_ha_state()

    hass.http.register_path('GET', re.compile(r'/api/camera_proxy_stream/(?P<entity_id>[a-zA-Z\._0-9]+)'), _proxy_camera_mjpeg_stream, require_auth=True)
    return True

    #


class Camera(Entity):
    """ Base class for cameras. """

    def __init__(self, hass, device_info):
        #super().__init__(hass, device_info)
        self.hass = hass
        self.device_info = device_info
        self.BASE_URL = device_info.get('base_url')
        if not self.BASE_URL.endswith('/'):
            self.BASE_URL = self.BASE_URL + '/'
        self.username = device_info.get('username')
        self.password = device_info.get('password')
        self.is_streaming = False


    def get_camera_image(self, stream=False):
        response = requests.get(self.still_image_url, auth=(self.username, self.password), stream=stream)
        return response

    @property
    def name(self):
        if self.device_info.get('name'):
            return self.device_info.get('name')
        else:
            return super().name

    @property
    def state(self):
        """ Returns the state of the entity. """
        if self.is_streaming:
            return "Streaming"
        else:
            return "Idle"



    @property
    def state_attributes(self):
        """ Returns optional state attributes. """
        attr = super().state_attributes
        attr['model_name'] = self.device_info.get('model', 'generic')
        attr['brand'] = self.device_info.get('brand', 'generic')
        attr['still_image_url'] = '/api/camera_proxy/' + self.entity_id
        attr[ATTR_ENTITY_PICTURE] = '/api/camera_proxy/' + self.entity_id + '?api_password=' + self.hass.http.api_password + '&time=' + str(time.time())
        attr['stream_url'] = '/api/camera_proxy_stream/' + self.entity_id

        return attr

    @property
    def still_image_url(self):
        """ This should be implemented by different camera models. """
        if self.device_info.get('still_image_url'):
            return self.BASE_URL + self.device_info.get('still_image_url')
        return self.BASE_URL + 'image.jpg'
