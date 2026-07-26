import os

import pytest


@pytest.mark.skipif(not os.getenv("ENERGYPLUS_HOME"), reason="EnergyPlus is not installed in the test environment")
def test_energyplus_home_is_configured():
    from core.config import settings

    assert settings.energyplus_home is not None
    assert settings.energyplus_home.exists()
