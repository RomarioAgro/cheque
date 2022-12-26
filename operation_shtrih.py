import logging
import os
import socket
import getpass
import json
from sys import argv, exit
import datetime
os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad
from shtrih_OOP import Shtrih


CUTTER = '~S'


current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logging.basicConfig(
    filename='D:\\files\\' + argv[2] + "_" + current_time + '.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt

def save_about_fr(i_list=None):
    if i_list == None:
        exit(0)
    f_name = socket.gethostname() + '_' + getpass.getuser() + '_' + i_list[0] + '.txt'
    f_path = 'e:\\inbox\\attention\\'
    with open(f_path + f_name, 'w') as o_file:
        for count, elem in enumerate(i_list):
            if count > 0:
                o_file.write(elem + '\n')


def main():
    comp_rec = read_composition_receipt(argv[1] + '\\' + argv[2] + '.json')
    logging.debug(comp_rec['operationtype'])
    i_shtrih = Shtrih()
    if comp_rec['operationtype'] == 'open_box':
        i_shtrih.open_box()
        exit(0)
    # печать отчета СБП
    if comp_rec.get('SBP', 0) == 1:
        i_sbp = SBP()
        str_registry_SBP = i_sbp.make_registry_for_print_on_fr(i_sbp.registry())
        i_shtrih.print_pinpad(str_registry_SBP, CUTTER)
    # печать отчета эквайринга
    if comp_rec.get('PinPad', 0) == 1:
        sber_pinpad = PinPad()
        sber_pinpad.pinpad_operation(operation_name=comp_rec['operationtype'], oper_sum=comp_rec['sum-cashless'])
        sber_pinpad.text = sber_pinpad.text.replace(CUTTER, '')
        i_shtrih.print_pinpad(sber_pinpad.text, CUTTER)
    # печать отчета штрих
    if comp_rec['operationtype'] == 'x_otchet':
        i_shtrih.x_otchet()
    if comp_rec['operationtype'] == 'z_otchet':
        i_shtrih.z_otchet()
    logging.debug(i_shtrih.error_analysis_soft())
    list_aboutfr = i_shtrih.about_me()
    save_about_fr(list_aboutfr)



if __name__ == '__main__':
    main()
