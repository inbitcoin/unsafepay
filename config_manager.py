import os.path
from configparser import ConfigParser

FNAME = 'config'


def add_section(config, name):
    if not config.has_section(name):
        config.add_section(name)


def load():
    config = ConfigParser()
    if os.path.isfile(FNAME):
        config.read(FNAME)
    add_section(config, 'telegram')
    add_section(config, 'lighter')
    return config


def save(config):
    with open(FNAME, 'wt') as fd:
        config.write(fd)


def print(config):
    for section in config.sections():
        print(section)
        for option in config.options(section):
            print(option, config[section][option])
