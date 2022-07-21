import re
qr = "0104620046412948215YOpNN_oEIAiZ91EE0792iMCZl3lrWPDGDGl1bv9A4qIUoVWStWbg+SCJxjgWUCY="
pattern =r'91\S+92'
a = re.findall(pattern, qr)
repl = ('\x1D' + a[0]).replace('92', '\x1D' + '92')
km_qr = re.sub(pattern, repl, qr)
print(qr)
print(km_qr)
