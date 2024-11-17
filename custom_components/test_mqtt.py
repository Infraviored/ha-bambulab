# test_bambu_mqtt.py
import paho.mqtt.client as mqtt
import ssl
import json
import logging
import time

# Setup logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

class BambuMonitor:
    def __init__(self, host, serial, access_code):
        self.host = host
        self.serial = serial
        self.access_code = access_code
        self.client = None
        self.connected = False

    def on_connect_outgoing(self, client, userdata, flags, rc):
        LOGGER.info(f"Connected with result code {rc}")
        self.connected = True
        topic = f"device/{self.serial}/report"
        LOGGER.info(f"Subscribing to {topic}")
        client.subscribe(topic)

    def on_connect_incoming(self, client, userdata, flags, rc):
        LOGGER.info(f"Connected with result code {rc}")
        self.connected = True
        topic = f"device/{self.serial}/request"
        LOGGER.info(f"Subscribing to {topic}")
        client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        LOGGER.info(f"Topic: {msg.topic}")
        try:
            payload = json.loads(msg.payload)
            LOGGER.info(f"Payload: {json.dumps(payload, indent=2)}")
        except:
            LOGGER.info(f"Raw payload: {msg.payload}")

    def track_outgoing(self):
        """Original functionality - track messages FROM the printer"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect_outgoing
        self.client.on_message = self.on_message

        # Setup TLS like the integration does
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE)
        self.client.tls_insecure_set(True)
        
        # Auth credentials
        self.client.username_pw_set("bblp", password=self.access_code)

        try:
            LOGGER.info(f"Connecting to {self.host}...")
            self.client.connect(self.host, 8883)
            self.client.loop_start()
            return True
        except Exception as e:
            LOGGER.error(f"Connection error: {e}")
            return False

    def track_incoming(self):
        """New functionality - track messages TO the printer"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect_incoming
        self.client.on_message = self.on_message

        # Setup TLS like the integration does
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE)
        self.client.tls_insecure_set(True)
        
        # Auth credentials
        self.client.username_pw_set("bblp", password=self.access_code)

        try:
            LOGGER.info(f"Connecting to {self.host}...")
            self.client.connect(self.host, 8883)
            self.client.loop_start()
            return True
        except Exception as e:
            LOGGER.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()

def main():
    # Your printer details
    monitor = BambuMonitor(
        host="192.168.178.70",
        serial="01P00A442900109",
        access_code="33055062"
    )

    # Choose which type of monitoring you want
    monitor_type = "incoming"  # or "incoming"

    try:
        if monitor_type == "outgoing":
            success = monitor.track_outgoing()
            message = "outgoing messages (from printer)"
        else:
            success = monitor.track_incoming()
            message = "incoming messages (to printer)"

        if success:
            LOGGER.info(f"Connected! Monitoring {message}...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Shutting down...")
    finally:
        monitor.disconnect()

if __name__ == "__main__":
    main()