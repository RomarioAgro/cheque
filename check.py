import win32com.client

# fr = win32com.client.Dispatch('Addin.DRvFR')
fr = win32com.client.GetObject('Addin.DRvFR')
# pinpad = win32com.client.Dispatch('SBRFSRV.Server')
# pinpad.Clear
# pinpad.SParam("Amount", "99900")
# pinpaderror = pinpad.NFun(4000)
# mycheque = pinpad.GParamString("Cheque1251")
# print(mycheque)
# print(pinpaderror)

fr.StringForPrinting = 'Товар ТОвр'
fr.Price = 10
fr.Quantity = 1
fr.Summ1Enabled = False
fr.PaymentTypeSign = 4  #
fr.PaymentItemSign = 1
fr.FNOperation()
print(fr.ResultCode, fr.ResultCodeDescription)

qr = "0102900021916404213Rfn-(uL4hLHv\x1D91EE06\x1D92ZL1qUSqxS/jylFxi1Sp/HouC05T7FqUi34uslMAoDc8="
fr.BarCode = qr
fr.ItemStatus = 1
fr.FNCheckItemBarcode()
print(fr.ResultCode, fr.ResultCodeDescription)
print(fr.CheckItemLocalResult)
print(fr.CheckItemLocalError)
print(fr.MarkingType2)
print(fr.KMServerErrorCode)
print(fr.KMServerCheckingStatus)

fr.FNAcceptMarkingCode()

fr.Barcode = qr
fr.FNSendItemBarcode()

fr.Summ1 = 10
fr.FNCloseCheckEx()