import logging
import os
import win32com.client
import datetime
from sys import exit
os.chdir('d:\\kassa\\script_py\\shtrih\\')

DICT_OPERATION_CHECK = {'sale': 4000,
                        'return_sale': 4002,
                        'correct_sale': 128,
                        'correct_return_sale': 130,
                        'x_otchet': 7004,
                        'full_otchet': 6002,
                        'z_otchet': 6000}

CUTTER = '~S'



class PinPad(object):
    """
    класс нашего терминала эквайринга
    operation: str наша операция, потом переведем ее в код операции
    oper_sum: int сумма операции, у отчетов это 0
    error: int код ошибки пинпада
    text: текст операции который возвращает пинпад
    """
    def __init__(self):
        self.operation_code = 7004
        self.operation_name = 'x_otchet'
        self.operation_sum = 0
        self.error = 0
        self.text = None
        self.drv_pp = win32com.client.Dispatch('SBRFSRV.Server')

    def pinpad_operation(self, operation_name: str = 'x_otchet', oper_sum: int = 0):
        """
        метод обращения к терминалу сбербанка
        для операций
        4000 оплата
        4002 возврат
        6000 сверка итогов - аналог Z отчета
        6001 ПОДТВЕРДИТЬ ОПЕРАЦИЮ
        6002 список всех операций за смену терминала
        6003 ПЕРЕВОД ОПЕРАЦИИ В НЕПОДТВЕРЖДЕННОЕ СОСТОЯНИЕ
        6004 ОТМЕНА ОПЕРАЦИИ
        7004 аналог Х отчета из фискального регистратора
        """
        self.operation_code = DICT_OPERATION_CHECK.get(operation_name, 7004)
        self.operation_name = operation_name
        self.operation_sum = oper_sum * 100
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        # log_file = 'd:\\files\\pinpad_' + self.operation_name + ' ' + current_time + ".log"
        # logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)
        logging.debug(current_time + ' start operation ' + self.operation_name)
        # pinpad = win32com.client.Dispatch('SBRFSRV.Server')
        self.drv_pp.Clear()
        self.drv_pp.SParam("Amount", self.operation_sum)
        self.error = self.drv_pp.NFun(self.operation_code)
        self.text = self.drv_pp.GParamString("Cheque1251")
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' end operation ' + self.operation_name + ' error ' + str(self.error) + ' \n' + self.text)


def main():
    comp_rec = dict()
    comp_rec['sum-cashless'] = 0
    comp_rec['operationtype'] = 'x_otchet'
    i_pinpad = PinPad()
    i_pinpad.pinpad_operation(operation_name=comp_rec['operationtype'], oper_sum=comp_rec['sum-cashless'])
    print(i_pinpad.text)
    exit(i_pinpad.error)

if __name__ == '__main__':
    main()