"""
telebot.py — обёртка Telegram Bot API для MicroPython
Совместима с ESP32/ESP8266/RP2040 и другими MicroPython-устройствами.
"""

import urequests
import ujson
import utime


class TeleBot:
    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, timeout: int = 10):
        """
        :param token: токен бота от @BotFather
        :param timeout: таймаут HTTP-запросов в секундах
        """
        self.token = token
        self.timeout = timeout
        self._offset = 0
        self._handlers = {}          # {команда: функция}
        self._message_handler = None # обработчик всех сообщений
        self._error_handler = None   # обработчик ошибок

    # ──────────────────────────────────────────────
    # Низкоуровневый запрос к API
    # ──────────────────────────────────────────────

    def _request(self, method: str, params: dict = None) -> dict:
        url = self.BASE_URL.format(token=self.token, method=method)
        headers = {"Content-Type": "application/json"}
        body = ujson.dumps(params) if params else "{}"
        # urequests на MicroPython требует bytes, иначе тело может уйти пустым
        if isinstance(body, str):
            body = body.encode("utf-8")

        try:
            resp = urequests.post(url, data=body, headers=headers)
            result = ujson.loads(resp.text)
            resp.close()
        except Exception as e:
            self._on_error(e)
            return {}

        if not result.get("ok"):
            err = result.get("description", "Unknown API error")
            self._on_error(RuntimeError(err))
            return {}

        return result.get("result", {})

    # ──────────────────────────────────────────────
    # Методы API
    # ──────────────────────────────────────────────

    def get_me(self) -> dict:
        """Информация о боте."""
        return self._request("getMe")

    def send_message(self, chat_id, text: str,
                     parse_mode: str = None,
                     reply_markup: dict = None) -> dict:
        """
        Отправить текстовое сообщение.
        :param parse_mode: "HTML" | "Markdown" | None
        :param reply_markup: InlineKeyboardMarkup / ReplyKeyboardMarkup / ...
        """
        params = {"chat_id": chat_id, "text": text}
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_markup:
            params["reply_markup"] = reply_markup
        print("[sendMessage] chat_id=" + str(chat_id) + " type=" + str(type(chat_id)))
        return self._request("sendMessage", params)

    def get_chat_id(self, obj: dict):
        """
        Универсально извлечь chat_id из любого объекта Telegram:
        message, callback_query, edited_message и т.д.
        Печатает структуру если chat_id не найден.
        """
        # message / edited_message
        if "chat" in obj:
            return obj["chat"]["id"]
        # callback_query -> message -> chat
        if "message" in obj:
            msg = obj["message"]
            if "chat" in msg:
                return msg["chat"]["id"]
        # callback_query -> from (личный чат = user_id == chat_id)
        if "from" in obj:
            return obj["from"]["id"]
        # Ничего не нашли — напечатаем структуру для отладки
        print("[TeleBot] Cannot find chat_id in object:")
        print(ujson.dumps(obj))
        return None

    def reply(self, obj: dict, text: str, **kwargs) -> dict:
        """
        Ответить на message или callback_query.
        chat_id определяется автоматически через get_chat_id().
        """
        chat_id = self.get_chat_id(obj)
        if chat_id is None:
            print("[TeleBot] reply() skipped: no chat_id")
            return {}
        return self.send_message(chat_id=chat_id, text=text, **kwargs)

    def forward_message(self, chat_id, from_chat_id, message_id: int) -> dict:
        return self._request("forwardMessage", {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        })

    def delete_message(self, chat_id, message_id: int) -> dict:
        return self._request("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
        })

    def send_chat_action(self, chat_id, action: str) -> dict:
        """
        Показать индикатор действия.
        action: "typing" | "upload_photo" | "record_video" | ...
        """
        return self._request("sendChatAction", {
            "chat_id": chat_id,
            "action": action,
        })

    def answer_callback_query(self, callback_query_id: str,
                               text: str = None, show_alert: bool = False) -> dict:
        params = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            params["text"] = text
        return self._request("answerCallbackQuery", params)

    def get_updates(self, limit: int = 10, allowed_updates: list = None) -> list:
        params = {
            "offset": self._offset,
            "limit": limit,
            "timeout": self.timeout,
        }
        if allowed_updates:
            params["allowed_updates"] = allowed_updates
        updates = self._request("getUpdates", params)
        return updates if isinstance(updates, list) else []

    # ──────────────────────────────────────────────
    # Построители клавиатур
    # ──────────────────────────────────────────────

    @staticmethod
    def inline_keyboard(buttons: list) -> dict:
        """
        Создать InlineKeyboardMarkup.

        Пример:
            bot.inline_keyboard([
                [("Кнопка 1", "cb_1"), ("Кнопка 2", "cb_2")],
                [("Ссылка", None, "https://example.com")],
            ])

        Каждая кнопка — кортеж:
            (текст, callback_data)          — callback-кнопка
            (текст, None, url)              — url-кнопка
        """
        keyboard = []
        for row in buttons:
            kb_row = []
            for btn in row:
                text = btn[0]
                if len(btn) == 3 and btn[2]:          # url
                    kb_row.append({"text": text, "url": btn[2]})
                else:                                   # callback
                    kb_row.append({"text": text, "callback_data": btn[1]})
            keyboard.append(kb_row)
        return {"inline_keyboard": keyboard}

    @staticmethod
    def reply_keyboard(buttons: list, resize: bool = True,
                       one_time: bool = False) -> dict:
        """
        Создать ReplyKeyboardMarkup.

        Пример:
            bot.reply_keyboard([["Да", "Нет"], ["Отмена"]])
        """
        keyboard = [[{"text": b} for b in row] for row in buttons]
        return {
            "keyboard": keyboard,
            "resize_keyboard": resize,
            "one_time_keyboard": one_time,
        }

    @staticmethod
    def remove_keyboard() -> dict:
        return {"remove_keyboard": True}

    # ──────────────────────────────────────────────
    # Регистрация обработчиков
    # ──────────────────────────────────────────────

    def on_command(self, command: str):
        """
        Декоратор: обработчик команды /command.

        @bot.on_command("start")
        def start(message):
            bot.reply(message, "Привет!")
        """
        def decorator(func):
            self._handlers["cmd:" + command.lstrip("/")] = func
            return func
        return decorator

    def on_callback(self, data: str):
        """
        Декоратор: обработчик нажатия inline-кнопки по callback_data.

        @bot.on_callback("get_temp")
        def cb_temp(cq):
            bot.answer_callback_query(cq["id"])
            bot.reply(cq, "Температура: 42°C")
        """
        def decorator(func):
            self._handlers["cb:" + data] = func
            return func
        return decorator

    def on_message(self, func):
        """
        Декоратор: обработчик всех текстовых сообщений
        (вызывается, если команда не найдена).
        """
        self._message_handler = func
        return func

    def on_error(self, func):
        """Декоратор: обработчик ошибок."""
        self._error_handler = func
        return func

    # ──────────────────────────────────────────────
    # Внутренняя диспетчеризация
    # ──────────────────────────────────────────────

    def _on_error(self, exc):
        if self._error_handler:
            try:
                self._error_handler(exc)
            except Exception:
                pass
        else:
            print("[TeleBot ERROR]", exc)

    def _dispatch(self, update: dict):
        # Callback query
        if "callback_query" in update:
            cq = update["callback_query"]
            data = cq.get("data", "")
            handler = self._handlers.get("cb:" + data)
            if handler:
                handler(cq)
            else:
                # Нет обработчика — просто закрываем спиннер
                self.answer_callback_query(cq["id"])
            return

        # Обычное сообщение
        message = update.get("message")
        if not message:
            return

        text = message.get("text", "")

        # Команда?
        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0][1:].split("@")[0]   # /start@mybot → start
            handler = self._handlers.get("cmd:" + cmd)
            if handler:
                handler(message)
                return

        # Общий обработчик
        if self._message_handler:
            self._message_handler(message)

    # ──────────────────────────────────────────────
    # Главный цикл
    # ──────────────────────────────────────────────

    def polling(self):
        """
        Запустить опрос на наличие новых сообщений.
        """
        try:
            updates = self.get_updates()
            for update in updates:
                self._offset = update["update_id"] + 1
                self._dispatch(update)
        except Exception as e:
            self._on_error(e)
