import re
import json
from typing import List


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r', encoding='utf-8') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt

def make_qr(list_km: List[str]):
    # qr = "0104620046412948215YOpNN_oEIAiZ91EE0792iMCZl3lrWPDGDGl1bv9A4qIUoVWStWbg+SCJxjgWUCY="
    pattern =r'91\S+92'
    for qr in list_km:
        a = re.findall(pattern, qr[30:])
        repl = ('\x1D' + a[0]).replace('92', '\x1D' + '92')
        km_qr = qr[:30] + re.sub(pattern, repl, qr[30:])
        print(qr)
        print(km_qr)

file_name = '112233.json'
composition_receipt = read_composition_receipt(file_name)
make_qr(composition_receipt['km'])
