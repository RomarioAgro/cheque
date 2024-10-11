import re


def preparation_km(in_km: str) -> str:
    """
    функция подготовки кода маркировки к отправке в честный знак
    вставляем символы разрыва перед 91 и 92
    :param in_km: str
    :return: str
    """
    pattern = r'91\S+?92'
    s_break = '\x1D'
    list_break_pattern = re.findall(pattern, in_km[30:])
    if len(list_break_pattern) > 0:
        repl = (s_break + list_break_pattern[0]).replace('92', s_break + '92')
        out_km = in_km[:30] + re.sub(pattern, repl, in_km[30:])
    else:
        out_km = in_km[:]
    return out_km


def main():
    km = 'oolololo'
    preparation_km(in_km=km)


if __name__ == '__main__':
    main()