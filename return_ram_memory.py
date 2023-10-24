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

if __name__ == '__main__':
    r_memory = ram_memory()
    print(r_memory)


