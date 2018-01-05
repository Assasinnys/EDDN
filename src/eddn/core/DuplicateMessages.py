# coding: utf8
import hashlib
import re
import simplejson
import zlib

from datetime import datetime, timedelta
from eddn.conf.Settings import Settings
from threading import Lock, Thread
from time import sleep


class DuplicateMessages(Thread):
    max_minutes = Settings.RELAY_DUPLICATE_MAX_MINUTES

    caches = {}

    lock = Lock()

    def __init__(self):
        super(DuplicateMessages, self).__init__()
        self.daemon = True

    def run(self):
        while True:
            sleep(60)
            with self.lock:
                maxTime = datetime.utcnow()

                for key in self.caches.keys():
                    if self.caches[key] + timedelta(minutes=self.max_minutes) < maxTime:
                        del self.caches[key]

    def isDuplicated(self, message):
        with self.lock:
            # Test messages are not duplicate
            if re.search('test', message['$schemaRef'], re.I):
                return False

            if 'gatewayTimestamp' in message['header']:
                del message['header']['gatewayTimestamp']  # Prevent dupe with new timestamp
            if 'timestamp' in message['message']:
                del message['message']['timestamp']  # Prevent dupe with new timestamp
            if 'softwareName' in message['header']:
                del message['header']['softwareName']  # Prevent dupe with different software
            if 'softwareVersion' in message['header']:
                del message['header']['softwareVersion']  # Prevent dupe with different software version
            if 'uploaderID' in message['header']:
                del message['header']['uploaderID']  # Prevent dupe with different uploaderID
            
            # Convert starPos to avoid software modification in dupe messages
            if 'StarPos' in message['message']:
                if message['message']['StarPos'][0]:
                    message['message']['StarPos'][0] = round(message['message']['StarPos'][0] *32)
                if message['message']['StarPos'][1]:
                    message['message']['StarPos'][1] = round(message['message']['StarPos'][1] *32)
                if message['message']['StarPos'][2]:
                    message['message']['StarPos'][2] = round(message['message']['StarPos'][2] *32)
            
            # Prevent Docked event with small difference in distance from start
            if 'DistFromStarLS' in message['message']:
                message['message']['DistFromStarLS'] = round(message['message']['DistFromStarLS'])

            message = simplejson.dumps(message, sort_keys=True) # Ensure most duplicate messages will get the same key
            key     = hashlib.sha256(message).hexdigest()

            if key not in self.caches:
                self.caches[key] = datetime.utcnow()
                return False
            else:
                self.caches[key] = datetime.utcnow()
                return True
