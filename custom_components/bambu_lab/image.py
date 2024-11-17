"""Image platform."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, LOGGER
from .coordinator import BambuDataUpdateCoordinator
from .models import BambuLabEntity
from .definitions import BambuLabSensorEntityDescription
from .pybambu.const import Features
import xml.etree.ElementTree as ET
from .pybambu.commands import PRINT_FILE_TEMPLATE

CHAMBER_IMAGE_SENSOR = BambuLabSensorEntityDescription(
        key="p1p_camera",
        translation_key="p1p_camera",
        value_fn=lambda self: self.coordinator.get_model().get_camera_image(),
        exists_fn=lambda coordinator: coordinator.get_model().supports_feature(Features.CAMERA_IMAGE) and coordinator.camera_as_image_sensor,
    )

COVER_IMAGE_SENSOR = BambuLabSensorEntityDescription(
        key="cover_image",
        translation_key="cover_image",
        value_fn=lambda self: self.coordinator.get_model().print_job.get_cover_image(),
        exists_fn=lambda coordinator: coordinator.get_model().info.has_bambu_cloud_connection
    )

PRINT_JOB_THUMBNAIL = BambuLabSensorEntityDescription(
    key="print_job_thumbnail",
    translation_key="print_job_thumbnail",
    value_fn=lambda self: self.get_thumbnail(),
    exists_fn=lambda coordinator: True,
    icon="mdi:printer-3d-nozzle",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Everything but the Kitchen Sink config entry."""

    LOGGER.debug("IMAGE::async_setup_entry")
    coordinator: BambuDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if COVER_IMAGE_SENSOR.exists_fn(coordinator):
        cover_image = CoverImage(hass, coordinator, COVER_IMAGE_SENSOR)
        async_add_entities([cover_image])

    if CHAMBER_IMAGE_SENSOR.exists_fn(coordinator):
        chamber_image = ChamberImage(hass, coordinator, CHAMBER_IMAGE_SENSOR)
        async_add_entities([chamber_image])

    if PRINT_JOB_THUMBNAIL.exists_fn(coordinator):
        job_names = await coordinator.data.print_job.get_job_names()
        LOGGER.debug(f"Found print jobs in cache: {job_names}")
        for job_name in job_names:
            thumbnail = PrintJobThumbnail(hass, coordinator, PRINT_JOB_THUMBNAIL, job_name)
            async_add_entities([thumbnail])


class CoverImage(ImageEntity, BambuLabEntity):
    """Representation of an image entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BambuDataUpdateCoordinator,
        description: BambuLabSensorEntityDescription
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass=hass)
        super(BambuLabEntity, self).__init__(coordinator=coordinator)
        self._attr_content_type = "image/jpeg"
        self._image_filename = None
        self.entity_description = description
        printer = self.coordinator.get_model().info
        self._attr_unique_id = f"{printer.serial}_{description.key}"

    def image(self) -> bytes | None:
        """Return bytes of image."""
        return self.coordinator.get_model().cover_image.get_jpeg()

    @property
    def image_last_updated(self) -> datetime | None:
        """The time when the image was last updated."""
        return self.coordinator.get_model().cover_image.get_last_update_time()


class ChamberImage(ImageEntity, BambuLabEntity):
    """Representation of an image entity."""
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BambuDataUpdateCoordinator,
        description: BambuLabSensorEntityDescription
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass=hass)
        super(BambuLabEntity, self).__init__(coordinator=coordinator)
        self._attr_content_type = "image/jpeg"
        self._image_filename = None
        self.entity_description = description
        printer = self.coordinator.get_model().info
        self._attr_unique_id = f"{printer.serial}_{description.key}"

    def image(self) -> bytes | None:
        """Return bytes of image."""
        return self.coordinator.get_model().chamber_image.get_jpeg()
    
    @property
    def image_last_updated(self) -> datetime | None:
        """The time when the image was last updated."""
        return self.coordinator.get_model().chamber_image.get_last_update_time()
    
    @property
    def available(self) -> bool:
        return self.coordinator.get_model().chamber_image.available and self.coordinator.camera_enabled


class PrintJobThumbnail(ImageEntity, BambuLabEntity):
    """Representation of a print job thumbnail with click action."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BambuDataUpdateCoordinator,
        description: BambuLabSensorEntityDescription,
        job_name: str
    ) -> None:
        """Initialize the print job thumbnail entity."""
        super().__init__(hass=hass)
        super(BambuLabEntity, self).__init__(coordinator=coordinator)
        self._attr_content_type = "image/png"
        self.entity_description = description
        self.job_name = job_name
        printer = self.coordinator.get_model().info
        self._attr_unique_id = f"{printer.serial}_printjob_{job_name}"
        
        # Set name and icon
        self._attr_name = job_name
        self._attr_icon = description.icon
        
        # Make entity clickable and configurable
        self._attr_entity_picture_local = True
        self._attr_should_poll = False
        self._attr_entity_category = description.entity_category
        
        # Entity registry settings
        self._attr_has_entity_name = True
        self._attr_translation_key = f"print_job_{job_name}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check if both image and config exist
        image_path = Path(__file__).parent / "cache" / self.job_name / "Metadata" / "plate_1.png"
        config_path = Path(__file__).parent / "cache" / self.job_name / "Metadata" / "model_settings.config"
        return image_path.exists() and config_path.exists()

    def image(self) -> bytes | None:
        """Return bytes of image."""
        try:
            image_path = Path(__file__).parent / "cache" / self.job_name / "Metadata" / "plate_1.png"
            with open(image_path, "rb") as f:
                return f.read()
        except Exception as e:
            LOGGER.error(f"Error reading thumbnail for {self.job_name}: {e}")
            return None

    async def async_press(self) -> None:
        """Handle click/press action - start the print."""
        if not self.coordinator.data.print_job.can_start_print():
            LOGGER.warning("Cannot start print - printer is not idle")
            return

        try:
            config_path = Path(__file__).parent / "cache" / self.job_name / "Metadata" / "model_settings.config"
            if not config_path.exists():
                LOGGER.error(f"model_settings.config not found for {self.job_name}")
                return

            tree = ET.parse(config_path)
            root = tree.getroot()
            
            # Extract gcode path from XML
            gcode_file = None
            for plate in root.findall('plate'):
                for metadata in plate.findall('metadata'):
                    if metadata.get('key') == 'gcode_file':
                        gcode_file = metadata.get('value')
                        break
                if gcode_file:
                    break

            if not gcode_file:
                LOGGER.error("No gcode_file found in model_settings.config")
                return

            # Construct and send print command
            command = PRINT_FILE_TEMPLATE.copy()
            command['print']['param'] = gcode_file
            command['print']['url'] = f"file:///sdcard/{self.job_name}.gcode.3mf"
            command['print']['flow_cali'] = False
            command['print']['vibration_cali'] = False
            command['print']['layer_inspect'] = False

            LOGGER.debug(f"Starting print with command: {command}")
            self.coordinator.client.publish(command)

        except Exception as e:
            LOGGER.error(f"Error starting print for {self.job_name}: {e}")
