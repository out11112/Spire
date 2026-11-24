"""The error contract: an action is rejected whole with a message for the player."""


class InvalidAction(ValueError): pass

def require(condition, message):
    if not condition: raise InvalidAction(message)
