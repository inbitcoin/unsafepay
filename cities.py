import os

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def read_cities():
    with open(os.path.join(__location__, 'cities.txt'), 'rt') as fd:
        return [x.strip() for x in fd.readlines()]
