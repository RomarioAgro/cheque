# -*- coding: UTF-8 -*-
import win32com.client

fr = win32com.client.Dispatch('Addin.DRvFR')

fr.StringForPrinting = '1'
fr.Price = 10
fr.Quantity = 1
fr.Summ1Enabled = False
fr.PaymentTypeSign = 4  # 1
fr.PaymentItemSign = 1
fr.FNOperation()
print(fr.ResultCode, fr.ResultCodeDescription)

qr1 = "0102900021916404213Rfn-(uL4hLHv\x1D91EE06\x1D92ZL1qUSqxS/jylFxi1Sp/HouC05T7FqUi34uslMAoDc8="
fr.BarCode = qr1
fr.ItemStatus = 1
fr.FNCheckItemBarcode()
print(fr.ResultCode, fr.ResultCodeDescription)
# print(f'������ ��������� ��������: {fr.CheckItemLocalResult}')
# print(f'�������, �� ������� �� ���� ��������� ��������� ��������: {fr.CheckItemLocalError}')
# print(f'������������ ��� ��, (��� 2100 ���): {fr.MarkingType2}')
# print(f'��� ������ �� �� ������� ������-��������: {fr.KMServerErrorCode}')
# print(f'��������� �������� ��***. (��� 2106 ���): {fr.KMServerCheckingStatus}')

fr.FNAcceptMarkingCode()

fr.Barcode = qr1
fr.FNSendItemBarcode()

fr.Summ1 = 10
fr.FNCloseCheckEx()