from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from dataclasses import dataclass
from .utils import search, fan_percentage, get_speed_name, get_stage_action, get_printer_type, get_hw_version, \
    get_sw_version, start_time, end_time
from .const import LOGGER, Features

import asyncio


class Device:
    def __init__(self, client, device_type, serial):
        self.client = client
        self.temperature = Temperature()
        self.lights = Lights()
        self.info = Info(device_type, serial)
        self.fans = Fans()
        self.speed = Speed()
        self.stage = StageAction()
        self.ams = AMS(self)

    def update(self, data):
        """Update from dict"""
        self.temperature.update(data)
        self.lights.update(data)
        self.fans.update(data)
        self.info.update(data)
        self.speed.update(data)
        self.stage.update(data)
        self.ams.update(data)

    def supports_feature(self, feature):
        if feature == Features.AUX_FAN:
            return self.info.device_type == "X1" or self.info.device_type == "X1C" or self.info.device_type == "P1P"
        if feature == Features.CHAMBER_LIGHT:
            return self.info.device_type == "X1" or self.info.device_type == "X1C" or self.info.device_type == "P1P"
        if feature == Features.CHAMBER_FAN:
            return self.info.device_type == "X1" or self.info.device_type == "X1C"
        if feature == Features.CHAMBER_TEMPERATURE:
            return self.info.device_type == "X1" or self.info.device_type == "X1C"
        if feature == Features.CURRENT_STAGE:
            return self.info.device_type == "X1" or self.info.device_type == "X1C" or self.info.device_type == "P1P"
        if feature == Features.PRINT_LAYERS:
            return self.info.device_type == "X1" or self.info.device_type == "X1C"
        return False


@dataclass
class Lights:
    """Return all light related info"""
    chamber_light: str
    work_light: str

    def __init__(self):
        self.chamber_light = "Unknown"
        self.work_light = "Unknown"

    def update(self, data):
        """Update from dict"""

        self.chamber_light = \
            search(data.get("lights_report", []), lambda x: x.get('node', "") == "chamber_light",
                   {"mode": self.chamber_light}).get("mode")
        self.work_light = \
            search(data.get("lights_report", []), lambda x: x.get('node', "") == "work_light",
                   {"mode": self.work_light}).get("mode")


@dataclass
class Temperature:
    """Return all temperature related info"""
    bed_temp: int
    target_bed_temp: int
    chamber_temp: int
    nozzle_temp: int
    target_nozzle_temp: int

    def __init__(self):
        self.bed_temp = 0
        self.target_bed_temp = 0
        self.chamber_temp = 0
        self.nozzle_temp = 0
        self.target_nozzle_temp = 0

    def update(self, data):
        """Update from dict"""

        self.bed_temp = round(data.get("bed_temper", self.bed_temp))
        self.target_bed_temp = round(data.get("bed_target_temper", self.target_bed_temp))
        self.chamber_temp = round(data.get("chamber_temper", self.chamber_temp))
        self.nozzle_temp = round(data.get("nozzle_temper", self.nozzle_temp))
        self.target_nozzle_temp = round(data.get("nozzle_target_temper", self.target_nozzle_temp))


@dataclass
class Fans:
    """Return all fan related info"""
    aux_fan_speed: int
    _aux_fan_speed: int
    chamber_fan_speed: int
    _chamber_fan_speed: int
    cooling_fan_speed: int
    _cooling_fan_speed: int
    heatbreak_fan_speed: int
    _heatbreak_fan_speed: int

    def __init__(self):
        self.aux_fan_speed = 0
        self._aux_fan_speed = 0
        self.chamber_fan_speed = 0
        self._chamber_fan_speed = 0
        self.cooling_fan_speed = 0
        self._cooling_fan_speed = 0
        self.heatbreak_fan_speed = 0
        self._heatbreak_fan_speed = 0

    def update(self, data):
        """Update from dict"""
        self._aux_fan_speed = data.get("big_fan1_speed", self._aux_fan_speed)
        self.aux_fan_speed = fan_percentage(self._aux_fan_speed)
        self._chamber_fan_speed = data.get("big_fan2_speed", self._chamber_fan_speed)
        self.chamber_fan_speed = fan_percentage(self._chamber_fan_speed)
        self._cooling_fan_speed = data.get("cooling_fan_speed", self._cooling_fan_speed)
        self.cooling_fan_speed = fan_percentage(self._cooling_fan_speed)
        self._heatbreak_fan_speed = data.get("heatbreak_fan_speed", self._heatbreak_fan_speed)
        self.heatbreak_fan_speed = fan_percentage(self._heatbreak_fan_speed)


@dataclass
class Info:
    """Return all information related content"""
    wifi_signal: int
    print_percentage: int
    device_type: str
    hw_ver: str
    sw_ver: str
    gcode_state: str
    remaining_time: int
    start_time: str
    end_time: str
    current_layer: int
    total_layers: int

    def __init__(self, device_type, serial):
        self.wifi_signal = 0
        self.print_percentage = 0
        self.device_type = device_type
        self.hw_ver = "Unknown"
        self.sw_ver = "Unknown"
        self.gcode_state = "Unknown"
        self.serial = serial
        self.remaining_time = 0
        self.end_time = 000
        self.start_time = 000
        self.current_layer = 0
        self.total_layers = 0

    def update(self, data):
        """Update from dict"""
        self.wifi_signal = int(data.get("wifi_signal", str(self.wifi_signal)).replace("dBm", ""))
        self.print_percentage = data.get("mc_percent", self.print_percentage)
        self.device_type = get_printer_type(data.get("module", []), self.device_type)
        self.hw_ver = get_hw_version(data.get("module", []), self.hw_ver)
        self.sw_ver = get_sw_version(data.get("module", []), self.sw_ver)
        self.gcode_state = data.get("gcode_state", self.gcode_state)
        self.remaining_time = data.get("mc_remaining_time", self.remaining_time)
        self.start_time = start_time(int(data.get("gcode_start_time", self.remaining_time)))
        self.end_time = end_time(data.get("mc_remaining_time", self.remaining_time))
        self.current_layer = data.get("layer_num", self.current_layer)
        self.total_layers = data.get("total_layer_num", self.total_layers)

    def add_serial(self, data):
        self.serial = data or self.serial


