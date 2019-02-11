from noodles import (schedule, has_scheduled_methods)
from noodles.interface import PromisedObject


@has_scheduled_methods
class Results(dict):
    """
    Encapsulate the results of a workflow by storing the
    results or promised objects in a dictionary.
    """
    def __init__(self, init):
        self.state = init

    def __getitem__(self, val):
        if isinstance(val, PromisedObject):
            return schedule(self.state[val])
        else:
            return self.state[val]

    def __setitem__(self, key, val):
        self.state[key] = val

    def __deepcopy__(self, _):
        return Results(self.state.copy())
