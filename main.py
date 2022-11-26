import gc

# noinspection PyUnresolvedReferences
import micropython

import config_local
import time
import sys
import machine

import switch

try:
    # noinspection PyUnresolvedReferences
    import config
except (ImportError, SyntaxError):
    pass

# import upip
# upip.install("micropython-mcron")
import mcron


last_timesync = last_config_fetch = time.time()
switchpin = dict()
buttonstates = dict()
do_switch_by_button = False
do_time_sync = False
do_fetch_config = False


def connect_network():
    # noinspection PyUnresolvedReferences
    import network
    # noinspection PyUnresolvedReferences
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(config_local.wifi_ssid, config_local.wifi_password)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())


def sync_time_cb(callback_id, current_time, callback_memory):
    _ = callback_id
    _ = current_time
    _ = callback_memory
    global do_time_sync
    do_time_sync = True


def sync_time():
    # noinspection PyUnresolvedReferences
    import ntptime
    try:
        ntptime.settime()
    except (OSError, OverflowError):
        time.sleep(5)
        connect_network()
        try:
            ntptime.settime()
        except (OSError, OverflowError) as e:
            # maybe later
            pass
            # print("Could not sync to ntp time: {}".format(repr(e)))
            # f = open("/exception.log", "a")
            # f.write("Could not sync to ntp time: {}\ntime: {}\n".format(repr(e), time.gmtime()))
            # f.close()


def fetch_config_cb(callback_id, current_time, callback_memory):
    _ = callback_id
    _ = current_time
    _ = callback_memory
    global do_fetch_config
    do_fetch_config = True


def fetch_config():
    try:
        import urequests as requests
    except ImportError:
        # noinspection PyUnresolvedReferences
        import requests

    gc.collect()
    try:
        r = requests.get(config_local.config_url)
    except OSError:
        connect_network()
        try:
            r = requests.get(config_local.config_url)
        except OSError:
            return  # spaeter vielleicht?

    try:
        hash_before = get_hash(open("/config.py", "r").read())
    except OSError:
        hash_before = "a"
    f = open("/config.py", "w")
    f.write(r.content)
    f.close()
    hash_after = get_hash(open("/config.py", "r").read())
    global last_config_fetch
    last_config_fetch = time.time()
    if hash_before != hash_after:
        # noinspection PyUnresolvedReferences
        machine.soft_reset()
    global do_fetch_config
    do_fetch_config = False


def get_hash(data: str) -> str:
    import hashlib
    import binascii
    # noinspection PyTypeChecker
    return binascii.hexlify(hashlib.sha1(data).digest()).decode("utf-8")


def switch_callback(callback_id, current_time, callback_memory):
    _ = current_time
    _ = callback_memory
    print(callback_id)
    switch_name, action = callback_id.rsplit("_", 1)
    global switchpin, buttonstates
    if action == "on":
        buttonstates[switch_name] = True
        switchpin[switch_name].on()
    else:
        buttonstates[switch_name] = False
        switchpin[switch_name].off()


def sec_to_utc(t: int) -> int:
    utc_t = int(t - config.time_diff_utc * 60 * 60)
    if utc_t < 0:
        utc_t += 24 * 60 * 60
    if utc_t > 24 * 60 * 60 - 1:
        utc_t -= 24 * 60 * 60
    return utc_t


def sun_sec_utc(t: str, add_hour: int = 0, add_minute: int = 0) -> int:
    if t not in ("sunrise", "sunset"):
        raise ValueError("parameter t must be 'sunset' or 'sunrise'!")
    if "longitude" not in dir(config) or "latitude" not in dir(config):
        raise ValueError("config options 'longitude' and 'latitude' must be set!")

    # micropython-suntime (GitHub) has to be put into the /lib directory
    import suntime
    import time

    day = micropython.const(2)
    hour = micropython.const(3)
    minute = micropython.const(4)

    now = time.gmtime()
    s = suntime.Sun(config.latitude, config.longitude)
    if t == "sunrise":
        sun_time = s.get_sunrise_time(date=now)
    else:
        sun_time = s.get_sunset_time(date=now)
    if sun_time[day] != now[day]:
        # FIXME sunset is tomorrow but at 00:00 the sunset time for the next day is calculated
        return 23*60*60 + 59*60
    # add_* can be negative for subtracting time
    # examples:
    # 2, 0 for 120 minutes after sunset
    # -1, -30 for 90 minutes before sunset
    # 0, -45 for 45 minutes before sunset
    adj_sun_time = sun_time[hour]*60*60 + sun_time[minute]*60 + add_hour*60*60 + add_minute*60

    # capped at 23:59
    if adj_sun_time >= 24*60*60:
        # FIXME sunset is tomorrow but at 00:00 the sunset time for the next day is calculated
        return 23*60*60 + 59*60
    return adj_sun_time


