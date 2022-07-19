import gc

import config_local
import time

import switch

try:
    # noinspection PyUnresolvedReferences
    import config
except ImportError:
    pass

# import upip
# upip.install("micropython-mcron")
import mcron


last_timesync = last_config_fetch = time.time()
switchpin = dict()
do_time_sync = False
do_fetch_config = False


def connect_network():
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
    except OSError:
        connect_network()
        try:
            ntptime.settime()
        except OSError as e:
            # dann eben jetzt nicht
            print("Could not sync to ntp time: {}".format(repr(e)))


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
    r = requests.get(config_local.config_url)
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
        import machine
        machine.soft_reset()


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
    global switchpin
    if action == "on":
        switchpin[switch_name].on()
    else:
        switchpin[switch_name].off()


def sec_to_utc(t: int) -> int:
    utc_t = int(t - config.time_diff_utc * 60 * 60)
    if utc_t < 0:
        utc_t += 24 * 60 * 60
    if utc_t > 24 * 60 * 60 - 1:
        utc_t -= 24 * 60 * 60
    return utc_t


def main():
    connect_network()
    sync_time()
    mcron.init_timer()
    mcron.remove_all()

    if "config" not in globals():
        fetch_config()  # and soft_reset if config is old or not loaded

    mcron.insert(config.fetch_config_interval * 60, {0}, "fetch_config", fetch_config_cb, from_now=True)
    mcron.insert(config.time_sync_interval * 60, {0}, "time_sync", sync_time_cb, from_now=True)

    global switchpin, do_time_sync, do_fetch_config
    for switch_name in config.switches:
        switchpin[switch_name] = switch.Switch(
            gpio=config.gpio,
            code=config.switches[switch_name]["code"],
            protocol=config.switches[switch_name]["protocol"]
        )
        for action in ("on", "off"):
            times = set()
            for t in config.switches[switch_name][action]:
                times.add(sec_to_utc(int(t[0] * 60 * 60 + t[1] * 60)))
            if times:
                mcron.insert(mcron.PERIOD_DAY, times, "{}_{}".format(switch_name, action), switch_callback)

    while True:
        if do_fetch_config:
            fetch_config()
        if do_time_sync:
            sync_time()
        time.sleep(5)


if __name__ == '__main__':
    main()
