class NotInstalledError(RuntimeError):
    """Exception raised if the dependencies for a particular PDF to
    image backend are not installed."""
