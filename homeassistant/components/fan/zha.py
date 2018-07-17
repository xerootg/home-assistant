"""
Fans on Zigbee Home Automation networks.

For more details on this platform, please refer to the documentation
at https://home-assistant.io/components/fan.zha/
"""
import logging
from homeassistant.components import zha
from homeassistant.components.fan import (
    DOMAIN, FanEntity, SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
    SUPPORT_SET_SPEED)

DEPENDENCIES = ['zha']

_LOGGER = logging.getLogger(__name__)

# Additional speeds in zigbee's ZCL
# Spec is unclear as to what this value means. On King Of Fans HBUniversal
# receiver, this means Very High.
SPEED_ON = 'on'
# The fan speed is self-regulated
SPEED_AUTO = 'auto'
# When the heated/cooled space is occupied, the fan is always on
SPEED_SMART = 'smart'

SPEED_LIST = [
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SPEED_ON,
    SPEED_AUTO,
    SPEED_SMART
]

VALUE_TO_SPEED = {i: speed for i, speed in enumerate(SPEED_LIST)}
SPEED_TO_VALUE = {speed: i for i, speed in enumerate(SPEED_LIST)}


async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the Zigbee Home Automation switches."""
    discovery_info = zha.get_discovery_info(hass, discovery_info)
    if discovery_info is None:
        return

    from zigpy.zcl.clusters.hvac import Fan
    in_clusters = discovery_info['in_clusters']
    cluster = in_clusters[Fan.cluster_id]
    await cluster.bind()
    await cluster.configure_reporting(0, 0, 600, 1,)

    async_add_devices([ZhaFan(**discovery_info)], update_before_add=True)

class ZhaFan(zha.Entity, FanEntity):
    """Representation of a ZHA fan."""

    _domain = DOMAIN
    value_attribute = 0

    def attribute_updated(self, attribute, value):
        """Handle attribute update from device."""
        _LOGGER.debug("Attribute updated: %s %s %s", self, attribute, value)
        if attribute == self.value_attribute:
            self._state = value
            self.async_schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return SPEED_LIST

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._state

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        if self._state is None:
            return False
        return self._state != SPEED_OFF

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the entity on."""
        if speed is None:
            speed = SPEED_ON

        await self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.async_set_speed(SPEED_OFF)

    async def async_set_speed(self: FanEntity, speed: str) -> None:
        """Set the speed of the fan."""
        await self._endpoint.fan.write_attributes({
            'fan_mode': SPEED_TO_VALUE[speed]})

        self._state = speed
        self.async_schedule_update_ha_state()

    async def async_update(self):
        """Retrieve latest state."""
        result = await zha.safe_read(self._endpoint.fan, ['fan_mode'])
        new_value = result.get('fan_mode', None)
        self._state = VALUE_TO_SPEED.get(new_value, self._state)
        _LOGGER.debug(self._state)

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False
