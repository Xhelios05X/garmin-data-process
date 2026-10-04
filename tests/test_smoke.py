"""Smoke tests: verify that the package is installed and consistent."""

from importlib.metadata import version

import garmin_metrics


def test_version_matches_installed_metadata():
    # __version__ in the code must match the version from pyproject.toml.
    # If someone bumps only one of them, this test fails.
    assert garmin_metrics.__version__ == version("garmin-metrics")
