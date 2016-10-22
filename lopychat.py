import network, select, socket, machine, binascii

name = binascii.hexlify(machine.unique_id())

uart = machine.UART(0, 115200)

lora = network.LoRa(mode=network.LoRa.LORA)

s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)

inline=b"\t"
while True:
    readers, writers, errors = select.select([uart, s], [], [])
    if uart in readers:
        ch=uart.read(1)
        if ch in b"\r\n":
            uart.write(b'\r\n')
            s.send(name + inline)
            inline = b"\t"
        elif ch in b"\x08\x7f" and inline:
            uart.write(b'\x08 \x08')
            inline = inline[:-1]
        else:
            uart.write(ch)
            inline = inline + ch
    if s in readers:
        uart.write(repr(s.recv(64)).encode('ascii')+b"\r\n")
