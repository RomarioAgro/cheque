import win32com.client

Prn = win32com.client.Dispatch('Addin.DRvFR')
pinpad = win32com.client.Dispatch('SBRFSRV.Server')


pinpad.Clear()
pinpad.SParam("Amount", "99900")
pinpaderror = pinpad.NFun(4000)
mycheque = pinpad.GParamString("Cheque1251")
print(mycheque)
print(pinpaderror)
# pinpad.SParam()
Prn.CheckType = 0 #'0 ЭТО ПРОДАЖА 2 ЭТО ВОЗВРАТ 128 ЧЕК КОРРЕКЦИИ ПРОДАЖА 130 ЭТО ЧЕК КОРРЕКЦИИ ВОЗВРАТ'
Prn.Password = 1
Prn.OpenCheck()
Prn.UseReceiptRibbon = "TRUE"
# ****************************
Prn.CheckType = 1
Prn.Quantity = 1
Prn.Price = 459
Prn.Summ1 = 459
Prn.Summ1Enabled = 'TRUE'
Prn.Tax1 = 0
Prn.TaxType = 4
Prn.Department = 1
Prn.PaymentTypeSign = 4
Prn.StringForPrinting = "Ct CONCEPT рис имит чулок 21о nero 4 353  4  "
Prn.FNOperation()
print(Prn.ResultCode, Prn.ResultCodeDescription)
# ****************************
Prn.Summ1 = 459
Prn.Summ2 = 0
Prn.Summ3 = 0
Prn.Summ4 = 0
Prn.Summ14 = 0
Prn.Summ15 = 0
Prn.Summ16 = 0
Prn.TaxType = 4
Prn.FNCloseCheckEx()
print(Prn.ResultCode, Prn.ResultCodeDescription)