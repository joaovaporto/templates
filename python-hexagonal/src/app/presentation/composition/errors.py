class ConfigurationError(Exception):
    """The wiring or the settings are wrong. Raised at startup, never at first use."""
