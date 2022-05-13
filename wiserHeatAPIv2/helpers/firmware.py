from ..const import (
    TEXT_UNKNOWN
)

class _WiserFirmwareUpgradeItem:
    """Data structure for upgrade info for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self) -> int:
        "Get the id of the firmware filename"
        return self._data.get("id",0)

    @property
    def filename(self) -> str:
        "Get the filename of the firmware file"
        return self._data.get("FirmwareFilename", TEXT_UNKNOWN)


class _WiserFirmareUpgradeInfo:
    """Data structure to hold upgrade file info for a Wiser Hub"""
    def __init__(self, data: dict):
        self._data = data
        self._items = []
        for item in self._data:
            self._items.append(_WiserFirmwareUpgradeItem(item))

    @property
    def all(self) -> dict:
        return self._items

    def by_id(self, id) -> _WiserFirmwareUpgradeItem:
        return [item for item in self._items if item.id == id][0]