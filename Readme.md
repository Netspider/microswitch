# Microswitch

With this micropython code, a microcontroller with micropython support and an rf sender you can automatically switchsockets on a timer.

The configuration is hosted on a website, so you can change parameters without flashing the microcontroller.

## my Hardware

- ESP-WROOM-32 board with USB and Wi-Fi
- FS1000A 433MHz transmitter
- breadboard 10x25
- 3 cables

## Installation

- copy `config_local.py.sample` to `config_local.py` and change the settings
- copy `config.py.sample` to `config.py` and change the settings
- push `config.py` to a webpage (github pages or gist?)
- install [MicroPython](https://micropython.org/download/]) on your microcontroller
- flash `*.py` to your microcontroller (except config.py)
- connect to the microcontroller REPL shell and install mcron:

```python
import network
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("SSID", "PASSWORD")

ìmport upip
upip.install("micropython-mcron")
```