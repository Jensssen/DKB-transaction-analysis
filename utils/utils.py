from typing import Dict


def flatten_dict(dd: Dict, separator: str = '_', prefix: str = '') -> Dict:
    """Flattens a nested dictionary and returns it."""
    return {prefix + separator + k if prefix else k: v
            for kk, vv in dd.items()
            for k, v in flatten_dict(vv, separator, kk).items()
            } if isinstance(dd, dict) else {prefix: dd}
