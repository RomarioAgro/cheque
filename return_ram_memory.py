import subprocess


def ram_memory():
    p = subprocess.Popen('wmic memorychip get Capacity', stdout=subprocess.PIPE, text=True, shell=True)
    p.wait()
    all_memory = 0
    for i in p.stdout.readlines():
        i_str = i.strip()
        if i_str.isdigit():
            all_memory += int(i_str)
    return all_memory // 1048576

def mini_display_qr():
    p = subprocess.Popen('WMIC PATH Win32_PnPSignedDriver GET DeviceName,DeviceID /format:list | find "USB\VID_1A86"',
                         stdout=subprocess.PIPE, text=True, shell=True)
    p.wait()
    for i in p.stdout.readlines():
        if len(i) > 0:
            return i
    return None


if __name__ == '__main__':
    h_l = mini_display_qr()
    print(h_l)


