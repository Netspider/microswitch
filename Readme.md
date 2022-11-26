# Microswitch

With this micropython code, a microcontroller with micropython support and an rf sender you can automatically switch sockets on a timer.

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

## Advanced

### Sun
You can use basic sundown/sunrise calculation instead of a constant time. `("sunset", -1, 30)` triggers 1.5 hours before sunset. If the calculated time is after midnight (or before 00:00 with sunrise) it will likely fail!

### Manual override

If you sometimes want to switch your appliances manually you can do so with added buttons:

- connect one leg of the button to 3.3V
- connect the other leg to a GPIO (I use 18, 19 and 21 for 3 buttons)
- add the GPIO to the switch config (`switches["xxx"]["button"] = 18` for GPIO 18)
- send your config to the device

The buttons are initialised as **off** on reboot and the state is toggled when you press the button and set when an appliance is automatically switched. There is a delay of around 1 second before something happens.