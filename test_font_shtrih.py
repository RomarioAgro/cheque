import win32com.client
"""
тестер шрифтов кассы
проходи по порядку, смотрим какие строки арспеатались 
значит такие шрифты в прошивке есть

"""

PRN = win32com.client.Dispatch('Addin.DRvFR')

def print_str(i_str: str, i_font: int = 5):
    """
    печать одиночной строки
    :param i_str: str
    :param i_font: int номер шрифта печати
    """
    PRN.FontType = i_font
    PRN.StringForPrinting = i_str
    PRN.PrintStringWithFont()
    PRN.WaitForPrinting()

if __name__ == '__main__':
    test_string = 'съешь еще этих французских булок, да выпей чаю'
    font_size = 1
    while font_size < 10:
        print_str('--' + str(font_size) + ') ' + test_string, font_size)
        font_size += 1
        PRN.StringQuantity = 1
        PRN.FeedDocument()
    PRN.StringQuantity = 5
    PRN.FeedDocument()
    PRN.CutType = 2
    PRN.CutCheck()

