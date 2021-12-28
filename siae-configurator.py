import os
import re
import time
import serial
import ipaddress as ip
import concurrent.futures
import serial.tools.list_ports as port_list

#from queue import Queue
#10.12.231.104 - 10.12.231.111
#Radio: 10.12.231.107
#Def GW: 10.12.231.105


def findSerialPort():
    ports = list(port_list.comports())
    for p in ports:
        return p.device


def connectToSerial(com_device):
    serialObj = serial.Serial(port=com_device, baudrate=115200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
    return serialObj


# Way to find what type of equipment you're working with: snmpget mib oid 1.3.6.1.4.1.3373.1103.1.4.0
# Unkown          - 1.3.6.1.4.1.3373.1103.1.5.1
# ALFO80HD        - 1.3.6.1.4.1.3373.1103.1.5.74
# ALFO80HDsm      - 1.3.6.1.4.1.3373.1103.1.5.75
# AGS20           - 1.3.6.1.4.1.3373.1103.1.5.76
# ALFOPlus2       - 1.3.6.1.4.1.3373.1103.1.5.77
# EasyCellGateway - 1.3.6.1.4.1.3373.1103.1.5.78
# ALFO80HDx       - 1.3.6.1.4.1.3373.1103.1.5.79
# ALFOPlus1       - 1.3.6.1.4.1.3373.1103.1.5.80


def findRadioType(matchString):
    if '1.3.6.1.4.1.3373.1103.1.5.79' in matchString:
        return "ALFO80HDX"
    elif '1.3.6.1.4.1.3373.1103.1.5.74' in matchString:
        return "ALFO80HD"
    elif '1.3.6.1.4.1.3373.1103.1.5.77' in matchString:
        return "ALFOPLUS2"
    else:
        return "Unknown Radio"


def serialWrite(serialObj, serialString, matchString):
    serialObj.write(serialString)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(serialRead, serialObj, matchString)
        return_value = future.result()

    return return_value


def serialRead(serialObj, matchString):

    if matchString == b'vlan1':
        while True:
            if serialObj.in_waiting > 0:
                serialString = serialObj.readlines()

                try:
                    return serialString

                except:
                    pass

            time.sleep(0.2)

    elif matchString == b'=: ':
        while True:
            if serialObj.in_waiting > 0:
                serialString = serialObj.readline()
                print(serialString)

                try:
                    if matchString in serialString:
                        return serialString.strip()[3:].decode('ascii')

                    #else:
                    #    return 'no match found'

                except:
                    pass

            time.sleep(0.2)

    else:
        while True:
            if serialObj.in_waiting > 0:
                serialString = serialObj.readline()
                print(serialString)

                try:
                    if matchString in serialString:
                        return serialString.strip().decode('ascii').split(':')[1]

                    #else:
                    #    return 'no match found'

                except:
                    pass

            time.sleep(0.2)


def getInterfacesList(serial_output):
    ifList = {}

    for item in serial_output:
        time.sleep(0.1)
        if b'up' in item or b'down' in item:
            list = item.strip().decode('ascii').split(' ')
            desc = list[-2] + list[-1]
            desc = desc.strip(' ')
            if desc == 'down' or desc == 'up':
                pass
            else:
                result = [re.findall(r'(\w+?)(\d\S+)', list[0])[0]]
                result = ' '.join(result[0])
                ifList[desc] = result

    return ifList


def main():

    radio_name = input("\nChoose Radio Name: ")

    while True:
        try:
            mgmt_vlan = int(input("\nChoose Management VLAN: "))

        except:
            print("Error: Non-Integer detected. Please try again.")
            continue

        else:
            if mgmt_vlan >= 1 and mgmt_vlan <= 4096:
                mgmt_vlan = str(mgmt_vlan)
                break
            else:
                print("Please enter a number in the following range [1-4096]")

    while True:
        try:
            ip_address = str(ip.ip_address(input("IP Address: ")))
            default_gw = str(ip.ip_address(input("Default Gateway: ")))
            subnet_mask = str(ip.ip_address(input("Subnet Mask: ")))

        except ValueError:
            print("\nInvalid IP detected, please try again.")
            continue
        else:
            cidr_arg = '0.0.0.0/' + subnet_mask
            cidr = str(ip.IPv4Network(cidr_arg).prefixlen)
            ip_cidr = ip_address + '/' + cidr

            try:
                if ip.ip_address(ip_address) in ip.ip_network(ip_cidr, strict=False) and ip.ip_address(default_gw) in ip.ip_network(ip_cidr, strict=False):
                    break
            except:
                pass
            else:
                print("\nThe Default Gateway: {} and IP Address: {} are not within the same subnet. Please try again.".format(default_gw, ip_address))
                continue

    port = findSerialPort()
    serialObj = connectToSerial(port)

    #thread = Thread(target=serialRead, args= (serialObj, equipTypeOID, ))
    #thread.start()
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'enable\n')
    time.sleep(0.2)
    serialObj.write(b'conf t\n')
    time.sleep(0.2)
    serialObj.write(b'exit\n')
    time.sleep(0.2)

    serialString = b'show interfaces description\n'
    return_value = serialWrite(serialObj, serialString, b'vlan1')

    time.sleep(0.3)
    #This will have the radio's interface list and the respective descriptions in the form of a dictionary.
    ifList = getInterfacesList(return_value)

    serialObj.write(b'configure terminal\n')

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.1.4.0\n'
    return_value = serialWrite(serialObj, serialString, b'1.3.6.1.4.1.3373.1103.1.5.')

    #This will return the type of radio we're dealing with i.e. ALFO80HDX,ALFO80HD or ALFOPLUS2
    radio_type = findRadioType(return_value)

    if radio_type == "ALFO80HDX" or radio_type == 'ALFOPLUS2':

        #Need logic to figure out Duplex Frequency Options and then set it
        #After that need to determine frequency list
        index = 1
        duplex_freqs = []
        while True:
            serialStringPrep = 'snmpget mib oid 1.3.6.1.4.1.3373.1103.80.30.1.2.1.' + str(index) + '\n'
            serialString = bytes(serialStringPrep, encoding='utf-8')
            return_value = serialWrite(serialObj, serialString, b'=: ')
            duplex_freq = int(return_value)

            if duplex_freq == 0:
                break
            else:
                duplex_freqs.append(duplex_freq)
                index += 1

        if len(duplex_freqs) > 1:
            print('This radio supports the following duplex frequencies [MHz]: {}'.format([freq / 10**3 for freq in duplex_freqs]))

            while True:
                try:
                    duplex_freq = int(input('Choose Duplex Frequency [MHz]: '))
                    duplex_freq = duplex_freq * 10**3

                    if duplex_freq in duplex_freqs:
                        duplex_freq = str(duplex_freq)
                        break
                    else:
                        print("Please select a valid duplex frequency.")
                        continue

                except:
                    print("Please select a valid duplex frequency.")
                    continue

        else:
            duplex_freq = str(duplex_freqs[0])

        #Set the Duplex Freq here in order to get an updated list of frequencies.
        serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.6.1.5.1 value 2\n'
        return_value = serialWrite(serialObj, serialString, b'=: ')

        serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.7.1.4.1.1 value 2\n'
        return_value = serialWrite(serialObj, serialString, b'=: ')

        serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.9.1.5.1 value ' + duplex_freq + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        return_value = serialWrite(serialObj, serialString, b'=: ')

    elif radio_type == "ALFO80HD":
        index = 65
        duplex_freqs = []
        while True:
            serialStringPrep = 'snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.' + str(index) + '.1\n'
            serialString = bytes(serialStringPrep, encoding='utf-8')
            return_value = serialWrite(serialObj, serialString, b'=: ')
            duplex_freq = int(return_value)

            if duplex_freq == -2:
                break
            else:
                duplex_freqs.append(duplex_freq)
                index += 1

        if len(duplex_freqs) > 1:
            print('This radio supports the following duplex frequencies [MHz]: {}'.format(
                [freq / 10 ** 3 for freq in duplex_freqs]))

            while True:
                try:
                    duplex_freq = int(input('Choose Duplex Frequency [MHz]: '))
                    duplex_freq = duplex_freq * 10 ** 3

                    if duplex_freq in duplex_freqs:
                        duplex_freq = str(duplex_freq)
                        break
                    else:
                        print("Please select a valid duplex frequency.")
                        continue

                except:
                    print("Please select a valid duplex frequency.")
                    continue

        else:
            duplex_freq = str(duplex_freqs[0])

        # Set the Duplex Freq here in order to get an updated list of frequencies.
        serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 2\n'
        return_value = serialWrite(serialObj, serialString, b'=: ')

        serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 2\n'
        return_value = serialWrite(serialObj, serialString, b'=: ')

        serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.71.1 value ' + duplex_freq + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        return_value = serialWrite(serialObj, serialString, b'=: ')

    hex_name = ":".join("{:02x}".format(ord(c)) for c in radio_name)
    
    if radio_type == 'ALFO80HD':
        Alfo80HD(hex_name,radio_type,serialObj,ip_address,default_gw,subnet_mask,duplex_freq,mgmt_vlan,ifList)
    else:
        AlfoPlus2(hex_name,radio_type,serialObj,ip_address,default_gw,subnet_mask,duplex_freq,mgmt_vlan,ifList)


