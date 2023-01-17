import logging
import win32com.client
import json
from sys import argv
from typing import Tuple, List
import ctypes
import re
import os
import datetime

os.chdir('d:\\kassa\\script_py\\shtrih\\')

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130,
                        'x_otchet': 7004,
                        'open_box': 6002,
                        'z_otchet': 6000}

CUTTER = '~S'

current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')

logging.basicConfig(
    filename=argv[1] + '\\' + argv[2] + "_" + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logging.debug('start')


class Shtrih(object):
    """
    класс нашего кассового аппарата
    """

    def __init__(self, i_path: str = 'd:\\files', i_file_name: str = 'x'):
        """
        конструктор класса, инициализируется
        :param i_path: str путь где лежит json с параметрами
        :param i_file_name: str имя json с параметрами
        prn - объект драйвера штриха
 
        """
        file_json_name = i_path + '\\' + i_file_name + '.json'
        if os.path.exists(file_json_name):
            with open(file_json_name, 'r') as json_file:
                self.cash_receipt = json.load(json_file)
        else:
            self.cash_receipt = None
        self.drv = win32com.client.Dispatch('Addin.DRvFR')
        logging.debug('создали объект чека' + str(self.cash_receipt))

    def shtrih_operation_fn(self):
        """
        метод печати позиций чека

        """
        # уточняем по какому ФФД работает касса 1.05 или 1.2
        error_code = 1000
        error_code_desc = 'ошибка начала'
        for item in self.cash_receipt['items']:
            if item['quantity'] != 0:
                self.print_str(i_str='_' * 30, i_font=2)
                if (DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype']) == 0 or
                        DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype']) == 128):
                    self.drv.CheckType = 1
                else:
                    self.drv.CheckType = 2
                paymentitemsign = item['paymentitemsign']
                if self.drv.WorkModeEx == 0 and paymentitemsign == 33:
                    paymentitemsign = 1
                self.drv.PaymentItemSign = paymentitemsign
                self.drv.Quantity = item['quantity']
                self.drv.Price = item['price']
                self.drv.Summ1 = item['quantity'] * item['price']
                self.drv.Summ1Enabled = True
                self.drv.Tax1 = item['taxtype']
                self.drv.Department = 1
                self.drv.PaymentTypeSign = item['paymenttypesign']
                # если строка начинается символами //, то она передаётся на сервер ОФД но не печатается на
                # кассе.
                self.drv.StringForPrinting = item['name']
                self.drv.FNOperation()
                error_code = self.drv.ResultCode
                error_code_desc = self.drv.ResultCodeDescription
                if len(item['qr']) > 30:
                    self.drv.DivisionalQuantity = False
                    self.drv.BarCode = preparation_km(item['qr'])
                    self.drv.FNSendItemBarcode()
                self.drv.WaitForPrinting()
                if item.get('fullprice', None) is not None:
                    self.print_str(i_str='Первоначальная розничная цена=' + str(item.get('fullprice', '0')), i_font=1)
                if item.get('discount', None) is not None:
                    self.print_str(i_str='Скидка = ' + str(item.get('discount', '0')), i_font=1)
                if item.get('bonuswritedown', None) is not None:
                    self.print_str(i_str='Бонусов списано = ' + str(item.get('bonuswritedown', '0')), i_font=1)
                if item.get('bonusaccrual', None) is not None:
                    self.print_str(i_str='Бонусов начислено = ' + str(item.get('bonusaccrual', '0')), i_font=1)
        logging.debug('FNOperation= {0}, описание ошибки: {1}'.format(error_code, error_code_desc))
        return error_code

    def shtrih_close_check(self) -> Tuple:
        """
        функция печати конца чека, закрытие и все такое
        :param comp_rec:
        :return: int, str код ошибки, описание ошибки
        """
        self.drv.Summ1 = self.cash_receipt['sum-cash']
        self.drv.Summ2 = self.cash_receipt['sum-cashless']
        self.drv.Summ3 = self.cash_receipt['summ3']
        self.drv.Summ4 = self.cash_receipt['summ4']
        self.drv.Summ14 = self.cash_receipt['summ14']
        self.drv.Summ15 = self.cash_receipt['summ15']
        self.drv.Summ16 = self.cash_receipt['summ16']
        self.drv.TaxType = self.cash_receipt['tax-type']
        self.drv.StringForPrinting = 'Итоговая скидка = ' + str(self.cash_receipt.get('total-discount', '0'))
        self.send_tag_1021_1203()
        list_correction = [128, 130]
        if DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype']) in list_correction:
            self.send_tag_correction()
        self.drv.FNCloseCheckEx()
        self.drv.WaitForPrinting()
        error_code = self.drv.ResultCode
        error_descr = self.drv.ResultCodeDescription
        logging.debug(str(error_code) + '-' + error_descr)
        fd = self.drv.DocumentNumber
        fp = self.drv.FiscalSign
        fp_str = self.drv.FiscalSignAsString
        logging.debug('ФД: {0}, ФП: {1},  ФП строка: {2}'.format(fd, fp, fp_str))
        return error_code, error_descr

    def send_tag_correction(self):
        """
        метод отправки тегов чека коррекции
        самостоятельно коррекция или нет
        номер неверного ФП если есть
        """
        # это отправка не верного ФП
        self.drv.TagNumber = 1192
        self.drv.TagType = 7
        self.drv.TagValueStr = self.cash_receipt.get('wrong_FP', '')
        self.drv.FNSendTag()
        # тип коррекции самостоятельно - 0
        self.drv.TagNumber = 1173
        self.drv.TagType = 0
        self.drv.TagValueInt = self.cash_receipt.get('type_correction', 0)
        self.drv.FNSendTag()
        if self.cash_receipt.get('type_correction', 0) != 0:
            self.drv.TagNumber = 1179
            self.drv.TagType = 7
            self.drv.TagValueStr = self.cash_receipt.get('footing_correction', 0)
            self.drv.FNSendTag()

        # отправка не даты коррекции, а дата когда не был пробит чек
        #или когда была ошибочная продажа
        self.drv.TagNumber = 1178
        self.drv.TagType = 6
        corr_date = self.cash_receipt.get('correction_date', '')
        if corr_date == '':
            corr_date = datetime.datetime.today().strftime('%d.%m.%y')
        self.drv.TagValueDateTime = datetime.datetime.strptime(corr_date, '%d.%m.%y').strftime('%Y.%m.%d')
        self.drv.FNSendTag()


    def send_tag_1021_1203(self) -> None:
        """
        функция отправки тэгов 1021 и 1203
        ФИО кассира и ИНН кассира
        :param comp_rec: dict словарь нашего чека
        :return:
        """
        self.drv.TagNumber = 1021
        self.drv.TagType = 7
        self.drv.TagValueStr = self.cash_receipt['tag1021']
        self.drv.FNSendTag()
        self.drv.TagNumber = 1203
        self.drv.TagType = 7
        self.drv.TagValueStr = self.cash_receipt['tag1203']
        self.drv.FNSendTag()

    def get_ecr_status(self):
        """
        функция запрoса режима кассы
        :return: int, str
        """
        self.drv.Password = 30
        self.drv.GetECRStatus()
        return self.drv.ECRMode, self.drv.ECRModeDescription

    def preparation_for_work(self):
        """
        функция подготовки кассы к работе
        проверка связи, состояния, если состояние
        не рабочее, то попытки его исправить

        """
        # проверка связи с кассой

        logging.debug('создали объект печати чека')
        dict_of_command_ecr_mode = {
            4: self.open_session,
            3: self.z_otchet,
            8: self.error_analysis_hard
        }
        connect_error, connect_error_description = self.check_connect_fr()
        logging.debug('проверка связи с кассой {0} - {1}'.format(connect_error, connect_error_description))
        if connect_error != 0:
            Mbox('ошибка', 'ошибка: {}'.format(connect_error_description), 4096 + 16)
            exit(connect_error)
        # проверка режима работы кассы
        # режим 2 - Открытая смена, 24 часа не кончились
        while True:
            ecr_mode, ecr_mode_description = self.get_ecr_status()
            logging.debug('проверка режима кассы {0} - {1}'.format(ecr_mode, ecr_mode_description))
            if ecr_mode == 2:
                break
            else:
                logging.debug('режим не рабочий {0}, запускаем {1}'.format(ecr_mode, dict_of_command_ecr_mode))
                dict_of_command_ecr_mode.get(ecr_mode, self.i_dont_know)()

        # внесение наличных в кассу, если это у нас первый возврат в смене
        if self.cash_receipt.get('cashincome', 0) > 0:
            logging.debug('внесение наличных в кассу, если это у нас первый возврат в смене')
            self.shtrih_operation_cashincime()
            logging.debug('cashincome')

    def open_box(self):
        self.drv.OpenDrawer()

    def x_otchet(self):
        self.drv.Password = 30
        self.drv.PrintReportWithoutCleaning()
        self.drv.WaitForPrinting()

    def z_otchet(self):
        """
        метод закрытия смены
        """
        self.drv.Password = 30
        self.drv.FNBeginCloseSession()
        self.send_tag_1021_1203()
        self.drv.FNCloseSession()
        self.drv.WaitForPrinting()
        return self.drv.ECRMode, self.drv.ECRModeDescription

    def shtrih_operation_cashincime(self):
        """
        функция внесения наличных в кассу
        на случай 1-го возврата в смене
        """
        self.drv.Summ1 = self.cash_receipt.get('cashincome', 0)
        self.drv.CashIncome()

    def sendcustomeremail(self):
        """
        функция отправки чека по почте или смс
        ОФД сам решает
        """
        self.drv.Password = 1
        self.drv.CustomerEmail = self.cash_receipt["email"]
        self.drv.FNSendCustomerEmail()
        return self.drv.ResultCode

    def shtrih_operation_attic(self):
        """
        функция оформления начала чека,
        задаем тип чека,
        открываем сам документ в объекте
        0 ЭТО ПРОДАЖА
        2 ЭТО ВОЗВРАТ
        128 ЧЕК КОРРЕКЦИИ ПРОДАЖА
        130 ЭТО ЧЕК КОРРЕКЦИИ ВОЗВРАТ'
        """
        self.drv.CheckType = DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype'])
        self.drv.Password = 1
        self.drv.OpenCheck()
        self.drv.UseReceiptRibbon = "TRUE"

    def print_QR(self, item: str = 'nothing'):
        """
        метод печати QRкода на чеке, вызов будет
        после
        """
        self.drv.Password = 30
        self.drv.BarCode = item
        self.drv.BarcodeType = 3
        self.drv.BarcodeStartBlockNumber = 0
        self.drv.BarcodeParameter1 = 0
        self.drv.BarcodeParameter3 = 6
        self.drv.BarcodeParameter5 = 3
        self.drv.LoadAndPrint2DBarcode()
        self.drv.WaitForPrinting()
        self.drv.StringQuantity = 10
        self.drv.FeedDocument()
        self.drv.CutType = 2
        self.drv.CutCheck()

    def print_pinpad(self, i_str: str, sum_operation: str):
        """
        функция печати ответа от пинпада сбербанка
        :param i_str: str строка печати
        sum_operation: str сумма операции
        count_cutter: int количество команд отрезки,
        отрезать надо только на 1
        """
        i_text = i_str.split('\n')
        count_cutter = 0
        for key, i_line in enumerate(i_text):
            if key != 3:
                line = i_line.strip('\r')
                if (line.find(CUTTER) != -1 and
                        count_cutter == 0):
                    count_cutter += 1
                    self.drv.StringQuantity = 7
                    self.drv.FeedDocument()
                    self.drv.CutType = 2
                    self.drv.CutCheck()
                else:
                    if line.find(CUTTER) != -1:
                        # сам символ отрезки печатать не надо
                        pass
                    else:
                        if line.find(sum_operation) != -1:
                            if line.strip().startswith(sum_operation) is True:
                                self.print_str(i_str=line, i_font=2)
                            else:
                                self.print_str(i_str='Сумма (Руб):', i_font=5)
                                self.print_str(i_str=sum_operation, i_font=2)

                        else:
                            self.print_str(i_str=line, i_font=5)

    def print_advertisement(self, list_advertisement):
        """
        функция печати рекламного текста в начале чека
        """
        for item in list_advertisement:
            self.print_str(i_str=item[0], i_font=item[1])

    def print_barcode(self):
        """
        функция печати штрихкода на чеке,
        обычно это для рекламы
        """
        for item in self.cash_receipt['barcode']:
            self.drv.BarCode = item
            self.drv.PrintBarCode()
            self.drv.WaitForPrinting()
            self.drv.StringQuantity = 2
            self.drv.FeedDocument()

    def get_info_about_FR(self):
        """
        функция запроса итогов фискализации
        она ничего не возвращиет, но послее нее у объекта PRN
        появляются дополнительные свойства
        """
        self.drv.Password = 30
        self.drv.Connect()
        self.drv.FNGetFiscalizationResult()


    def check_connect_fr(self):
        """
        функция проверки связи с фискальмым регистратором
        """
        self.drv.Password = 30
        self.drv.Connect()
        return self.drv.ResultCode, self.drv.ResultCodeDescription

    def open_session(self):
        """
        функция открытия смены на кассе
        :param comp_rec: dict
        """
        self.drv.Password = 30
        self.drv.FnBeginOpenSession()
        self.drv.WaitForPrinting()
        self.send_tag_1021_1203()
        self.drv.FnOpenSession()
        self.drv.WaitForPrinting()
        return self.drv.ECRMode, self.drv.ECRModeDescription

    def kill_document(self):
        """
        функция прибития застрявшего документа
        :param comp_rec:  dict
        """
        self.drv.Password = 30
        self.drv.SysAdminCancelCheck()

    def continuation_printing(self):
        self.drv.Password = 30
        self.drv.ContinuePrint()
        # self.drv.WaitForPrinting()
        return self.drv.ECRMode, self.drv.ECRModeDescription, self.drv.ECRAdvancedMode, self.drv.ECRAdvancedModeDescription,

    def check_km(self):
        """
        функция проверки кодов маркировки в честном знаке
        :param comp_rec: dict словарь с нашим чеком
        PRN.ItemStatus = 1 при продаже
        PRN.ItemStatus = 3 при возврате
        """
        for qr in self.cash_receipt['km']:
            """
            поиск шиблона между 91 и 92 с помощью регулярного выражения
            и замена потом этого шаблона на него же но с символами разрыва
            перед 91 и 92
            """
            self.drv.BarCode = preparation_km(qr)
            if (DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype']) == 0 or
                    DICT_OPERATION_CHECK.get(self.cash_receipt['operationtype']) == 128):
                self.drv.ItemStatus = 1
            else:
                self.drv.ItemStatus = 3
            self.drv.CheckItemMode = 0
            self.drv.DivisionalQuantity = False
            self.drv.FNCheckItemBarcode2()
            if self.drv.KMServerCheckingStatus != 15:
                self.drv.FNAcceptMarkingCode()

    def about_me(self) -> List:
        """
        метод опроса кассы на предмет всяких данных
        потом сохраняем в текстовый файл
        :return:
        """
        list_about_fr = []
        self.drv.FNGetExpirationTime()
        if self.drv.ResultCode != 0:
            return list_about_fr
        self.drv.ReadSerialNumber()
        v_date = datetime.datetime.strftime(self.drv.Date, "%d.%m.%Y")
        list_about_fr.append(v_date + '_' + self.drv.SerialNumber)
        list_about_fr.append('SROK ' + v_date)
        list_about_fr.append('ZN ' + self.drv.SerialNumber)
        self.drv.FNGetFiscalizationResult()
        list_about_fr.append('RN ' + self.drv.KKTRegistrationNumber)
        self.drv.FNGetSerial()
        list_about_fr.append('ZN ' + self.drv.SerialNumber)
        self.drv.FNGetInfoExchangeStatus()
        if self.drv.MessageCount > 0:
            list_about_fr.append('ALYARM NOTSEND ' + str(self.drv.MessageCount))
            list_about_fr.append('DATENOTSEND ' + datetime.datetime.strftime(self.drv.Date, "%d.%m.%Y"))
        self.drv.ReadFeatureLicenses()
        if self.drv.License == '':
            list_about_fr.append('LIC NONE')
        else:
            list_about_fr.append('LIC ' + self.drv.License)
        self.drv.FNGetFiscalizationResult()
        if self.drv.WorkModeEx == 16:
            list_about_fr.append('FFD 1.2')
        else:
            list_about_fr.append('FFD 1.05')
        self.drv.TableNumber = 18
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 10
        self.drv.ReadTable()
        list_about_fr.append('OFD ' + self.drv.ValueOfFieldString)
        self.drv.TableNumber = 18
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 14
        self.drv.ReadTable()
        list_about_fr.append('MESTO ' + self.drv.ValueOfFieldString)
        list_about_fr.append('INN ' + self.drv.INN)
        self.drv.TableNumber = 18
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 7
        self.drv.ReadTable()
        list_about_fr.append('ORG ' + self.drv.ValueOfFieldString)
        self.drv.TableNumber = 18
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 9
        self.drv.ReadTable()
        list_about_fr.append('ADR ' + self.drv.ValueOfFieldString)
        self.drv.GetECRStatus()
        list_about_fr.append('DATEFIRMWARE ' + datetime.datetime.strftime(self.drv.ECRSoftDate, "%d.%m.%Y"))
        self.drv.GetDeviceMetrics()
        list_about_fr.append('MODEL ' + self.drv.UDescription)
        list_about_fr.append('DRIVER VERSION ' + self.drv.DriverVersion)
        self.drv.Connect()
        if self.drv.ConnectionType == 6:
            list_about_fr.append('CONNECTION TYPE TCP-Socket')
        else:
            list_about_fr.append('CONNECTION TYPE LOCAL')
        list_about_fr.append('IP ADRESS ' + self.drv.IPAddress)
        self.drv.GetFieldStruct()
        self.drv.TableNumber = 16
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 1
        self.drv.ReadTable()
        list_about_fr.append('STATIC IP ' + self.drv.ValueOfFieldString)
        self.drv.TableNumber = 16
        self.drv.RowNumber = 1
        self.drv.FieldNumber = 2
        self.drv.ReadTable()
        list_about_fr.append('DHCP STATUS ' + self.drv.ValueOfFieldString)
        return list_about_fr

    def cut_print(self, cut_type: int = 2, feed: int = 10):
        """
        метод отрезки документа
        :param cut_type: int тип отрезки 2 не полная 1 полная
        :param feed: int промотать
        :return:
        """
        self.drv.WaitForPrinting()
        self.drv.StringQuantity = feed
        self.drv.FeedDocument()
        self.drv.CutType = cut_type
        self.drv.CutCheck()



    def print_str(self, i_str: str, i_font: int = 5):
        """
        печать одиночной строки
        :param i_str: str
        :param i_font: int номер шрифта печати
        """
        self.drv.FontType = i_font
        self.drv.StringForPrinting = i_str
        self.drv.PrintStringWithFont()
        self.drv.WaitForPrinting()


    def i_dont_know(self):
        """
        функция-заглушка для обработки
        неизвестных мне режимов,
        всего режимов ECR 16, мне известно решение в 4 из них
        что надо делать в остальных вообще без понятия
        :return:
        """
        Mbox('я не знаю что делать', f'неизвестный режим: {self.get_ecr_status()}', 4096 + 16)

    def error_analysis_soft(self):
        """
        метод обработки ошибок связанных с данными
        :return:
        """
        not_connection = [x for x in range(-1, -7, -1)]
        self.drv.Connect()
        while True:
            logging.debug('Ошибка ' + str(self.drv.ResultCode) + '*' + self.drv.ResultCodeDescription)
            # if self.drv.ResultCode !=0:
            #     Mbox('Ошибка ' + str(self.drv.ResultCode), self.drv.ResultCodeDescription, 4096 + 16)
            #     self.continuation_printing()
            #     logging.debug('продолжили печать просто по циклу')
            if self.drv.ResultCode != 0:
                # Mbox('Ошибка ' + str(self.drv.ResultCode), self.drv.ResultCodeDescription, 4096 + 16)
                yes_no = ctypes.windll.user32.MessageBoxW(0, 'проверить связь?', 'проверьте связь', 4 + 4096 + 16)
                if yes_no == 6:
                    self.continuation_printing()
                    logging.debug('продолжили печать после проверки связи')
            if self.drv.ResultCode in not_connection:
                Mbox('Ошибка связи', 'у вас проблема со связью с кассовым аппаратом\nзаймитесь ее решением', 4096 + 16)
            else:
                self.continuation_printing()
                logging.debug('продолжили печать просто по циклу')
                return self.drv.ResultCode

    def error_analysis_hard(self):
        """
        метод обработки ошибок связаных с бумагой
        :return:
        """
        self.drv.WaitForPrinting()
        self.drv.GetECRStatus()
        count = 0
        if self.drv.ECRMode == 0 or self.drv.ECRMode == 2:
            logging.debug('ошибок нет, статус: ' + str(
                self.drv.ECRAdvancedMode) + '*' + self.drv.ECRAdvancedModeDescription)
            return 0
        if self.drv.ECRMode == 8:
            logging.debug('Статус: ' + str(
                self.drv.ECRMode) + '*' + self.drv.ECRModeDescription)
            logging.debug('Статус расширенный: ' + str(
                self.drv.ECRAdvancedMode) + '*' + self.drv.ECRAdvancedModeDescription)
            while True:
                count += 1
                if self.drv.ECRAdvancedMode == 0:
                    self.kill_document()
                    self.drv.GetECRStatus()
                    logging.debug('документ аннулирован')
                    return -2
                else:
                    Mbox('Ошибка: {0}'.format(self.drv.ECRAdvancedMode), self.drv.ECRAdvancedModeDescription, 4096 + 16)
                    logging.debug('Ошибка: ' + str(self.drv.ECRAdvancedMode) + '*' + self.drv.ECRAdvancedModeDescription)
                if self.drv.ECRAdvancedMode == 2 or self.drv.ECRAdvancedMode == 1:
                    Mbox('нет бумаги', 'поменяйте вы уже бумагу наконец', 4096 + 16)
                if self.drv.ECRAdvancedMode == 3:
                    self.continuation_printing()
                    logging.debug('Раз до сюда дошли - ошибок нет, статус: ' + str(self.drv.ECRAdvancedMode) + '*' + self.drv.ECRAdvancedModeDescription)
                    break
                self.drv.WaitForPrinting()
                self.drv.GetECRStatus()
                if self.drv.ECRMode == 0 or self.drv.ECRMode == 2:
                    logging.debug('ошибок нет, статус: ' + str(
                        self.drv.ECRAdvancedMode) + '*' + self.drv.ECRAdvancedModeDescription)
                    return 0
        else:
            Mbox('Ошибка: {0}'.format(self.drv.ECRMode), self.drv.ECRDescription, 4096 + 16)
            logging.debug('Ошибка: {0}'.format(self.drv.ECRMode), self.drv.ECRDescription)
        return self.drv.ECRAdvancedMode


def format_string(elem: str) -> str:
    """
    функция выравнивания строки
    добавляем в середину строки пробелы
    :param elem: str строка
    :return: выходить будем с одной строкой
    """
    len_string = 33
    pattern = elem.rpartition(' ')
    i = 0
    while len(pattern[0]) + len(' ' * i) + len(pattern[2]) < len_string:
        i += 1
    o_str = f'{pattern[0]} {" " * i} {pattern[2]}'
    return o_str


def print_operation_SBP_PAY(operation_dict: dict = {}) -> str:
    """
    печать операции PAY СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["order_operation_params"][0]["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП мерчант {operation_dict["mid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП Покупатель {operation_dict["sbp_operation_params"]["sbp_masked_payer_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["order_operation_params"][0]["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["order_operation_params"][0]["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["order_operation_params"][0]["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["order_operation_params"][0]["operation_sum"] // 100}.00'
    i_list.append(i_str)

    o_str = '\n'.join(i_list) + ' \n' * 2 + '~S' + ' \n' * 2 + '\n'.join(i_list)
    return o_str


def print_operation_SBP_REFUND(operation_dict: dict = {}) -> str:
    """
    печать операции REFUND СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["operation_sum"] // 100}.00'
    i_list.append(i_str)
    o_str = '\n'.join(i_list) + ' \n' * 2 + '~S' + '\n'.join(i_list)
    return o_str


def Mbox(title, text, style):
    """
        ##  Styles:
        ##  0 : OK
        ##  1 : OK | Cancel
        ##  2 : Abort | Retry | Ignore
        ##  3 : Yes | No | Cancel
        ##  4 : Yes | No
        ##  5 : Retry | Cancel
        ##  6 : Cancel | Try Again | Continue

    """
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)


def preparation_km(in_km: str) -> str:
    """
    функция подготовки кода маркировки к отправке в честный знак
    вставляем символы разрыва перед 91 и 92
    :param in_km: str
    :return: str
    """
    logging.debug('зашли в подготовку км')
    pattern = r'91\S+?92'
    s_break = '\x1D'
    list_break_pattern = re.findall(pattern, in_km[30:])
    if len(list_break_pattern) > 0:
        repl = (s_break + list_break_pattern[0]).replace('92', s_break + '92')
        out_km = in_km[:30] + re.sub(pattern, repl, in_km[30:])
    else:
        out_km = in_km[:]
    logging.debug('вышли из подготовки км ' + out_km)
    return out_km


def main():
    # argv[1] =  'd:\\files'
    # argv[2] = '273926_01_sale'
    # PRN = win32com.client.Dispatch('Addin.DRvFR')
    current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
    i_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    i_shtrih.shtrih_operation_fn()
    # log_file = 'd:\\files\\pinpad_' + i_shtrih.operationtype + '_' + current_time + ".log"
    # logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)
    # logging.debug(current_time + ' ' + i_shtrih.operationtype)
    # sber_pinpad = PinPad(operation_name=i_shtrih.operationtype, oper_sum=i_shtrih.sum_cashless)
    #
    # sber_pinpad.pinpad_operation()
    # i_shtrih.print_pinpad(sber_pinpad.text, CUTTER)


if __name__ == '__main__':
    main()
