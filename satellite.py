import requests
from skyfield.api import load
class Satellite:
    def __init__(self, norad_id):
        self.norad_id = norad_id

    def get_tle_data(self):
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={self.norad_id}&FORMAT=TLE"
        filename = f'tle-CATNR-{self.norad_id}.txt'
        satellites = load.tle_file(url, filename=filename)
        return satellites[0]