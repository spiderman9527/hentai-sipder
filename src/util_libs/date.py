from datetime import datetime


def now_time():
    now = datetime.now()

    return "{}/{}/{} {}:{}:{}".format(
        now.year,
        fillZero(now.month),
        fillZero(now.day),
        fillZero(now.hour),
        fillZero(now.minute),
        fillZero(now.second)
    )


def fillZero(num: int) -> str:
    return num if num >= 10 else "0{}".format(num)


def datetime_title(title: str):
    return "[{}][{}]：".format(now_time(), title)
