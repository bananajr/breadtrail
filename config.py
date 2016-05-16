import configparser
import os

_ledger_config_dir = os.path.expanduser('~/.ledger')


_defaults = {
        'ledger': {
            'path': os.path.join(_ledger_config_dir, 'ledger.dat'),
        },
}

class BreadTrailConfig(configparser.ConfigParser):
    def __init__(self):
        configparser.ConfigParser.__init__(self)
        self.read_dict(_defaults)
        self.read(os.path.join(_ledger_config_dir, 'config'))

    def get_ledger_path(self):
        path = os.path.expanduser(config.get('ledger', 'path'))
        if not os.path.isabs(path):
            path = os.path.join(_ledger_config_dir, path)
        return path


config = BreadTrailConfig()