def replace_switch_cron(callback_id, current_time=None, callback_memory=None):
    # type: (str, int, str) -> None
    _ = current_time
    _ = callback_memory
    switch_name, action = callback_id.replace("refresh_", "").rsplit("_", 1)
    times = set()
    my_callback_id = "{}_{}".format(switch_name, action)
    mcron.remove(my_callback_id)
    mcron.remove(callback_id)
    refresh_later = False
    for t in config.switches[switch_name][action]:
        if isinstance(t[0], str):
            refresh_later = True
            if t[0] == "sunset":
                times.add(sun_sec_utc("sunset", t[1], t[2]))
            elif t[0] == "sunrise":
                times.add(sun_sec_utc("sunrise", t[1], t[2]))
        else:
            times.add(sec_to_utc(int(t[0] * 60 * 60 + t[1] * 60)))
    if refresh_later:
        mcron.insert(mcron.PERIOD_DAY, {0}, "refresh_{}".format(my_callback_id), replace_switch_cron)
    if times:
        mcron.insert(mcron.PERIOD_DAY, times, my_callback_id, switch_callback)


def switch_by_button_callback(pin):
    global do_switch_by_button
    do_switch_by_button = pin


def switch_by_button(pin):
    if not pin:
        return False
    global switchpin, buttonstates
    for sw in config.switches:
        if "button" in config.switches[sw]:
            if "Pin({})".format(config.switches[sw]["button"]) == str(pin):
                if sw not in buttonstates or buttonstates[sw] is False:
                    switchpin[sw].on()
                    buttonstates[sw] = True
                else:
                    switchpin[sw].off()
                    buttonstates[sw] = False
                return True
    return False


def main():
    try:
        connect_network()
        sync_time()
        mcron.init_timer()
        mcron.remove_all()

        if "config" not in globals():
            fetch_config()  # and soft_reset if config is old or not loaded

        mcron.insert(config.fetch_config_interval * 60, {0}, "fetch_config", fetch_config_cb, from_now=True)
        mcron.insert(config.time_sync_interval * 60, {0}, "time_sync", sync_time_cb, from_now=True)

        global switchpin, do_time_sync, do_fetch_config, do_switch_by_button
        for switch_name in config.switches:
            switchpin[switch_name] = switch.Switch(
                gpio=config.gpio,
                code=config.switches[switch_name]["code"],
                protocol=config.switches[switch_name]["protocol"]
            )
            if "button" in config.switches[switch_name]:
                tmp_pin = machine.Pin(config.switches[switch_name]["button"], machine.Pin.IN, machine.Pin.PULL_DOWN)
                tmp_pin.irq(handler=switch_by_button_callback, trigger=machine.Pin.IRQ_RISING)

            for action in ("on", "off"):
                replace_switch_cron("{}_{}".format(switch_name, action))

        while True:
            if do_fetch_config:
                connect_network()
                fetch_config()
            if do_time_sync:
                sync_time()
            if do_switch_by_button:
                if switch_by_button(do_switch_by_button):
                    do_switch_by_button = False
                else:
                    # got an error, maybe ISR ran twice?
                    do_switch_by_button = False
            time.sleep(0.5)
    except Exception as e:
        f = open("/exception.log", "a")
        f.write("----------\n")
        # noinspection PyUnresolvedReferences
        sys.print_exception(e, f)  # documentation says "file=f" but that does not work
        # noinspection PyUnresolvedReferences
        sys.print_exception(e)  # to stdout
        f.write("\ntime: {}\n".format(time.gmtime()))
        f.write("----------\n")
        f.close()
        # noinspection PyUnresolvedReferences
        machine.Pin(2, machine.Pin.OUT).on()  # enable onboard LED


if __name__ == '__main__':
    main()
