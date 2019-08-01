import paho.mqtt.client as mqtt_client
import ssl
import urllib.parse
from . import LOGGER, REGISTRY, Device

def mqtt_on_connect(client, userdata, flags, rc):
    LOGGER.info('MQTT client connected to broker: %s', client._host)

def mqtt_on_disconnect(client, userdata, rc):
    LOGGER.info('MQTT client disconnected from broker: %s', client._host)

def mqtt_transmit(client, userdata, msg):
    LOGGER.debug('MQTT %s: received message', msg.topic)
    topic = msg.topic[len(userdata['prefix']):]
    topic = topic.split('/', 1)
    device_id = topic[0]
    if not device_id:
        LOGGER.warning('MQTT %s: Device mising', msg.topic)
        return
    device = REGISTRY.find_device(device_id)
    if not device:
        LOGGER.warning('MQTT %s: Device not found: %s', msg.topic, device_id)
        return
    code = msg.payload
    if not code:
        LOGGER.warning('MQTT %s: No payload', msg.topic)
        return
    try:
        if device.transmit(code):
            return
    except:
        pass
    LOGGER.warning('MQTT %s: invalid payload', msg.topic)

def mqtt_connect(url, prefix='broadlink'):
    if not url:
        LOGGER.info('MQTT client disabled')
        return False
    if not prefix.endswith('/'):
        prefix = prefix + '/' 
    LOGGER.debug('MQTT using prefix %s', prefix)

    url = urllib.parse.urlparse(url, scheme='mqtt', allow_fragments=False)
    query = urllib.parse.parse_qs(url.query)
    port = url.port
    if not port:
        if url.scheme == 'mqtt':
            port = 1883
        elif url.scheme == 'mqtts':
            port = 8883
        else:
            raise ValueError('Invalid protocol: %s', url.scheme)

    mqtt = mqtt_client.Client()
    if url.username or url.password:
        mqtt.username_pw_set(url.username, url.password)
    if url.scheme == 'mqtts':
        ctx = ssl.create_default_context()
        if query.get('insecure', False):
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        mqtt.tls_set_context(ctx)

    mqtt.user_data_set({
        'prefix': prefix,
    })
    mqtt.enable_logger = True
    mqtt.on_connect = mqtt_on_connect
    mqtt.on_disconnect = mqtt_on_disconnect
    mqtt.connect(url.hostname, port)
    mqtt.message_callback_add(prefix + '+/transmit', mqtt_transmit)
    mqtt.subscribe(prefix + '#')
    mqtt.loop_start()
    return True