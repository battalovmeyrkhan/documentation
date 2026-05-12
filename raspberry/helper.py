from time import ticks_ms, ticks_diff

id_list_is_interval_elapsed = []          # Хранение списка id                           // Для is_interval_elapsed
last_poll = []                            # Хранение последнего времени отправки сигнала // Для is_interval_elapsed

id_list_true_for_interval = []            # Хранение списка id                           // Для true_for_interval
last_signal_time = []                     # Хранение последнего времени прихода сигнала  // Для true_for_interval
active = []                               # Хранение активности                          // Для true_for_interval

def is_interval_elapsed(id: int, interval: int):
    global last_poll, id_list_is_interval_elapsed

    # Если это первый запуск, то инициализируем массив
    if id not in id_list_is_interval_elapsed:
        id_list_is_interval_elapsed.append(id)
        last_poll.append(0)
    index = id_list_is_interval_elapsed.index(id)

    # Если прошло больше времени, чем интервал, то возвращаем True
    if ticks_diff(ticks_ms(), last_poll[index]) > interval:
        last_poll[index] = ticks_ms()
        return True
    return False


def true_for_interval(id: int, signal: bool, interval: int):
    global last_signal_time, active, id_list_true_for_interval

    now = ticks_ms()

    if id not in id_list_true_for_interval:
        id_list_true_for_interval.append(id)
        last_signal_time.append(0)
        active.append(False)
    index = id_list_true_for_interval.index(id)

    # Если пришел сигнал — запускаем таймер
    if signal:
        last_signal_time[index] = now
        active[index] = True

    # Если таймер активен и время еще не вышло
    if active[index] and ticks_diff(now, last_signal_time[index]) <= interval:
        return True

    # Если время вышло
    active[index] = False
    return False
