"""Load basin definitions from a replaceable JSON configuration file."""

import json
from pathlib import Path

from .models import Basin


def load_basins(path):
    basins = [Basin(**item) for item in json.loads(Path(path).read_text())]
    if not basins or len({basin.id for basin in basins}) != len(basins):
        raise ValueError("Configure at least one basin with unique IDs.")
    return {basin.id: basin for basin in basins}
