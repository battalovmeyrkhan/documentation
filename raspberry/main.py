# ──────────────────────────────────────────────
# 0. Конфигурация проекта
# ──────────────────────────────────────────────

from pibody import WiFi
from helper import is_interval_elapsed, true_for_interval
from bot import bot
import secrets
from machine import Pin
from micropython import const

btn = Pin(21, Pin.IN)
led = Pin("LED", Pin.OUT)

tg_poll_id = const(0)
tg_poll_interval = const(1000)
btn_id = const(1)
btn_interval = const(1000)

# ──────────────────────────────────────────────
# 1. Подключение к WiFi
# ──────────────────────────────────────────────

wifi = WiFi()
wifi.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)

# ──────────────────────────────────────────────
# Главный цикл
# ──────────────────────────────────────────────

while True:
    if is_interval_elapsed(tg_poll_id, tg_poll_interval):
        bot.polling()

    print(true_for_interval(btn_id, btn.value(), btn_interval))
    if true_for_interval(btn_id, btn.value(), btn_interval):
        led.on()
    else:
        led.off()
