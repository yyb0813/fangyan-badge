"""Nametag with a mood seal, minute clock and one-shot LED greeting."""

import framebuf
import time

from apps.base_app import BaseApp
from lib.button import UserA, UserB
from lib.epd import display
from lib.led_bar import leds, NUM_LEDS


class NametagApp(BaseApp):
    def __init__(self, name: str | None = None) -> None:
        self.name = "Nametag"
        self.sleep_ms = 50
        self.launched = False
        self._mood = 0
        self._shown_mood = None
        self._last_minute = None
        self._needs_background = True
        self._signal_step = None
        self._signal_due = None

    def _signal(self):
        if self._signal_step is None or not display.is_done_updating():
            return
        now = time.ticks_ms()
        if self._signal_due is not None and time.ticks_diff(now, self._signal_due) < 140:
            return
        step = self._signal_step
        if step >= 20:
            leds.clear()
            self._signal_step = None
            return
        pixels = [(0, 0, 0)] * NUM_LEDS
        if step < 14:
            position = step if step < 8 else 14 - step
            pixels[position] = (3, 1, 0)
        elif step % 2 == 0:
            pixels = [(2, 2, 2)] * NUM_LEDS
        leds.set(pixels)
        self._signal_step += 1
        self._signal_due = now

    def run(self):
        if self.launched:
            leds.clear_sequence()
            leds.clear()
            self._signal_step = None
            self._needs_background = True
            self._shown_mood = None
            self._last_minute = None
            with open("/data/clock-digits.bin", "rb") as source:
                self._digits = source.read()
            with open("/data/date-glyphs.bin", "rb") as source:
                self._date_glyphs = source.read()

        if UserA.pressed():
            self._mood = (self._mood + 1) % 3
        if UserB.pressed() and self._signal_step is None:
            self._signal_step = 0
            self._signal_due = None
        self._signal()

        minute = time.localtime()[:5]
        if not display.is_done_updating() or self._signal_step is not None:
            return
        if minute == self._last_minute and self._mood == self._shown_mood:
            return

        if self._needs_background:
            display.draw_png("/data/graphics/hello_i_am_blank.png")
            with open("/data/fangyan-name.bin", "rb") as source:
                name_bits = bytearray(source.read())
            name_image = framebuf.FrameBuffer(name_bits, 640, 260, framebuf.MONO_HLSB)
            display.black.blit(name_image, 160, 259)
            self._needs_background = False

        if self._mood != self._shown_mood:
            with open("/data/mood-%d.bin" % self._mood, "rb") as source:
                seal_bits = bytearray(source.read())
            seal = framebuf.FrameBuffer(seal_bits, 96, 144, framebuf.MONO_HLSB)
            display.black.fill_rect(778, 390, 96, 144, 0)
            display.red.blit(seal, 778, 390)
            self._shown_mood = self._mood

        display.black.fill_rect(0, 557, 960, 115, 0)
        display.red.fill_rect(0, 557, 960, 115, 1)
        date = "%04d年%02d月%02d日" % minute[:3]
        for index, char in enumerate(date):
            digit = "0123456789年月日".index(char)
            glyph = framebuf.FrameBuffer(bytearray(self._date_glyphs[digit * 96:(digit + 1) * 96]), 24, 32, framebuf.MONO_HLSB)
            display.red.blit(glyph, 348 + index * 24, 563)
        for index, char in enumerate("%02d:%02d" % minute[3:5]):
            digit = "0123456789:".index(char)
            glyph = framebuf.FrameBuffer(bytearray(self._digits[digit * 320:(digit + 1) * 320]), 40, 64, framebuf.MONO_HLSB)
            display.red.blit(glyph, 380 + index * 40, 600)
        display.update()
        self._last_minute = minute
