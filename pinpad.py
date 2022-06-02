import win32com.client

pinpad = win32com.client.Dispatch("SBRFSRV.Server")
# pinpad = win32com.client.Dispatch("SBRFSRV.Server")
# pinpad = win32com.client.DispatchEx("{2DB7F353-0A33-4263-AACE-1CEA09D8C0EF}")
# pinpad = win32com.client.gencache.EnsureDispatch("SBRFSRV.Server")
# pinpad.Clear
# pinpad.SParam("Amount", "199900")
# pinpaderror = pinpad.NFun(4000)
# mycheque = pinpad.GParamString("Cheque1251")
# print(mycheque)
# print(pinpaderror)
#

