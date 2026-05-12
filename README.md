# Telegram Bot + Raspberry Pi Pico W — Управление GPIO и шаговым двигателем

> MicroPython-проект: удалённое управление Pico W через Telegram, управление шаговым двигателем через ULN2003, неблокирующая логика таймеров.

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Архитектура системы](#2-архитектура-системы)
3. [Workflow системы](#3-workflow-системы)
4. [Структура проекта](#4-структура-проекта)
5. [Подробное описание логики кода](#5-подробное-описание-логики-кода)
6. [GPIO Configuration](#6-gpio-configuration)
7. [Подключение оборудования](#7-подключение-оборудования)
8. [Hardware Requirements](#8-hardware-requirements)
9. [Software Requirements](#9-software-requirements)
10. [Installation & Setup](#10-installation--setup)
11. [Telegram Commands](#11-telegram-commands)
12. [Motor Control Logic](#12-motor-control-logic)
13. [Timing Logic](#13-timing-logic)
14. [Security Considerations](#14-security-considerations)
15. [Performance / Embedded Considerations](#15-performance--embedded-considerations)
16. [Future Improvements](#16-future-improvements)
17. [Заключение](#17-заключение)

---

## 1. Обзор проекта

Проект реализует систему удалённого управления периферией Raspberry Pi Pico W через Telegram Bot. Устройство подключается к Wi-Fi и периодически опрашивает Telegram API (long polling). Пользователь отправляет команды через Telegram — бот их обрабатывает и управляет GPIO: включает LED, читает кнопки, вращает шаговый двигатель через драйвер ULN2003.

**Что умеет система:**

- Подключаться к Wi-Fi при старте
- Принимать команды из Telegram в реальном времени (с задержкой polling-интервала)
- Отвечать на текстовые команды и нажатия inline-кнопок
- Управлять встроенным LED по нажатию физической кнопки
- Вращать шаговый двигатель (дозатор) в обоих направлениях
- Возвращать уникальный ID устройства

**Зачем это нужно:**

Классический use-case для IoT: физическое устройство (Pico W) управляется дистанционно через привычный мессенджер без выделенного сервера, мобильного приложения или VPN. Telegram Bot API работает как посредник между пользователем и железом.

---

## 2. Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛЬ                            │
│                    (Telegram-клиент)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTPS / Telegram Bot API
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TELEGRAM SERVERS                             │
│              api.telegram.org/bot<TOKEN>/                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │  getUpdates (polling) / sendMessage
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RASPBERRY PI PICO W                           │
│                                                                 │
│  ┌────────────┐    ┌────────────┐    ┌──────────────────────┐  │
│  │  main.py   │───▶│   bot.py   │───▶│    telegram.py       │  │
│  │ (главный   │    │ (команды   │    │ (TeleBot: HTTP,      │  │
│  │   цикл)    │    │  и хендл.) │    │  dispatch, keyboard) │  │
│  └─────┬──────┘    └────────────┘    └──────────────────────┘  │
│        │                                                        │
│        │    ┌────────────┐    ┌──────────────────────────────┐ │
│        ├───▶│  helper.py │    │       dispencer.py           │ │
│        │    │ (таймеры   │    │   (Dispencer → Motor →       │ │
│        │    │  без sleep)│    │    ULN2003 → GPIO 0-3)       │ │
│        │    └────────────┘    └──────────────────────────────┘ │
│        │                                                        │
│  GPIO: LED("LED")  BTN(21)  MOTOR(0,1,2,3)  BTN_REV(20)       │
└─────────────────────────────────────────────────────────────────┘
```

**Поток данных:**

```
Команда из Telegram
    → Telegram API (HTTPS)
        → TeleBot.polling() (telegram.py)
            → TeleBot._dispatch() (разбор update)
                → обработчик в bot.py
                    → GPIO-действие или ответ в чат
```

---

## 3. Workflow системы

### Инициализация

```
Старт main.py
    │
    ├─ Импорт модулей (pibody, helper, bot, secrets, machine)
    ├─ Инициализация Pin(21, IN)  — кнопка
    ├─ Инициализация Pin("LED", OUT) — встроенный LED
    ├─ Определение констант: интервалы polling и кнопки
    │
    └─ WiFi.connect(SSID, PASSWORD)
           │
           └─ При успехе → главный цикл while True
```

### Главный цикл `while True`

```
while True:
    │
    ├─ is_interval_elapsed(tg_poll_id, 1000ms)?
    │       ДА → bot.polling()
    │              │
    │              ├─ getUpdates от Telegram
    │              │       ├─ Нет новых → ничего
    │              │       └─ Есть update → _dispatch(update)
    │              │               ├─ callback_query → cb-обработчик
    │              │               └─ message → cmd-обработчик или echo
    │              └─ Обновить _offset (пометить update как обработанный)
    │
    └─ true_for_interval(btn_id, btn.value(), 1000ms)?
            ДА  → led.on()
            НЕТ → led.off()
```

Оба события обрабатываются в одном цикле без блокировки: `is_interval_elapsed` и `true_for_interval` возвращают результат мгновенно, не останавливая выполнение.

---

## 4. Структура проекта

```
raspberry/
├── main.py        # Точка входа. Wi-Fi, главный цикл, GPIO-логика кнопки и LED
├── bot.py         # Обработчики команд и callback-кнопок Telegram
├── telegram.py    # Библиотека TeleBot: HTTP-запросы, диспетчер, клавиатуры
├── motor.py       # Классы Motor, FullStepMotor, HalfStepMotor
├── dispencer.py   # Класс Dispencer поверх FullStepMotor, тест в main-блоке
├── helper.py      # Таймерные функции без sleep()
└── secrets.py     # Wi-Fi SSID/пароль и Telegram Bot Token
```

### Описание каждого файла

**`main.py`** — точка входа. Инициализирует железо, подключается к Wi-Fi, запускает бесконечный цикл. Именно здесь собраны все «провода»: bot из `bot.py`, таймеры из `helper.py`, пины из `machine`.

**`bot.py`** — конфигурация бота. Создаёт экземпляр `TeleBot`, регистрирует обработчики команд (`/start`, `/help`, `/btn`, `/unique_id`), callback-обработчики для inline-кнопок, эхо для текстовых сообщений и обработчик ошибок.

**`telegram.py`** — самодельная библиотека под MicroPython. Никаких сторонних зависимостей типа `pyTelegramBotAPI` — они не совместимы с MicroPython. Всё написано поверх `urequests` и `ujson`. Реализует: HTTP-запросы к Bot API, построитель клавиатур, декораторы регистрации хендлеров, диспетчер update'ов, метод `polling()`.

**`motor.py`** — библиотека для шагового двигателя через ULN2003. Базовый класс `Motor` + два режима: `FullStepMotor` (4 состояния, 2048 шагов/оборот) и `HalfStepMotor` (8 состояний, 4096 шагов/оборот). Есть методы `step(n)`, `step_until(position)`, `step_until_angle(degrees)`.

**`dispencer.py`** — высокоуровневая обёртка над `FullStepMotor`. Класс `Dispencer` с методами `dispense()` (+50 шагов) и `dispense_reverse()` (−50 шагов). В конце файла — тест с двумя кнопками (GPIO 20 и 21), запускается напрямую для проверки железа.

**`helper.py`** — утилиты для неблокирующих таймеров. Две функции: `is_interval_elapsed(id, interval)` — проверяет, прошло ли заданное время с прошлого вызова; `true_for_interval(id, signal, interval)` — возвращает `True` на протяжении `interval` миллисекунд после получения сигнала.

**`secrets.py`** — конфигурация окружения. Три переменные: `WIFI_SSID`, `WIFI_PASSWORD`, `TG_TOKEN`. Файл не должен попадать в git-репозиторий в боевом виде.

---

## 5. Подробное описание логики кода

### `main.py` — инициализация и главный цикл

```python
from pibody import WiFi
from helper import is_interval_elapsed, true_for_interval
from bot import bot
import secrets
from machine import Pin
from micropython import const

btn = Pin(21, Pin.IN)          # Физическая кнопка
led = Pin("LED", Pin.OUT)      # Встроенный LED Pico W

tg_poll_id = const(0)          # ID таймера polling
tg_poll_interval = const(1000) # Интервал polling: 1 секунда

btn_id = const(1)              # ID таймера кнопки
btn_interval = const(1000)     # Кнопка удерживает LED включённым 1 сек после отпускания

wifi = WiFi()
wifi.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)

while True:
    if is_interval_elapsed(tg_poll_id, tg_poll_interval):
        bot.polling()  # Проверить новые сообщения в Telegram

    if true_for_interval(btn_id, btn.value(), btn_interval):
        led.on()
    else:
        led.off()
```

`const()` из `micropython` — это оптимизация: значение подставляется на этапе компиляции, не занимает RAM как переменная. Важно на устройстве с 264 КБ RAM.

### `telegram.py` — класс `TeleBot`

Это ядро системы. Ключевые части:

**HTTP-запросы (`_request`):**

```python
def _request(self, method: str, params: dict = None) -> dict:
    url = self.BASE_URL.format(token=self.token, method=method)
    body = ujson.dumps(params).encode("utf-8")  # MicroPython требует bytes
    resp = urequests.post(url, data=body, headers={"Content-Type": "application/json"})
    result = ujson.loads(resp.text)
    resp.close()  # Критично: на Pico нет GC-сборщика как на PC
    return result.get("result", {})
```

`resp.close()` вызывается явно — MicroPython не гарантирует своевременное закрытие сокетов через GC. Незакрытые соединения ведут к утечке памяти и зависанию.

**Определение `chat_id` (`get_chat_id`):**

Telegram может прислать `message`, `callback_query`, `edited_message` — структуры разные. `get_chat_id()` обходит все варианты:

```python
def get_chat_id(self, obj):
    if "chat" in obj:                     # message / edited_message
        return obj["chat"]["id"]
    if "message" in obj:                  # callback_query → message → chat
        if "chat" in obj["message"]:
            return obj["message"]["chat"]["id"]
    if "from" in obj:                     # callback_query без message
        return obj["from"]["id"]
    return None
```

**Диспетчер (`_dispatch`):**

```python
def _dispatch(self, update):
    if "callback_query" in update:
        cq = update["callback_query"]
        handler = self._handlers.get("cb:" + cq.get("data", ""))
        if handler:
            handler(cq)
        else:
            self.answer_callback_query(cq["id"])  # Закрыть спиннер
        return

    message = update.get("message")
    if not message:
        return

    text = message.get("text", "")
    if text.startswith("/"):
        cmd = text.split()[0][1:].split("@")[0]  # /start@mybot → "start"
        handler = self._handlers.get("cmd:" + cmd)
        if handler:
            handler(message)
            return

    if self._message_handler:
        self._message_handler(message)
```

**`polling()`:**

```python
def polling(self):
    updates = self.get_updates()           # getUpdates с текущим offset
    for update in updates:
        self._offset = update["update_id"] + 1  # Сдвинуть окно
        self._dispatch(update)
```

`_offset` — механизм дедупликации. После обработки update его `update_id + 1` становится новым offset. Telegram не вернёт этот update повторно.

**`inline_keyboard()`:**

```python
@staticmethod
def inline_keyboard(buttons):
    keyboard = []
    for row in buttons:
        kb_row = []
        for btn in row:
            text = btn[0]
            if len(btn) == 3 and btn[2]:      # (текст, None, url)
                kb_row.append({"text": text, "url": btn[2]})
            else:                              # (текст, callback_data)
                kb_row.append({"text": text, "callback_data": btn[1]})
        keyboard.append(kb_row)
    return {"inline_keyboard": keyboard}
```

### `bot.py` — обработчики

```python
bot = TeleBot(secrets.TG_TOKEN)

@bot.on_command("start")
def cmd_start(msg):
    name = msg.get("from", {}).get("first_name", "друг")
    bot.reply(msg, f"Привет, {name}! Я работаю на MicroPython.")

@bot.on_command("btn")
def cmd_btn(msg):
    kb = bot.inline_keyboard([
        [("Уникальный ID", "get_unique_id"), ("Инфо", "get_info")],
        [("Anthropic", None, "https://anthropic.com")],
    ])
    bot.reply(msg, "Выберите действие:", reply_markup=kb)

@bot.on_callback("get_unique_id")
def cb_get_unique_id(cq):
    bot.answer_callback_query(cq["id"])   # Убрать спиннер кнопки
    cmd_unique_id(cq["message"])          # Переиспользовать логику команды

@bot.on_message
def echo(msg):
    bot.reply(msg, f"Вы написали: {msg.get('text', '')}")

@bot.on_error
def handle_error(exc):
    print("[ERROR]", exc)
```

Декоратор `@bot.on_command("start")` вызывает `bot._handlers["cmd:start"] = func`. Это стандартный паттерн регистрации хендлеров через словарь — минимальный overhead на MicroPython.

### `helper.py` — неблокирующие таймеры

**`is_interval_elapsed(id, interval)`:**

Хранит время последнего вызова для каждого `id`. Если прошло больше `interval` мс — возвращает `True` и обновляет время.

```python
def is_interval_elapsed(id, interval):
    if id not in id_list_is_interval_elapsed:
        id_list_is_interval_elapsed.append(id)
        last_poll.append(0)
    index = id_list_is_interval_elapsed.index(id)
    if ticks_diff(ticks_ms(), last_poll[index]) > interval:
        last_poll[index] = ticks_ms()
        return True
    return False
```

`ticks_ms()` и `ticks_diff()` — MicroPython-функции для работы со временем. `ticks_diff` корректно обрабатывает переполнение счётчика (wraparound через ~49 дней).

**`true_for_interval(id, signal, interval)`:**

Если `signal == True` (кнопка нажата) — запускает таймер. Возвращает `True`, пока таймер не истёк. Используется для «растягивания» короткого нажатия кнопки на 1 секунду.

```
btn.value()=1 (нажата) → last_signal_time = now, active = True
btn.value()=0 (отпущена) → active=True, пока не прошло 1000мс
После 1000мс → active = False, LED выключается
```

---

## 6. GPIO Configuration

| GPIO | Режим | Подключение | Описание |
|------|-------|-------------|----------|
| GPIO 0 | OUT | ULN2003 IN1 | Шаговый двигатель, фаза 1 |
| GPIO 1 | OUT | ULN2003 IN2 | Шаговый двигатель, фаза 2 |
| GPIO 2 | OUT | ULN2003 IN3 | Шаговый двигатель, фаза 3 |
| GPIO 3 | OUT | ULN2003 IN4 | Шаговый двигатель, фаза 4 |
| GPIO 20 | IN | Кнопка (reverse) | Обратное вращение (в `dispencer.py`) |
| GPIO 21 | IN | Кнопка | Основная кнопка / управление LED |
| LED | OUT | Встроенный LED | Индикатор на плате Pico W |

> **Примечание:** GPIO 20 используется только в `dispencer.py` при прямом запуске. В `main.py` задействованы только GPIO 21 и LED.

---

## 7. Подключение оборудования

### Шаговый двигатель 28BYJ-48 + драйвер ULN2003

```
Raspberry Pi Pico W          ULN2003 Driver Board
──────────────────           ──────────────────────
GPIO 0  ────────────────────▶  IN1
GPIO 1  ────────────────────▶  IN2
GPIO 2  ────────────────────▶  IN3
GPIO 3  ────────────────────▶  IN4
3.3V или 5V ────────────────▶  VCC  (для 28BYJ-48 нужен 5V)
GND     ────────────────────▶  GND

ULN2003 → двигатель: разъём на плате, подключается напрямую
```

> Pico W работает от 3.3V, но 28BYJ-48 требует 5V питания. Подавать 5V на VCC ULN2003 от VBUS (pin 40 на Pico W), сигнальные линии IN1-IN4 — от GPIO (3.3V). ULN2003 совместим с 3.3V-сигналами.

### Кнопка

```
GPIO 21 ────── кнопка ────── GND
```

В коде `Pin(21, Pin.IN)` — без pull-up. Если кнопка нажата и тянет линию к GND, нужно `Pin.PULL_UP`. Если к 3.3V — `Pin.PULL_DOWN`. Уточните по схеме вашей кнопки.

### LED

Встроенный LED Pico W подключён к пину `"LED"` (не числовой номер). Им управляет `Pin("LED", Pin.OUT)`.

---

## 8. Hardware Requirements

| Компонент | Модель / Характеристика |
|-----------|------------------------|
| Микроконтроллер | Raspberry Pi Pico W (RP2040 + CYW43439 Wi-Fi) |
| Шаговый двигатель | 28BYJ-48 (5V, унипольный, 64:1 редуктор) |
| Драйвер двигателя | ULN2003 (Darlington array, совместим с 3.3V логикой) |
| Кнопка | Тактовая кнопка, нормально разомкнутая |
| Питание | USB 5V (для Pico W) или внешний источник |

---

## 9. Software Requirements

| Компонент | Версия / Источник |
|-----------|------------------|
| MicroPython | v1.21+ для RP2040 |
| pibody | MicroPython-библиотека для Pico W (Wi-Fi, GPIO) |
| urequests | Встроена в MicroPython (HTTP-клиент) |
| ujson | Встроена в MicroPython (JSON) |
| utime | Встроена в MicroPython (время) |
| Thonny IDE | Для загрузки файлов на устройство |

Сторонние Python-библиотеки (pyTelegramBotAPI, requests и т.д.) не используются — они несовместимы с MicroPython.

---

## 10. Installation & Setup

### Шаг 1. Установить MicroPython на Pico W

1. Скачать образ с [micropython.org/download/rp2-pico-w](https://micropython.org/download/rp2-pico-w/)
2. Зажать кнопку BOOTSEL на Pico W, подключить USB — устройство появится как накопитель RPI-RP2
3. Скопировать `.uf2` файл в корень накопителя
4. Pico W перезагрузится с MicroPython

### Шаг 2. Установить pibody

Через Thonny: Tools → Manage Packages → найти `pibody` → Install

Или через REPL:
```python
import mip
mip.install("pibody")
```

### Шаг 3. Настроить secrets.py

Скопировать файл и заполнить реальными данными:

```python
WIFI_SSID = "название_вашей_сети"
WIFI_PASSWORD = "пароль_от_wifi"
TG_TOKEN = "токен_от_BotFather"
```

Получить токен: написать `/newbot` в [@BotFather](https://t.me/BotFather).

### Шаг 4. Загрузить файлы на Pico W

Через Thonny (File → Save as → Raspberry Pi Pico) загрузить все файлы в корень файловой системы Pico:

```
/                  ← корень Pico W
├── main.py
├── bot.py
├── telegram.py
├── motor.py
├── dispencer.py
├── helper.py
└── secrets.py
```

### Шаг 5. Запуск

Нажать Run в Thonny или перезагрузить Pico W. В консоли должно появиться подключение к Wi-Fi. После подключения бот начнёт опрашивать Telegram API каждую секунду.

**Проверка:** написать `/start` боту в Telegram — устройство ответит приветствием.

### Шаг 6. Автозапуск

`main.py` на Pico W запускается автоматически при подаче питания — никаких дополнительных действий не нужно.

---

## 11. Telegram Commands

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие. Бот отвечает именем пользователя из Telegram-профиля |
| `/help` | Список доступных команд |
| `/btn` | Показывает inline-клавиатуру с тремя кнопками |
| `/unique_id` | Возвращает уникальный аппаратный ID устройства (`machine.unique_id()`) |

### Inline-кнопки (после `/btn`)

| Кнопка | Callback | Действие |
|--------|----------|----------|
| Уникальный ID | `get_unique_id` | Выполняет ту же логику, что `/unique_id` |
| Инфо | `get_info` | Возвращает username и ID бота через `getMe` |
| Anthropic | *(URL)* | Открывает `https://anthropic.com` в браузере |

### Текстовые сообщения

Любой текст, не являющийся командой, возвращается эхом: `Вы написали: <текст>`.

---

## 12. Motor Control Logic

### Как работает шаговый двигатель 28BYJ-48

28BYJ-48 — унипольный шаговый двигатель с 4 обмотками. ULN2003 управляет каждой обмоткой через транзисторные ключи. Pico W подаёт логические сигналы на IN1-IN4, ULN2003 коммутирует ток через обмотки.

### Full Step Mode (`FullStepMotor`)

Одновременно активны 2 обмотки. Последовательность из 4 состояний:

```
Состояние | IN1 | IN2 | IN3 | IN4 |
----------|-----|-----|-----|-----|
    0     |  1  |  1  |  0  |  0  |
    1     |  0  |  1  |  1  |  0  |
    2     |  0  |  0  |  1  |  1  |
    3     |  1  |  0  |  0  |  1  |
```

- 2048 шагов на полный оборот (с учётом редуктора 64:1)
- `stepms = 5` мс между шагами
- Больший крутящий момент

### Half Step Mode (`HalfStepMotor`)

Чередование 1 и 2 активных обмоток. 8 состояний:

```
Состояние | IN1 | IN2 | IN3 | IN4 |
----------|-----|-----|-----|-----|
    0     |  1  |  0  |  0  |  0  |
    1     |  1  |  1  |  0  |  0  |
    2     |  0  |  1  |  0  |  0  |
    3     |  0  |  1  |  1  |  0  |
    4     |  0  |  0  |  1  |  0  |
    5     |  0  |  0  |  1  |  1  |
    6     |  0  |  0  |  0  |  1  |
    7     |  1  |  0  |  0  |  1  |
```

- 4096 шагов на полный оборот
- `stepms = 3` мс между шагами
- Плавнее вращение, меньший момент

### Методы класса Motor

**`step(steps)`** — сделать N шагов. Знак определяет направление: `step(100)` вперёд, `step(-100)` назад. Внутри учитывает время выполнения одного шага и вычитает его из задержки:

```python
def step(self, steps):
    dir = 1 if steps >= 0 else -1
    for _ in range(abs(steps)):
        t_start = ticks_ms()
        self._step(dir)              # Подать сигналы на пины
        t_delta = ticks_diff(ticks_ms(), t_start)
        sleep_ms(self.stepms - t_delta)  # Компенсировать время выполнения
```

**`step_until(target)`** — вращать до позиции `target`. Автоматически определяет направление: идёт по короткому пути (если расстояние > половины оборота — меняет направление).

**`step_until_angle(angle)`** — вращать до угла в градусах. Конвертирует угол в шаги: `target = angle / 360 * maxpos`.

**`frompins(*pins)`** — classmethod, создать экземпляр с указанием номеров GPIO напрямую:
```python
m = FullStepMotor.frompins(0, 1, 2, 3, stepms=2)
```

### Dispencer

```python
class Dispencer(FullStepMotor):
    def __init__(self, stepms=2):
        self.motor = FullStepMotor.frompins(0, 1, 2, 3, stepms=stepms)

    def dispense(self):
        self.motor.step(50)      # +50 шагов — выдать порцию

    def dispense_reverse(self):
        self.motor.step(-50)     # -50 шагов — вернуть назад
```

50 шагов при `stepms=2` — примерно 100 мс движения. Угол поворота: `50 / 2048 * 360 ≈ 8.8°`.

---

## 13. Timing Logic

### Проблема: почему нельзя использовать `sleep()`

Основной цикл должен делать два дела одновременно: опрашивать Telegram и проверять кнопку. Если использовать `sleep(1)` перед polling — кнопка не реагирует 1 секунду. Если нажать кнопку, а в это время идёт HTTP-запрос к Telegram — кнопка пропускается.

MicroPython однопоточный (нет asyncio в базе). Решение — таймеры без блокировки.

### `is_interval_elapsed(id, interval)`

```python
is_interval_elapsed(0, 1000)  # Вернёт True раз в 1000мс
```

Проверяет, прошло ли `interval` мс с последнего `True`. Если да — обновляет timestamp и возвращает `True`. Иначе — сразу возвращает `False`. Цикл не блокируется.

Поддерживает несколько независимых таймеров через параметр `id`. У каждого `id` свой счётчик в параллельных списках `id_list_is_interval_elapsed` и `last_poll`.

### `true_for_interval(id, signal, interval)`

```python
true_for_interval(1, btn.value(), 1000)  # True пока кнопка нажата + ещё 1 сек
```

Решает проблему дребезга и коротких нажатий. При получении сигнала (`signal=True`) запоминает момент. Возвращает `True`, пока с этого момента не прошло `interval` мс. После истечения — `False`.

Применение: кнопка нажата на 50мс → LED горит 1000мс. Без этой функции LED мигал бы с частотой главного цикла.

### Взаимодействие в главном цикле

```
Итерация цикла (≈ несколько мс):
    ├─ is_interval_elapsed(0, 1000): False → skip polling
    ├─ true_for_interval(1, 0, 1000): False → led.off()
    ...
После 1000мс:
    ├─ is_interval_elapsed(0, 1000): True → bot.polling() (~200-500мс)
    └─ true_for_interval(1, btn, 1000): зависит от кнопки
```

---

## 14. Security Considerations

### secrets.py

Файл содержит три чувствительных значения: SSID, пароль Wi-Fi и токен Telegram-бота. В репозитории лежит шаблон с placeholder-значениями (`"your_wifi_ssid"` и т.д.) — реальные данные подставляются вручную на устройстве.

**Что нужно сделать:**

Добавить `secrets.py` в `.gitignore`:
```
secrets.py
```

Или хранить шаблон `secrets.example.py`, а реальный файл не коммитить.

### Telegram Token

Токен бота даёт полный контроль над ботом. Его компрометация означает, что кто угодно может отправлять команды от имени бота и управлять устройством. При утечке — немедленно отозвать через `/revoke` в @BotFather.

### Авторизация пользователей

В текущей реализации бот отвечает на команды от **любого пользователя Telegram**. Для защиты нужно добавить проверку `chat_id` или `user_id`:

```python
ALLOWED_USERS = [123456789]  # Ваш Telegram user_id

@bot.on_command("start")
def cmd_start(msg):
    if msg["from"]["id"] not in ALLOWED_USERS:
        bot.reply(msg, "Доступ запрещён.")
        return
    # ... логика
```

### Передача данных

Все запросы идут через HTTPS к `api.telegram.org`. MicroPython's `urequests` использует SSL. Трафик зашифрован.

---

## 15. Performance / Embedded Considerations

### Ограничения Pico W

| Ресурс | Значение |
|--------|----------|
| RAM | 264 КБ (доступно ≈ 180-200 КБ после старта MicroPython) |
| Flash | 2 МБ |
| CPU | Dual-core RP2040 @ 133 МГц (MicroPython использует 1 ядро) |
| Wi-Fi | CYW43439, 2.4 ГГц, нет 5 ГГц |

### Почему lightweight архитектура

**Нет asyncio** — базовый MicroPython на Pico W поддерживает `uasyncio`, но он добавляет сложность. Polling через `is_interval_elapsed` проще и предсказуемее для данного проекта.

**Нет потоков** — MicroPython поддерживает `_thread`, но синхронизация сложна. Однопоточный подход без sleep безопаснее.

**`micropython.const()`** — все константы (интервалы, ID таймеров) определены через `const()`. Это экономит RAM: значение встраивается в байткод.

**`resp.close()` после каждого запроса** — MicroPython не освобождает сокеты автоматически. Без явного закрытия после 4-5 запросов сокеты исчерпываются и устройство зависает.

**`ujson` вместо `json`** — встроенный модуль для MicroPython, работает быстрее стандартного.

**Параллельные списки вместо словарей в helper.py** — `list.index()` на 2-3 элементах быстрее, чем `dict` на MicroPython в данном случае.

---

## 16. Future Improvements

### MQTT вместо Telegram Polling

Polling создаёт задержку до 1 секунды и требует постоянного HTTPS-соединения. MQTT (например, через HiveMQ Cloud) даёт latency < 100 мс и меньше трафика. Pico W поддерживает MQTT через библиотеку `umqtt.simple`.

```python
# Концепт замены
from umqtt.simple import MQTTClient
client = MQTTClient("pico", "broker.hivemq.com")
client.connect()
client.subscribe(b"pico/commands")
```

### Web Dashboard

Node-RED или простой HTTP-сервер на Pico W (`picoweb`) для управления через браузер без Telegram.

### Сенсоры

Добавить датчики к существующей архитектуре: DHT22 (температура/влажность), HC-SR04 (расстояние), PIR (движение). Данные передавать в Telegram по команде или по событию.

### OTA-обновления

Скачивать обновлённый код с GitHub через Wi-Fi и перезаписывать файлы на Pico W без физического подключения к ПК. Реализуется через `urequests.get(raw_url)` + запись в файловую систему.

### Авторизация пользователей

Список разрешённых `user_id` в `secrets.py`. Проверка в каждом обработчике или на уровне `_dispatch` в `TeleBot`.

### Логирование

Запись событий в файл на Pico W (`log.txt`) с ротацией по размеру. Команда `/log` для получения последних записей через Telegram.

### Cloud Integration

Отправка данных в InfluxDB / Grafana Cloud через HTTP API для мониторинга состояния устройства и истории команд.

---

## 17. Заключение

Проект реализует полноценную систему удалённого управления микроконтроллером через Telegram, написанную полностью на MicroPython без сторонних зависимостей.

**Что реализовано:**

- Самодельный Telegram Bot API клиент (`telegram.py`) с поддержкой команд, callback-кнопок, inline-клавиатур — совместим с любым MicroPython-устройством с Wi-Fi
- Неблокирующая таймерная логика (`helper.py`) — позволяет параллельно обрабатывать polling и GPIO без потоков и asyncio
- Библиотека шагового двигателя (`motor.py`) с поддержкой full step и half step, позиционированием по шагам и углу
- Высокоуровневый класс дозатора (`dispencer.py`) поверх мотора

**Что демонстрирует проект:**

Архитектурный подход: как строить embedded IoT-систему с внешним интерфейсом управления в условиях жёстких ограничений по RAM и отсутствия полноценной ОС. Разделение на слои (транспорт → диспетчер → бизнес-логика → железо) даёт возможность менять любой слой независимо.

**Где можно использовать:**

Автоматические дозаторы, кормушки для животных, управление жалюзи/замками, контроль доступа, удалённый мониторинг и управление любым электромеханическим устройством через Telegram.

---

*Документация написана на основе реального кода репозитория `battalovmeyrkhan/documentation`, ветка `main`, папка `raspberry`.*