@dataclass
class AMS:
    """Return all AMS related info"""

    def __init__(self, device):
        """Load from dict"""
        self.device = device
        self.data = []

    def update(self, data):
        """Update from dict"""

        # First determine if this the version info data or the json payload data. We use the version info to determine
        # what devices to add to home assistant and add all the sensors as entititied. And then then json payload data
        # to populate the values for all those entities.

        # The module entries are of this form:
        # {
        #     "name": "ams/0",
        #     "project_name": "",
        #     "sw_ver": "00.00.05.96",
        #     "loader_ver": "00.00.00.00",
        #     "ota_ver": "00.00.00.00",
        #     "hw_ver": "AMS08",
        #     "sn": "<SERIAL>"
        # }

        received_ams_data = False
        module_list = data.get("module", [])
        for module in module_list:
            name = module["name"]
            if name.startswith("ams/"):
                received_ams_data = True
                index = int(name[4])
                LOGGER.debug(f"ADDING AMS {index}: {module['sn']}")
                new_ams = { 
                    "serial": module['sn'],
                    "sw_version": module['sw_ver'],
                    "hw_version": module['hw_ver'],
                }
                if not self.data:
                    self.data.append(new_ams)
                else:
                    self.data[index] = new_ams

        if received_ams_data:
            self.device.client.callback("event_ams_info_update")

        # AMS json payload is of the form:
        # "ams": {
        #     "ams": [
        #         {
        #             "id": "0",
        #             "humidity": "4",
        #             "temp": "0.0",
        #             "tray": [
        #                 {
        #                     "id": "0",
        #                     "remain": -1,
        #                     "k": 0.019999999552965164,
        #                     "n": 1.399999976158142,
        #                     "tag_uid": "0000000000000000",
        #                     "tray_id_name": "",
        #                     "tray_info_idx": "GFL99",
        #                     "tray_type": "PLA",
        #                     "tray_sub_brands": "",
        #                     "tray_color": "FFFF00FF",
        #                     "tray_weight": "0",
        #                     "tray_diameter": "0.00",
        #                     "drying_temp": "0",
        #                     "drying_time": "0",
        #                     "bed_temp_type": "0",
        #                     "bed_temp": "0",
        #                     "nozzle_temp_max": "240",
        #                     "nozzle_temp_min": "190",
        #                     "xcam_info": "000000000000000000000000",
        #                     "tray_uuid": "00000000000000000000000000000000"
        #                 },
        #                 {
        #                     "id": "1",
        #                     ...
        #                 },
        #                 {
        #                     "id": "2",
        #                     ...
        #                 },
        #                 {
        #                     "id": "3",
        #                     ...
        #                 }
        #             ]
        #         }
        #     ],
        #     "ams_exist_bits": "1",
        #     "tray_exist_bits": "f",
        #     "tray_is_bbl_bits": "f",
        #     "tray_now": "255",
        #     "tray_read_done_bits": "f",
        #     "tray_reading_bits": "0",
        #     "tray_tar": "255",
        #     "version": 3,
        #     "insert_flag": true,
        #     "power_on_flag": false
        # },

        ams_data = data.get("ams", [])
        if len(ams_data) != 0:
            ams_list = ams_data.get("ams", [])
            for ams in ams_list:
                LOGGER.debug(f"AMS: {ams}")

        #self.number_of_ams = int(data.get("ams", []).get("ams_exist_bits", self.number_of_ams))
        #self.version = int(data.get("ams", []).get("version", self.version))

        # TODO: Bug in the below logic that keeps adding more and more elements to the array, rather than updating it. Probably need to break this out a bit more
        # if int(data.get("ams", []).get("ams_exist_bits", 0)) > 0:
        #     ams_arr = data.get("ams").get("ams")
        #     for index, ams_device in enumerate(ams_arr):
        #         current_ams = {
        #             "id": int(ams_device.get("id", 0)),
        #             "temperature": round(float(ams_device.get("temp", 0.0))),
        #             "humidity": int(ams_device.get("humidity", 0)),
        #             # "tray": ams_device.get("tray", [])
        #         }
        #         self.ams_data.append(current_ams)
        #     return


@dataclass
class Speed:
    """Return speed profile information"""
    _id: int
    name: str
    modifier: int

    def __init__(self):
        """Load from dict"""
        self._id = 0
        self.name = get_speed_name(2)
        self.modifier = 100

    def update(self, data):
        """Update from dict"""
        self._id = int(data.get("spd_lvl", self._id))
        self.name = get_speed_name(self._id)
        self.modifier = int(data.get("spd_mag", self.modifier))


@dataclass
class StageAction:
    """Return Stage Action information"""
    _id: int
    description: str

    def __init__(self):
        """Load from dict"""
        self._id = 99
        self.description = get_stage_action(self._id)

    def update(self, data):
        """Update from dict"""
        self._id = int(data.get("stg_cur", self._id))
        self.description = get_stage_action(self._id)
