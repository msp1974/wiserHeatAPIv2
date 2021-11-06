# Exception Handlers
class WiserHubConnectionError(Exception):
    pass


class WiserHubAuthenticationError(Exception):
    pass


class WiserHubRESTError(Exception):
    pass


class WiserHubNotImplementedError(Exception):
    #_LOGGER.info("Function not yet implemented")
    pass
