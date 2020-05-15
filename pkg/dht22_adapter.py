"""DHT22 adapter for Mozilla WebThings Gateway."""

from gateway_addon import Device, Adapter, Property, Database
import Adafruit_DHT
import threading
import time


_POLL_INTERVAL = 5


class DHT22Adapter(Adapter):
    """Adapter for a DHT22 Sensor connected to Raspberry Pi GPIO."""

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        self.name = self.__class__.__name__
        Adapter.__init__(self,
                         'dht22-adapter',
                         'dht22-adapter',
                         verbose=verbose)

        database = Database('dht22-adapter')
        if not database.open():
            return

        self.config = database.load_config()
        database.close()

        if not self.config:
            return

        self.start_pairing()

    def start_pairing(self, timeout=None):
        """
        Start the pairing process.

        timeout -- Timeout in seconds at which to quit pairing
        """
        for pinConfig in self.config['DHT22']:
            _id = 'dht22-{}'.format(pinConfig['pin'])
            if _id not in self.devices:
                device = DHT22Device(self, _id, pinConfig['pin'], pinConfig)
                self.handle_device_added(device)


class DHT22Device(Device):
    """DHT22 device type."""

    def __init__(self, adapter, _id, pin, config):
        """Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID to assign to this device
        pin -- the pin the device is attached to
        config -- the device config
        """
        Device.__init__(self, adapter, _id)
        self._type = ['TemperatureSensor', 'MultiLevelSensor']
        self.name = 'DHT22 ({})'.format(pin)
        self.description = 'DHT22 sensor on pin {}'.format(pin)

        self.sensor_type = Adafruit_DHT.DHT22
        self.pin = pin
        self.temperature_offset = config['temperature_offset']
        self.humidity_offset = config['humidity_offset']

        humidity, temperature = \
            Adafruit_DHT.read_retry(self.sensor_type, self.pin)

        self.properties['temperature'] = DHT22Property(
            self,
            'temperature',
            {
                '@type': 'TemperatureProperty',
                'title': 'Temperature',
                'type': 'number',
                'readOnly': True,
                'unit': 'degree celsius',
            },
            self.pin,
            temperature
        )

        self.properties['humidity'] = DHT22Property(
            self,
            'humidity',
            {
                '@type': 'LevelProperty',
                'title': 'Humidity',
                'type': 'number',
                'readOnly': True,
                'unit': 'percent',
            },
            self.pin,
            humidity
        )

        t = threading.Thread(target=self.poll)
        t.daemon = True
        t.start()

    def poll(self):
        """Poll the GPIO device."""
        while True:
            time.sleep(_POLL_INTERVAL)
            humidity, temperature = \
                Adafruit_DHT.read_retry(self.sensor_type, self.pin)
            self.properties['humidity'].update(
                humidity + self.humidity_offset
            )
            self.properties['temperature'].update(
                temperature + self.temperature_offset
            )


class DHT22Property(Property):
    """DHT22 property type."""

    def __init__(self, device, name, description, pin, value):
        """
        Initialize the object.

        device -- the Device this property belongs to
        name -- name of the property
        description -- description of the property, as a dictionary
        pin -- the pin the device is attached to
        value -- current value of this property
        """
        Property.__init__(self, device, name, description)
        self.pin = pin
        self.set_cached_value(value)

    def update(self, value):
        """
        Update the current value, if necessary.

        value -- the new value
        """
        if value != self.value:
            print(
                '{}: Value of {} sensor on pin {} has changed from {} to {}'
                .format(time.ctime(), self.name, self.pin, self.value, value),
                flush=True
            )
            self.set_cached_value_and_notify(value)
