"""Reference data tables (JSON) shipped with the rules."""
import json
from importlib.resources import files


def load(name, encoding=None):
    return json.loads(files(__name__).joinpath(name).read_text(encoding=encoding))
