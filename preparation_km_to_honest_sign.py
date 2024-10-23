import re


def preparation_km(in_km: str) -> str:
    """
    функция подготовки кода маркировки к отправке в честный знак
    вставляем символы разрыва перед 91 и 92
    у воды только символ 93, разрыв надо перед ним
    :param in_km: str
    :return: str
    """
    pattern = r'91\S+?92'
    pattern_water = r'93\S+?'
    s_break = '\x1D'
    strt_symbol = 31
    fnsh_symbol = 39
    match = re.search(pattern, in_km[strt_symbol:fnsh_symbol])
    match_w = re.search(pattern_water, in_km[strt_symbol:fnsh_symbol])
    if match:
        out_km = in_km[:strt_symbol + match.start()] + \
                 s_break + match.group()[:-2] + s_break + \
                 match.group()[-2:] + in_km[strt_symbol + match.end():]
    elif match_w:
        out_km = in_km[:strt_symbol + match_w.start()] + \
                 s_break + match_w.group() + in_km[strt_symbol + match_w.end():]
    else:
        out_km = in_km[:]
    return out_km


def main():
    km_list = ['0104610293561292215Oa3NcYIG,-c>91EE1092p91P92bWgYS4Xcjcr+OWglRNO7lp/W0aFgCUQM9Ay14=',
               "0104650259150016215L='bgjU-kxkS93/x8C",
               "0104620015810126215nUWImNW+c!dC93nZiT"]
    for km in km_list:
        aa = preparation_km(in_km=km)
        print(aa)


if __name__ == '__main__':
    main()