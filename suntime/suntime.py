# taken from
# https://github.com/SatAgro/suntime
# and stripped down to work on micropython

import math
import time
from suntime import microcalendar as calendar
# from typing import Sequence, Tuple, Optional


class SunTimeException(Exception):

    def __init__(self, message):
        super(SunTimeException, self).__init__(message)


class Sun:
    """
    Approximated calculation of sunrise and sunset datetimes. Adapted from:
    https://stackoverflow.com/questions/19615350/calculate-sunrise-and-sunset-times-for-a-given-gps-coordinate-within-postgresql
    """
    def __init__(self, lat, lon):
        # type: (Sun, float, float) -> Sun
        """
        initalises Sun class
        :param lat: Latitude
        :param lon: Longitude
        :return: Sun class
        """
        self._lat = lat
        self._lon = lon

    def get_sunrise_time(self, date=None):
        # type: (Sun, Optional[Sequence[int]]) -> Tuple[int]
        """
        Calculate the sunrise time for given date.
        :param date: Reference date. Today if not provided.
        :return: UTC sunrise time tuple
        :raises: SunTimeException when there is no sunrise and sunset on given location and date
        """
        date = time.gmtime() if date is None else date
        sr = self._calc_sun_time(date, True)
        if sr is None:
            raise SunTimeException('The sun never rises on this location (on the specified date)')
        else:
            return sr

    def get_sunset_time(self, date=None):
        # type: (Sun, Optional[Sequence[int]]) -> Optional[Tuple[int]]
        """
        Calculate the sunset time for given date.
        :param date: Reference date. Today if not provided.
        :return: UTC sunset datetime
        :raises: SunTimeException when there is no sunrise and sunset on given location and date.
        """
        date = time.gmtime() if date is None else date
        ss = self._calc_sun_time(date, False)
        if ss is None:
            raise SunTimeException('The sun never sets on this location (on the specified date)')
        else:
            return ss

    def _calc_sun_time(self, date, isRiseTime=True, zenith=90.8):
        # type: (Sun, Sequence[int], bool, float) -> Optional[Tuple[int]]
        """
        Calculate sunrise or sunset date.
        :param date: Reference date
        :param isRiseTime: True if you want to calculate sunrise time.
        :param zenith: Sun reference zenith
        :return: UTC sunset or sunrise datetime
        :raises: SunTimeException when there is no sunrise and sunset on given location and date
        """
        # isRiseTime == False, returns sunsetTime
        day = date[2]
        month = date[1]
        year = date[0]

        TO_RAD = math.pi/180.0

        # 1. first calculate the day of the year
        N1 = math.floor(275 * month / 9)
        N2 = math.floor((month + 9) / 12)
        N3 = (1 + math.floor((year - 4 * math.floor(year / 4) + 2) / 3))
        N = N1 - (N2 * N3) + day - 30

        # 2. convert the longitude to hour value and calculate an approximate time
        lngHour = self._lon / 15

        if isRiseTime:
            t = N + ((6 - lngHour) / 24)
        else:  # sunset
            t = N + ((18 - lngHour) / 24)

        # 3. calculate the Sun's mean anomaly
        M = (0.9856 * t) - 3.289

        # 4. calculate the Sun's true longitude
        L = M + (1.916 * math.sin(TO_RAD*M)) + (0.020 * math.sin(TO_RAD * 2 * M)) + 282.634
        L = self._force_range(L, 360)  # NOTE: L adjusted into the range [0,360)

        # 5a. calculate the Sun's right ascension

        RA = (1/TO_RAD) * math.atan(0.91764 * math.tan(TO_RAD*L))
        RA = self._force_range(RA, 360)  # NOTE: RA adjusted into the range [0,360)

        # 5b. right ascension value needs to be in the same quadrant as L
        Lquadrant = (math.floor(L/90)) * 90
        RAquadrant = (math.floor(RA/90)) * 90
        RA = RA + (Lquadrant - RAquadrant)

        # 5c. right ascension value needs to be converted into hours
        RA = RA / 15

        # 6. calculate the Sun's declination
        sinDec = 0.39782 * math.sin(TO_RAD*L)
        cosDec = math.cos(math.asin(sinDec))

        # 7a. calculate the Sun's local hour angle
        cosH = (math.cos(TO_RAD*zenith) - (sinDec * math.sin(TO_RAD*self._lat))) / (cosDec * math.cos(TO_RAD*self._lat))

        if cosH > 1:
            return None     # The sun never rises on this location (on the specified date)
        if cosH < -1:
            return None     # The sun never sets on this location (on the specified date)

        # 7b. finish calculating H and convert into hours

        if isRiseTime:
            H = 360 - (1/TO_RAD) * math.acos(cosH)
        else:  # setting
            H = (1/TO_RAD) * math.acos(cosH)

        H = H / 15

        # 8. calculate local mean time of rising/setting
        T = H + RA - (0.06571 * t) - 6.622

        # 9. adjust back to UTC
        UT = T - lngHour
        UT = self._force_range(UT, 24)   # UTC time in decimal format (e.g. 23.23)

        # 10. Return
        hr = self._force_range(int(UT), 24)  # type: int
        minute = int(round((UT - int(UT))*60, 0))
        if minute == 60:
            hr += 1
            minute = 0

        # 10. check corner case https://github.com/SatAgro/suntime/issues/1
        if hr == 24:
            hr = 0
            day += 1
            
            if day > calendar.monthrange(year, month)[1]:
                day = 1
                month += 1

                if month > 12:
                    month = 1
                    year += 1

        # the last 4 elements are seconds, weekday, yearday and DST_flag
        # which are corrected when converting to timestamp and back
        outdate = (year, month, day, hr, minute, 0, 0, 0, -1)
        return time.gmtime(time.mktime(outdate))

    @staticmethod
    def _force_range(v, maximum):
        # force v to be >= 0 and < max
        if v < 0:
            return v + maximum
        elif v >= maximum:
            return v - maximum

        return v


if __name__ == '__main__':
    sun = Sun(85.0, 21.00)
    try:
        print(sun.get_sunrise_time())
        print(sun.get_sunset_time())

    # On a special date in UTC
        # tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst
        abd = (2014, 1, 3, 10, 0, 0, 0, 0, -1)
        abd_sr = sun.get_sunrise_time(abd)
        abd_ss = sun.get_sunset_time(abd)
        print(abd_sr)
        print(abd_ss)
    except SunTimeException as e:
        print("Error: {0}".format(e))
