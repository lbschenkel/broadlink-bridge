import base64
import binascii
import copy
import re
import socket
import struct
import urllib.parse

def get_ip_addresses(address):
    addrs = set()
    try:
        for info in socket.getaddrinfo(address, None):
            addr = info[4][0]
            if addr:
                addrs.add(addr)
    except:
        pass
    return addrs

def mac_format(mac, reverse=False):
    mac = mac_parse(mac, reverse)
    if not mac:
        return None
    mac = binascii.hexlify(mac)
    assert len(mac) == 12
    mac = str(mac, 'US-ASCII').upper()
    mac = "-".join(["%s" % (mac[i:i+2]) for i in range(0, 12, 2)])
    return mac

def mac_parse(mac, reverse=False):
    if mac is None:
        return None
    if isinstance(mac, str):    
        mac = mac.replace(' ', '')
        mac = mac.replace(':', '')
        mac = mac.replace('-', '')
        mac = ''.join(mac.split())
        if len(mac) != 12 or not mac.isalnum:
            return None
        try:
            mac = binascii.unhexlify(mac)
        except:
            return None
    assert len(mac) == 6
    if reverse:
        mac = list(mac)
        mac.reverse()
        mac = bytearray(mac)
    return mac

def ir_decode(code, repeat=None):
    if not code:
        raise ValueError('Empty code')

    if code[0] not in [0x26, 0xb2, 0xd7]:
        code = code.replace(' ', '')
        (code, repeat) = ir_decode_multiply(code, repeat)
        if len(code) < 5:
            raise ValueError('Code too short')
        if code.startswith('0000'): # Pronto hex
            code = ir_decode_pronto(code)
        else: # Broadlink base64
            code = base64.b64decode(code)
        if code[0] not in [0x26, 0xb2, 0xd7]:
            raise ValueError('Not a valid Broadlink code')

    if len(code) < 6:
        raise ValueError('Code too short')
    
    if repeat is not None:
        code = copy.copy(code)
        code[1] = min((code[1] + 1) * (repeat + 1) - 1, 255)
    return (code, code[1])

MULTIPLY_PATTERN = re.compile('(?:([0-9]+)[*])(.*)')

def ir_decode_multiply(code, repeat=None):
    code = code.replace(' ', '')
    m = MULTIPLY_PATTERN.fullmatch(code)
    if m:
        number = int(m.group(1))
        code = m.group(2)
        if repeat is None:
            repeat = 0
        repeat = (repeat + 1) * number - 1
        repeat = min(255, repeat)
    return (code, repeat)

def ir_decode_pronto(pronto) -> bytearray:
    # Shameless stolen from:
    # https://gist.githubusercontent.com/appden/42d5272bf128125b019c45bc2ed3311f/raw/bdede927b231933df0c1d6d47dcd140d466d9484/pronto2broadlink.py
    codes = [int(pronto[i:i + 4], 16) for i in range(0, len(pronto), 4)]
    if codes[0]:
        raise ValueError('Pronto code should start with 0000')
    if len(codes) < 4:
        raise ValueError('Code is too short')
    if len(codes) != 4 + 2 * (codes[2] + codes[3]):
        raise ValueError('Number of pulse widths does not match preamble')
    if codes[1] == 0:
        raise ValueError('Invalid frequency')
    frequency = 1 / (codes[1] * 0.241246)
    pulses = [int(round(code / frequency)) for code in codes[4:]]
    array = bytearray()
    for pulse in pulses:
        pulse = pulse * 269 // 8192  # 32.84ms units
        if pulse < 256:
            array += bytearray(struct.pack('>B', pulse))  # 1-byte (BE)
        else:
            array += bytearray([0x00])  # next number is 2-bytes
            array += bytearray(struct.pack('>H', pulse))  # 2-bytes (BE)
    packet = bytearray([0x26, 0x00])  # 0x26 = IR, 0x00 = repeats
    packet += bytearray(struct.pack('<H', len(array)))  # byte count (LE)
    packet += array
    packet += bytearray([0x0d, 0x05])  # IR terminator
    # Add 0s to make ultimate packet size a multiple of 16 for 128-bit
    # AES encryption.
    remainder = (len(packet) + 4) % 16  # add 4-byte header (02 00 00 00)
    if remainder:
        packet += bytearray(16 - remainder)
    return packet
