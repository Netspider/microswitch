import machine
import time


class Switch:
    def __init__(self, gpio: int, code: str, protocol: int = 1, pulse_length: int = None, repeat_transmit: int = 8,
                 debug: bool = False):
        self.code = code
        self.protocol = protocol
        self.repeat_transmit = repeat_transmit
        self.debug = debug
        self.debugpin = machine.Pin(2, machine.Pin.OUT)

        if protocol == 1:
            self.pulse_length = 350
        elif protocol == 2:
            self.pulse_length = 650
        elif protocol == 3:
            self.pulse_length = 100
        else:
            self.pulse_length = 180

        # set custom pulse length
        self.pin = machine.Pin(gpio, machine.Pin.OUT)

        if pulse_length:
            self.pulse_length = pulse_length

    def on(self):
        if self.debug:
            self.debugpin.on()
        if self.protocol in (1, 2, 3):
            self._send("{}0F".format(self.code))
        elif self.protocol in (4,):
            self._send("{}01".format(self.code))
        if self.debug:
            self.debugpin.off()

    def off(self):
        if self.debug:
            self.debugpin.on()
        if self.protocol in (1, 2, 3):
            self._send("{}F0".format(self.code))
        elif self.protocol in (4,):
            self._send("{}10".format(self.code))
        if self.debug:
            self.debugpin.off()

    def _transmit(self, num_high_pulses: int, num_low_pulses: int):
        self.pin.on()
        time.sleep_us(self.pulse_length * num_high_pulses)
        self.pin.off()
        time.sleep_us(self.pulse_length * num_low_pulses)

    def _send_t0(self):
        self._transmit(1, 3)
        self._transmit(1, 3)

    def _send_t1(self):
        self._transmit(3, 1)
        self._transmit(3, 1)

    def _send_tf(self):
        self._transmit(1, 3)
        self._transmit(3, 1)

    def _send_sync(self):
        if self.protocol in (1, 4):
            self._transmit(1, 31)
        elif self.protocol == 2:
            self._transmit(1, 10)
        else:
            self._transmit(1, 71)

    def _send(self, code):
        self._send_sync()
        for i in range(self.repeat_transmit):
            for c in code:
                if c == "0":
                    self._send_t0()
                elif c == "1":
                    self._send_t1()
                elif c.lower() == "f":
                    self._send_tf()
            self._send_sync()
