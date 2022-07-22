import win32com.client
import json

PRN = win32com.client.Dispatch('Addin.DRvFR')


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r', encoding='utf-8') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


def get_ecr_status():
    PRN.Password = 30
    PRN.GetECRStatus()
    print(PRN.ECRMode, PRN.ECRModeDescription)
    return PRN.ECRMode, PRN.ECRModeDescription


def open_session(comp_rec: dict):
    PRN.Password = 30
    PRN.FnBeginOpenSession()
    PRN.WaitForPrinting()
    PRN.TagNumber = 1021
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1021']
    PRN.FNSendTag()
    PRN.TagNumber = 1203
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1203']
    PRN.FnOpenSession()
    PRN.WaitForPrinting()


def close_session(comp_rec: dict):
    PRN.Password = 30
    PRN.TagValueStr = comp_rec['Tag1021']
    PRN.FNSendTag()
    PRN.TagNumber = 1203
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1203']
    PRN.PrintReportWithCleaning()
    PRN.WaitForPrinting()


def kill_document():
    PRN.Password = 30
    PRN.SysAdminCancelCheck()
    PRN.ContinuePrint()
    PRN.WaitForPrinting()


DICT_OF_COMMAND_ECR_MODE = {
    4: open_session,
    3: close_session,
    8: kill_document
}


def execute(command):
    DICT_OF_COMMAND_ECR_MODE[command](composition_receipt)


def main(json_name):
    # проверка режима работы кассы
    # режим 2 - Открытая смена, 24 часа не кончились

    while True:
        ecr_mode, ecr_mode_description = get_ecr_status()
        if (ecr_mode == 0):
            break
        else:
            print(ecr_mode)
            execute(ecr_mode)
            pass
composition_receipt = read_composition_receipt('112233.json')
main('112233.json')

