import PySimpleGUI as sg
from sys import exit
import time


def show_SBP_window(latenсy: int = 20, text: str = 'данные не переданы'):
    """
    функция показа окна с прогрессом
    :param latenсy: int время в секундах показа нашего окна
    :return:
    """
    progressbar = [
        [sg.ProgressBar(latenсy, orientation='h', size=(60, 30), key='progressbar')]
    ]
    outputwin = [
        [sg.Output(size=(60, 10))]
    ]
    layout = [
        [sg.Frame('Progress', layout=progressbar)],
        [sg.Frame('Output', layout=outputwin)],
        [sg.Button('Cancel')]
    ]
    window = sg.Window('Связь с банком', layout)
    progress_bar = window['progressbar']
    show_window = True
    i_exit = 2000   #по-умолчанию ошибка выход 2000 - отказ от оплаты
    i = 0
    while show_window:
        event, values = window.read(timeout=10)
        if event == 'Cancel' or event is None or event == sg.WIN_CLOSED:
            i_exit = 2000
            break
        else:
            print(text)
            time.sleep(1)
            progress_bar.UpdateBar(i + 1)
            event, values = window.read(timeout=10)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                show_window = False
                break
        i += 1
    window.close()
    return i_exit


def main():
    latency = 60    #время в секундах, которое мы показываем наше окно
    i_text = 'ожидаем оплаты 1000 рублей'
    i_event = show_SBP_window(latenсy=latency, text=i_text)
    exit(i_event)


if __name__ == '__main__':
    main()
