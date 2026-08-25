"""Runtime data types for MAIKA."""

from __future__ import annotations

from dataclasses import dataclass

from .api import MaikaApiClient
from .coordinator import MaikaDataUpdateCoordinator
from .license_manager import MaikaLicenseManager


@dataclass(slots=True)
class MaikaRuntimeData:
    """Objects attached to a MAIKA config entry while loaded."""

    client: MaikaApiClient
    coordinator: MaikaDataUpdateCoordinator
    license_manager: MaikaLicenseManager