def AlfoPlus2(hex_name,radio_type,serialObj,ip_address,default_gw,subnet_mask,duplex_freq,mgmt_vlan,ifList):

    serialObj.write(b'admin\n')
    serialObj.write(b'admin\n')
    serialObj.write(b'enable\n')
    serialObj.write(b'conf t\n')

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.80.28.1.2.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    start_freq = return_value

    time.sleep(0.2)

    start_freq_int = int(start_freq)
    start_freq_int = int(start_freq_int / 10 ** 6)

    if start_freq_int == 6:
        # 65536 * 4QAM + 60 MHz = 65536 * 2 + 15
        modulation = '4QAM'
        bandwidth = '60MHz'
        serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.8.1.1.1 value 131087\n')
    else:
        # 65536 * 4QAM + 80 MHz = 65536 * 2 + 16
        modulation = '4QAM'
        bandwidth = '80MHz'
        serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.8.1.1.1 value 131088\n')

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.7.1.4.1.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.6.1.5.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.80.28.1.2.1\n'
    match_str = bytes(str(start_freq_int), encoding='utf-8')
    return_value = serialWrite(serialObj, serialString, match_str)
    start_freq = return_value

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.80.28.1.3.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    stop_freq = return_value

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.80.28.1.4.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    step_freq = return_value

    # This will provide a list of frequencies used by the radio
    freq_list = list(range(int(start_freq), int(stop_freq) + int(step_freq), int(step_freq)))
    print('\nThis {} radio supports the following frequencies with {} bandwidth and {} modulation: '.format(radio_type, bandwidth, modulation))
    print([freq / 10 ** 3 for freq in freq_list])

    while True:
        try:
            freq = float(input('Choose Radio Frequency [MHz]: '))
            freq = int((freq * 10 ** 3))

            if freq in freq_list:
                freq = str(freq)
                break
            else:
                print("Please select a frequency from the list.")
                continue

        except:
            print("Please select a valid frequency from the list.")
            continue

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.1.16.0 value 126\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')

    serialObj.write(b'exit\n')
    serialObj.write(b'sleep 30\n')
    serialObj.write(b'reload\n')

    time.sleep(180)

    serialObj.write(b'\n')
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'enable\n')
    time.sleep(0.2)
    serialObj.write(b'conf t\n')
    time.sleep(0.2)

    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.1.10.0 value ' + hex_name + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    gi_ports = 'Gi '
    ex_ports = 'Ex '
    all_ports = ''
    all_LAN_ports = []
    all_ports_except_TRX = ''
    all_ports_except_TRX_MNGT = []
    trx_port = ifList['TRX']
    mgmt_only = ifList['MNGT']

    try:
        xglan_only = ifList['XGLAN1']
    except:
        xglan_only = ifList['XGLAN']

    for key, value in ifList.items():

        interface_type = value.split(' ',1)[0]
        interface_num = value.split(' ', 1)[1]

        if 'Gi' in interface_type:
            gi_ports = gi_ports + interface_num + ','

        elif 'Ex' in interface_type:
            ex_ports = ex_ports + interface_num + ','

        if 'LAN' in key:
            all_LAN_ports = all_LAN_ports + [value]

        if 'TRX' not in key and 'MNGT' not in key:
            all_ports_except_TRX_MNGT = all_ports_except_TRX_MNGT + [value]

        serialStringPrep = 'interface ' + value + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'no shutdown\n')
        serialObj.write(b'exit\n')

    gi_ports = gi_ports[:-1]
    ex_ports = ex_ports[:-1]
    all_ports = gi_ports + ' ' + ex_ports

    trx_interface_type = trx_port.split(' ')[0]
    trx_interface_num = trx_port.split(' ')[1]
    trx_interface_num_slot = trx_interface_num.split('/')[0]
    trx_interface_num_port = trx_interface_num.split('/')[1]

    pattern = r'(,' + trx_interface_num_slot + '\/' + trx_interface_num_port + ')|(' + trx_interface_num_slot + '\/' + trx_interface_num_port + ')'

    if 'Gi' in trx_interface_type:
        result = re.sub(pattern, '', gi_ports)
        all_ports_except_TRX = result + ' ' + ex_ports

    elif 'Ex' in trx_interface_type:
        result = re.sub(pattern, '', gi_ports)
        all_ports_except_TRX = result + ' ' + gi_ports

    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.1.20.0 value ' + ip_address + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    return_value = serialWrite(serialObj, serialString, b'=: ')

    if mgmt_vlan == '1':
        serialObj.write(b'vlan 1\n')
        serialStringPrep = 'ports ' + all_ports + ' untagged ' + all_ports + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

    else:
        serialObj.write(b'vlan 1\n')
        serialStringPrep = 'ports ' + all_ports + ' untagged ' + all_ports_except_TRX + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

        serialStringPrep = 'vlan ' + mgmt_vlan + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialStringPrep = 'ports ' + all_ports + ' untagged ' + mgmt_only + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

    serialStringPrep = 'default ip vlan id ' + mgmt_vlan + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialStringPrep = 'default ip address ' + ip_address + ' subnet-mask ' + subnet_mask + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialStringPrep = 'default gateway route ' + default_gw + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.73.2.1.7.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    serialObj.write(b'exit\n')
    serialObj.write(b'set hitless-restart enable\n')
    serialObj.write(b'reload\n')

    time.sleep(60)

    serialObj.write(b'\n')
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'enable\n')
    time.sleep(0.2)
    serialObj.write(b'conf t\n')
    time.sleep(0.2)

    for interface in all_ports_except_TRX_MNGT:
        serialStringPrep = 'interface ' + interface + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialStringPrep = 'port-isolation add ' + trx_port + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialObj.write(b'exit\n')

    serialStringPrep = 'interface ' + xglan_only + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)
    serialObj.write(b'speed auto\n')
    serialObj.write(b'exit\n')

    serialObj.write(b'system mtu 12266\n')
    time.sleep(3)
    serialObj.write(b'\n')
    time.sleep(0.2)

    ##GROUP CREATION
    #The contents of accessControlGroupRowStatus can only be changed if this object is notInService (2)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.4.82.111.111.116 value 2\n')

    #Create entries for the three groups and setting it to createAndWait (5) - (NMS5UX, control, EWsnmp420 respectively)
    #Name of Group (NMS5UX, control, EWsnmp420 respectively)
    #Profile (Admin (1), Read/Write (2), Maintenance (3), Readyonly (4))
    # Allowed Protocols
    # HTTP (Allow (2), Deny (1))
    # HTTPS (Allow (2), Deny (1))
    # SNMP (Deny (1), AllowV1 (2), AllowV2c (3), AllowV3 (4))
    # FTP (Deny (1), Allow (2))
    # SFTP (Deny (1), Allow (2))
    # SSH (Deny (1), Allow (2))
    # Setting group entries back to active (1) - (NMS5UX, control, EWsnmp420 respectively)

    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.6.78.77.83.53.85.88 value 5\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.6.78.77.83.53.85.88 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.6.78.77.83.53.85.88 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.6.78.77.83.53.85.88 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.6.78.77.83.53.85.88 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.6.78.77.83.53.85.88 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.6.78.77.83.53.85.88 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.6.78.77.83.53.85.88 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.6.78.77.83.53.85.88 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.7.99.111.110.116.114.111.108 value 5\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.7.99.111.110.116.114.111.108 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.7.99.111.110.116.114.111.108 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.7.99.111.110.116.114.111.108 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.7.99.111.110.116.114.111.108 value 3\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.7.99.111.110.116.114.111.108 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.7.99.111.110.116.114.111.108 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.7.99.111.110.116.114.111.108 value 2\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.7.99.111.110.116.114.111.108 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.9.69.87.115.110.109.112.52.50.48 value 5\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.9.69.87.115.110.109.112.52.50.48 value 4\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.9.69.87.115.110.109.112.52.50.48 value 3\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.9.69.87.115.110.109.112.52.50.48 value 1\n')
    time.sleep(0.3)
    #Setting contents of accessControlGroupRowStatus back to active (1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.4.82.111.111.116 value 1\n')

    # Setting FTP Server IP Address
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.30.3.0 value 204.14.36.3\n')

    #USERS CREATION
    # The contents of accessControlUserRowStatus can only be changed if this object is notInService (2)
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.4.114.111.111.116 value 2\n')
    #time.sleep(0.2)

    #Create entries for the three users and setting it to createAndWait (5) - (NMS5UX, control, EWsnmp420 respectively)
    #Name of Users (NMS5UX, control, EWsnmp420 respectively)
    #Connecting Users to Groups (NMS5UX, control, EWsnmp420 respectively)
    #Setting user passwords (SIAEMICR, PhrogBe17210, EWsnmp420 respectively)
    #Setting user authentication protocol (noAuth (1), md5 (2), sha (3))
    #Setting user authentication key if related group can use snmpv3 protocol
    #Setting user cipher protocol (noPriv (1), des (2), aes (3))
    #Setting user cipher key if related group can use snmpv3 protocol
    #Setting user timeout after login
    #Setting user entries back to active (1) - (NMS5UX, control, EWsnmp420 respectively)

    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.6.78.77.83.53.85.88 value 5\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.6.78.77.83.53.85.88 value 53:49:41:45:4D:49:43:52\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.6.78.77.83.53.85.88 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.6.78.77.83.53.85.88 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.6.78.77.83.53.85.88 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.6.78.77.83.53.85.88 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.6.78.77.83.53.85.88 value 3600\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.6.78.77.83.53.85.88 value 1\n')
    #time.sleep(0.3)
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.7.99.111.110.116.114.111.108 value 5\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.7.99.111.110.116.114.111.108 value 41:d6:b6:f7:d3:e9:4c:d7:6c:d7:12:4b\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.7.99.111.110.116.114.111.108 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.7.99.111.110.116.114.111.108 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.7.99.111.110.116.114.111.108 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.7.99.111.110.116.114.111.108 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.7.99.111.110.116.114.111.108 value 3600\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.7.99.111.110.116.114.111.108 value 1\n')
    #time.sleep(0.3)
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.9.69.87.115.110.109.112.52.50.48 value 5\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.9.69.87.115.110.109.112.52.50.48 value 54:e9:b7:f6:d9:db:1d:d4:6b\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.9.69.87.115.110.109.112.52.50.48 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.9.69.87.115.110.109.112.52.50.48 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.9.69.87.115.110.109.112.52.50.48 value 1\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.9.69.87.115.110.109.112.52.50.48 value 0\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.9.69.87.115.110.109.112.52.50.48 value 300\n')
    #serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.9.69.87.115.110.109.112.52.50.48 value 1\n')

    #Disable admin user credentials
    #fp.write('#snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.5.97.100.109.105.110 value 2\n')

    time.sleep(0.2)

    #Setting contents of accessControlUserRowStatus back to active (1)
    #serialObj.write(b'snmpget mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.4.114.111.111.116 value 1\n')

    #Disabling sftp service
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.2.2 value 1\n')

    #Setting username and password for ftp service (NMS5UX and SIAEMICR)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.3.1 value 4e:4d:53:35:55:58\n')
    time.sleep(0.1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.4.1 value 53:49:41:45:4d:49:43:52\n')

    #Changing status back to active (1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.6.1 value 1\n')

    #Setting up SNTP
    serialObj.write(b'sntp\n')
    serialObj.write(b'set sntp client enabled\n')
    serialObj.write(b'set sntp unicast-server ipv4 162.254.171.229 version 3\n')
    serialObj.write(b'exit\n')
    time.sleep(0.1)
    serialObj.write(b'clock time source ntp\n')

    #The contents of linkSettingsTable can be changed only if this object is notInService(2)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.6.1.5.1 value 2\n')

    #The content of radioSettingsTable can be changed only if this object is notInService(2)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.7.1.4.1.1 value 2\n')

    #Set Duplex Freq
    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.9.1.5.1 value ' + duplex_freq + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    time.sleep(0.5)

    if start_freq_int == 6:
        serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.8.1.1.1 value 131087\n')
    else:
        serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.8.1.1.1 value 131088\n')

    time.sleep(0.5)

    #Set Tx Freq
    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.9.1.4.1 value ' + freq + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    time.sleep(0.2)

    #Sets the ATPC Thresholds
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.9.1.8.1 value -30\n')
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.9.1.9.1 value -33\n')

    #The content of radioSettingsTable have been modified so setting this object back to active(1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.7.1.4.1.1 value 1\n')

    #The contents of linkSettingsTable have been modified so setting this object back to active(1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.80.6.1.5.1 value 1\n')
    serialObj.write(b'exit\n')


def Alfo80HD(hex_name,radio_type,serialObj,ip_address,default_gw,subnet_mask,duplex_freq,mgmt_vlan,ifList):

    serialObj.write(b'admin\n')
    serialObj.write(b'admin\n')
    serialObj.write(b'enable\n')
    serialObj.write(b'conf t\n')

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.48.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    start_freq = return_value

    time.sleep(0.2)

    start_freq_int = int(start_freq)
    start_freq_int = int(start_freq_int / 10 ** 6)

    # 65536 * 4QAM + 500 MHz = 65536 * 2 + 12
    modulation = '4QAM'
    bandwidth = '500MHz'
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.5.1 value 131084\n')

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.48.1\n'
    match_str = bytes(str(start_freq_int), encoding='utf-8')
    return_value = serialWrite(serialObj, serialString, match_str)
    start_freq = return_value

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.49.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    stop_freq = return_value

    serialString = b'snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.52.1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    step_freq = return_value

    # This will provide a list of frequencies used by the radio
    freq_list = list(range(int(start_freq), int(stop_freq) + int(step_freq), int(step_freq)))
    print('\nThis {} radio supports the following frequencies with {} bandwidth and {} modulation: '.format(radio_type, bandwidth, modulation))
    print([freq / 10 ** 3 for freq in freq_list])

    while True:
        try:
            freq = float(input('Choose Radio Frequency [MHz]: '))
            freq = int((freq * 10 ** 3))

            if freq in freq_list:
                freq = str(freq)
                break
            else:
                print("Please select a frequency from the list.")
                continue

        except:
            print("Please select a valid frequency from the list.")
            continue

    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.1.10.0 value ' + hex_name + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    gi_ports = 'Gi '
    all_ports = ''
    all_LAN_ports = 'Gi '
    all_ports_except_TRX = ''
    all_ports_except_TRX_MNGT_AUX = []
    trx_port = ifList['Radio']
    mgmt_only = ifList['Mngt']
    aux_only = ifList['Aux']

    for key, value in ifList.items():

        interface_type = value.split(' ',1)[0]
        interface_num = value.split(' ',1)[1]

        if 'Gi' in interface_type:
            gi_ports = gi_ports + interface_num + ','

        if 'LAN' in key and 'Gi' in interface_type:
                all_LAN_ports += interface_num + ','

        if 'Radio' not in key and 'Mngt' not in key and 'Aux' not in key:
            all_ports_except_TRX_MNGT_AUX = all_ports_except_TRX_MNGT_AUX + [value]

        serialStringPrep = 'interface ' + value + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'no shutdown\n')
        serialObj.write(b'exit\n')

    gi_ports = gi_ports[:-1]
    all_ports = gi_ports
    all_LAN_ports = all_LAN_ports[:-1]

    trx_interface_type = trx_port.split(' ')[0]
    trx_interface_num = trx_port.split(' ')[1]
    trx_interface_num_slot = trx_interface_num.split('/')[0]
    trx_interface_num_port = trx_interface_num.split('/')[1]

    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.1.20.0 value ' + ip_address + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    return_value = serialWrite(serialObj, serialString, b'=: ')

    if mgmt_vlan == '1':
        serialObj.write(b'vlan 1\n')
        serialStringPrep = 'ports ' + all_ports + ' untagged ' + all_ports + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

    else:
        serialObj.write(b'vlan 1\n')
        serialStringPrep = 'ports ' + all_ports + ' untagged ' + all_LAN_ports + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

        serialStringPrep = 'vlan ' + mgmt_vlan + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialStringPrep = 'ports ' + all_ports + ' untagged ' + mgmt_only + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)
        serialObj.write(b'exit\n')

    serialStringPrep = 'default ip vlan id ' + mgmt_vlan + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialStringPrep = 'default ip address ' + ip_address + ' subnet-mask ' + subnet_mask + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialStringPrep = 'default gateway route ' + default_gw + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialString = b'snmpset mib oid 1.3.6.1.4.1.3373.1103.73.2.1.7.1 value 1\n'
    return_value = serialWrite(serialObj, serialString, b'=: ')
    serialObj.write(b'exit\n')
    serialObj.write(b'set hitless-restart enable\n')
    serialObj.write(b'reload\n')

    time.sleep(90)

    serialObj.write(b'\n')
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'admin\n')
    time.sleep(0.2)
    serialObj.write(b'enable\n')
    time.sleep(0.2)
    serialObj.write(b'conf t\n')
    time.sleep(0.2)

    for interface in all_ports_except_TRX_MNGT_AUX:
        serialStringPrep = 'interface ' + interface + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialStringPrep = 'port-isolation add ' + trx_port + '\n'
        serialString = bytes(serialStringPrep, encoding='utf-8')
        serialObj.write(serialString)

        serialObj.write(b'exit\n')

    serialObj.write(b'system mtu 12266\n')
    time.sleep(3)
    serialObj.write(b'\n')
    time.sleep(0.2)

    # Disabling sftp service
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.2.2 value 1\n')

    # Setting username and password for ftp service (NMS5UX and SIAEMICR)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.3.1 value 4e:4d:53:35:55:58\n')
    time.sleep(0.1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.4.1 value 53:49:41:45:4d:49:43:52\n')

    # Changing status back to active (1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.6.1 value 1\n')

    #Setting up SNTP
    serialObj.write(b'sntp\n')
    serialObj.write(b'set sntp client enabled\n')
    serialObj.write(b'set sntp unicast-server ipv4 162.254.171.229 version 3\n')
    serialObj.write(b'exit\n')
    time.sleep(0.1)
    serialObj.write(b'clock time source ntp\n')
    time.sleep(0.1)
    serialObj.write(b'conf t')
    time.sleep(0.1)

    #The contents of radioEquipRowStatus and radioBranchRowStatus can be changed only if this object is notInService(2)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 2\n')
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 2\n')

    #Set Duplex Freq
    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.71.1 value ' + duplex_freq + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.5.1 value 131084\n')

    time.sleep(5)

    serialObj.write(b'\n')

    #Set Tx Freq
    serialStringPrep = 'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.2.1 value ' + freq + '\n'
    serialString = bytes(serialStringPrep, encoding='utf-8')
    serialObj.write(serialString)

    time.sleep(0.2)

    #Sets the ATPC Thresholds
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.6.1 value -30\n')
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.7.1 value -33\n')

    #The contents of radioBranchRowStatus and radioEquipRowStatus will be set back to Active(1)
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 1\n')
    serialObj.write(b'snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 1\n')
    serialObj.write(b'exit\n')

    '''
    with open(file_path, 'w') as fp:
        fp.write('#################################\n')
        fp.write('######ALFO80HD PORT INFO#######\n')
        fp.write('#################################\n')
        fp.write('#<LAN1>  = gigabitethernet 0/10\n')
        fp.write('#<LAN2>  = gigabitethernet 0/6\n')
        fp.write('#<RADIO> = gigabitethernet 0/1\n')
        fp.write('#<AUX>   = gigabitethernet 0/2\n')
        fp.write('#<MNGT>  = gigabitethernet 0/9\n')
        fp.write('\n')
        fp.write('admin\n')
        fp.write('admin\n')
        fp.write('\n')
        fp.write('configure terminal\n')
        fp.write('\n')
        fp.write('#Name of radio link (Note: Name needs to be converted to Hexadecimal. In this case, name being used is: ptp-670W-727M-siae-2g)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.1.10.0 value ' + hex_name + '\n')
        fp.write('\n')
        fp.write('#Enable AUX Port\n')
        fp.write('interface gigabitethernet 0/2\n')
        fp.write('no shutdown\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#Enable LAN 1 Port\n')
        fp.write('interface gigabitethernet 0/10\n')
        fp.write('no shutdown\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#Enable LAN 2 Port\n')
        fp.write('interface gigabitethernet 0/6\n')
        fp.write('no shutdown\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#Enable RADIO Port\n')
        fp.write('interface gigabitethernet 0/1\n')
        fp.write('no shutdown\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('##################\n')
        fp.write('####MNGT PLANE####\n')
        fp.write('##################\n')
        fp.write('#MNGT InBand IP/VLAN ROUTING CONFIGURATION\n')
        fp.write('#Configure IP Address, Default Gateway, SNMP agent, Change Management VLAN\n')
        fp.write('\n')
        fp.write('# Set IP\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.1.20.0 value ' + ip_address + '\n')
        fp.write('\n')
        fp.write('#MGNT VLAN CONFIGURATION\n')
        fp.write('vlan 1\n')
        fp.write('ports gigabitethernet 0/1,0/2,0/6,0/9,0/10 untagged gigabitethernet 0/6,0/10\n')
        fp.write('exit\n')
        fp.write('vlan ' + mgmt_vlan + '\n')
        fp.write('ports gigabitethernet 0/1,0/2,0/6,0/9,0/10 untagged gigabitethernet 0/9\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#MNGT VLAN/IP ROUTING SETTINGS\n')
        fp.write('#Change Management VLAN\n')
        fp.write('default ip vlan id ' + mgmt_vlan + '\n')
        fp.write('#Configure IP Address and Netmask\n')
        fp.write('default ip address ' + ip_address + ' subnet-mask ' + subnet_mask + '\n')
        fp.write('#Configure Default Gateway\n')
        fp.write('default gateway route ' + default_gw + '\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#Set the Port Alarm Report to Disable (Disable (1) or Enable (2))\n')
        fp.write('configure terminal\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.73.2.1.7.1 value 1\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#PORT ISOLATION\n')
        fp.write('configure terminal\n')
        fp.write('interface gigabitethernet 0/6\n')
        fp.write('port-isolation add gigabitethernet 0/1\n')
        fp.write('exit\n')
        fp.write('interface gigabitethernet 0/10\n')
        fp.write('port-isolation add gigabitethernet 0/1\n')
        fp.write('exit\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('#Set XGLAN to no negotiation\n')
        fp.write('configure terminal\n')
        fp.write('Interface gigabitethernet 0/1\n')
        fp.write('speed auto\n')
        fp.write('no negotiation\n')
        fp.write('no shutdown\n')
        fp.write('end\n')
        fp.write('\n')
        fp.write('#######################\n')
        fp.write('####GENERAL FEATUES####\n')
        fp.write('#######################\n')
        fp.write('#SYSTEM MTU\n')
        fp.write('#Configure MTU size for all ports to 12266\n')
        fp.write('configure terminal\n')
        fp.write('system mtu 12266\n')
        fp.write('exit\n')
        fp.write('\n')
        fp.write('############################################################################################################################\n')
        fp.write('#GROUPS CONFIG                                                                                                             #\n')
        fp.write('############################################################################################################################\n')
        fp.write('\n')
        fp.write('configure terminal\n')
        fp.write('\n')
        fp.write('#The contents of accessControlGroupRowStatus can only be changed if this object is notInService (2)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.4.82.111.111.116 value 2\n')
        fp.write('\n')
        fp.write('#Create entries for the three groups and setting it to createAndWait (5) - (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.6.78.77.83.53.85.88 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.7.99.111.110.116.114.111.108 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.9.69.87.115.110.109.112.52.50.48 value 5\n')
        fp.write('\n')
        fp.write('#Name of Group (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.1.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
        fp.write('\n')
        fp.write('#Profile (Admin (1), Read/Write (2), Maintenance (3), Readyonly (4))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.2.9.69.87.115.110.109.112.52.50.48 value 4\n')
        fp.write('\n')
        fp.write('#Allowed Protocols\n')
        fp.write('#HTTP (Allow (2), Deny (1))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.6.78.77.83.53.85.88 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.7.99.111.110.116.114.111.108 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.3.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#HTTPS (Allow (2), Deny (1))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.6.78.77.83.53.85.88 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.7.99.111.110.116.114.111.108 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.4.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#SNMP (Deny (1), AllowV1 (2), AllowV2c (3), AllowV3 (4))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.6.78.77.83.53.85.88 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.7.99.111.110.116.114.111.108 value 3\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.5.9.69.87.115.110.109.112.52.50.48 value 3\n')
        fp.write('\n')
        fp.write('#FTP (Deny (1), Allow (2))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.6.78.77.83.53.85.88 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.7.99.111.110.116.114.111.108 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.6.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#Setting FTP Server IP Address\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.30.3.0 value 204.14.36.3\n')
        fp.write('\n')
        fp.write('#SFTP (Deny (1), Allow (2))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.7.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#SSH (Deny (1), Allow (2))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.6.78.77.83.53.85.88 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.7.99.111.110.116.114.111.108 value 2\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.8.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#Setting group entries back to active (1) - (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.2.1.9.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('############################################################################################################################\n')
        fp.write('#USERS CONFIG                                                                                                              #\n')
        fp.write('############################################################################################################################\n')
        fp.write('\n')
        fp.write('#Create entries for the three users and setting it to createAndWait (5) - (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.6.78.77.83.53.85.88 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.7.99.111.110.116.114.111.108 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.9.69.87.115.110.109.112.52.50.48 value 5\n')
        fp.write('\n')
        fp.write('#Name of Users (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.1.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
        fp.write('\n')
        fp.write('#Connecting Users to Groups (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.6.78.77.83.53.85.88 value 4e:4d:53:35:55:58\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.7.99.111.110.116.114.111.108 value 63:6f:6e:74:72:6f:6c\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.2.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
        fp.write('\n')
        fp.write('#Setting user passwords (SIAEMICR, PhrogBe17210, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.6.78.77.83.53.85.88 value 53:49:41:45:4d:49:43:52\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.7.99.111.110.116.114.111.108 value 50:68:72:6f:67:42:65:31:37:32:31:30\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.3.9.69.87.115.110.109.112.52.50.48 value 45:57:73:6e:6d:70:34:32:30\n')
        fp.write('\n')
        fp.write('#Setting user authentication protocol (noAuth (1), md5 (2), sha (3))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.4.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#Setting user authentication key if related group can use snmpv3 protocol\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.6.78.77.83.53.85.88 value 0\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.7.99.111.110.116.114.111.108 value 0\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.5.9.69.87.115.110.109.112.52.50.48 value 0\n')
        fp.write('\n')
        fp.write('#Setting user cipher protocol (noPriv (1), des (2), aes (3))\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.6.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#Setting user cipher key if related group can use snmpv3 protocol\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.6.78.77.83.53.85.88 value 0\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.7.99.111.110.116.114.111.108 value 0\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.7.9.69.87.115.110.109.112.52.50.48 value 0\n')
        fp.write('\n')
        fp.write('#Setting user timeout after login\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.6.78.77.83.53.85.88 value 3600\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.7.99.111.110.116.114.111.108 value 3600\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.8.9.69.87.115.110.109.112.52.50.48 value 300\n')
        fp.write('\n')
        fp.write('#Setting user entries back to active (1) - (NMS5UX, control, EWsnmp420 respectively)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.6.78.77.83.53.85.88 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.7.99.111.110.116.114.111.108 value 1\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.9.69.87.115.110.109.112.52.50.48 value 1\n')
        fp.write('\n')
        fp.write('#Disable admin user credentials\n')
        fp.write('#snmpset mib oid 1.3.6.1.4.1.3373.1103.5.3.1.9.5.97.100.109.105.110 value 2\n')
        fp.write('\n')
        fp.write('############################################################################################################################\n')
        fp.write('#CLIENT SERVICE CONFIG                                                                                                     #\n')
        fp.write('############################################################################################################################\n')
        fp.write('\n')
        fp.write('#Disabling sftp service\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.2.2 value 1\n')
        fp.write('\n')
        fp.write('#Setting username and password for ftp service (NMS5UX and SIAEMICR)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.3.1 value 4e:4d:53:35:55:58\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.4.1 value 53:49:41:45:4d:49:43:52\n')
        fp.write('\n')
        fp.write('#Changing status back to active (1)\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.5.5.1.6.1 value 1\n')
        fp.write('\n')
        fp.write('#Setting up SNTP\n')
        fp.write('sntp\n')
        fp.write('set sntp client enabled\n')
        fp.write('set sntp unicast-server ipv4 162.254.171.229 version 3\n')
        fp.write('exit\n')
        fp.write('clock time source ntp\n')
        fp.write('\n')
        fp.write('############################################################################################################################\n')
        fp.write('#RADIO CONFIG                                                                                                              #\n')
        fp.write('############################################################################################################################\n')
        fp.write('\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.15.4.1.2.1 value 1\n')
        fp.write('snmpget mib oid 1.3.6.1.4.1.3373.1103.15.4.1.5.1 value 131084\n')
        fp.write('\n')
        fp.write('############################################################################################################################\n')
        fp.write('#MODULATION TABLE                                                                                                          #\n')
        fp.write('# BPSK - 1                                                                                                                 #\n')
        fp.write('# 4QAM Strong - 5                                                                                                          #\n')
        fp.write('# 4QAM Strong - 8                                                                                                          #\n')
        fp.write('# 64QAM - 15                                                                                                               #\n')
        fp.write('#ACM Enabled (2 for Active, 1 for Inactive: 1.3.6.1.4.1.3373.1103.15.4.1.9.1                                               #\n')
        fp.write('#ACM Lower Profile: 1.3.6.1.4.1.3373.1103.15.4.1.7.1                                                                       #\n')
        fp.write('#ACM Upper Profile: 1.3.6.1.4.1.3373.1103.15.4.1.6.1                                                                       #\n')
        fp.write('############################################################################################################################\n')
        fp.write('\n')
        fp.write('snmpget mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 5\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.2.1 value ' + freq + '\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.6.1 value -30\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.7.1 value -33\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.71.1 value 10000000\n')
        fp.write('snmpset mib oid 1.3.6.1.4.1.3373.1103.39.2.1.73.1 value 1\n')
        fp.write('exit\n')
        fp.write('sleep 20\n')
        fp.write('reload\n')
        fp.write('\n')
        fp.write('##########################################################################################################\n')
        fp.write('#Wait roughly 4 mins, confirm you have GUI access, disconnect your serial connection and connect it again#\n')
        fp.write('##########################################################################################################\n')
        fp.write('\n')
        
        '''


if __name__ == '__main__':
    main()