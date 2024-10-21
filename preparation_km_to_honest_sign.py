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
    strt_symbol = 30
    fnsh_symbol = 40
    list_break_pattern = re.findall(pattern, in_km[strt_symbol:fnsh_symbol])
    if len(list_break_pattern) > 0:
        repl = (s_break + list_break_pattern[0]).replace('92', s_break + '92')
        out_km = in_km[:strt_symbol] + re.sub(pattern, repl, in_km[strt_symbol:fnsh_symbol]) + in_km[fnsh_symbol:]
    else:
        out_km = in_km[:]
    return out_km


def main():
    km = '0104610293561292215Oa3NcYIG,-c>91EE1092p91P92bWgYS4Xcjcr+OWglRNO7lp/W0aFgCUQM9Ay14='
    preparation_km(in_km=km)


if __name__ == '__main__':
    main()