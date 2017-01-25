import network, select, socket, machine, binascii
import gc, pycom,  crypto

name = binascii.hexlify(machine.unique_id())

uart = machine.UART(0, 115200)

lora = network.LoRa(mode=network.LoRa.LORA)

# turn off the green LED (default makes it shine weakly)
greenled = machine.Pin('P9', mode=machine.Pin.OUT)
greenled.value(1)
# turn off the RGB LED
pycom.heartbeat(False)
pycom.rgbled(0)

send_tries = 3
msg_seq = 0

log=[]
bt_log_readout=0
send_counter=0

def send_unsent_log():
    global send_counter
    if send_counter < len(log):
        msg = log[send_counter]
        tries = msg[0]
        if tries:
            msg[0] -= 1
            lora_s.send(b"Chat"+msg)
        else:
            send_counter += 1
def add_new_msg(text):
    global msg_seq
    msg = bytearray([send_tries, msg_seq])
    msg.extend(machine.unique_id())
    msg.extend(text)
    msg_seq = (msg_seq+1) & 0xff
    log.append(msg)
def recvd_msg(msg):
    # search log for identical message
    if msg[:4]!=b"Chat":
        return
    msg=bytearray(msg[4:])
    for lmsg in log:
        if lmsg[1:] == msg[1:]:
            # Already seen message
            return
    # New message, record it
    # It will propagate if its transmit counter permits it
    log.append(msg)
    return msg

def bt_post_handler(*args):
    add_new_msg(post.value())
def cull_log():
    log.pop(0)
    global bt_log_readout
    if bt_log_readout>0:
        bt_log_readout -= 1
    global send_counter
    if send_counter>0:
        send_counter -= 1
def bt_log_reset(*args):
    global bt_log_readout
    bt_log_readout = 0
def bt_log_read(*args):
    global bt_log_readout
    if bt_log_readout<len(log):
        bt_log_readout+=1
        if bt_log_readout<len(log):
            # Updating the value should cause a notify
            bt_log.value(log[bt_log_readout])

# UUIDs for use in lopychat:
bt = network.Bluetooth()
# BT service   ca9df61a-9251-4bde-baae-6580dffa22ef
s_uuid = b"\xca\x9d\xf6\x1a\x92\x51\x4b\xde\xba\xae\x65\x80\xdf\xfa\x22\xef"
# post message e0683361-b328-4a8d-bb85-961b57d4bbe8
p_uuid = b"\xe0\x68\x33\x61\xb3\x28\x4a\x8d\xbb\x85\x96\x1b\x57\xd4\xbb\xe8"
# message log  4886956d-b295-47a8-9c49-1c256881bf38
l_uuid = b"\x48\x86\x95\x6d\xb2\x95\x47\xa8\x9c\x49\x1c\x25\x68\x81\xbf\x38"
bt.set_advertisement(name="LoPyChat",
                     service_uuid=s_uuid)
btsvc = bt.service(uuid=s_uuid)
post = btsvc.characteristic(uuid=p_uuid)
post.callback(trigger=bt.CHAR_WRITE_EVENT, handler=bt_post_handler)
bt_log = btsvc.characteristic(uuid=l_uuid)
bt_log.callback(trigger=bt.CHAR_WRITE_EVENT, handler=bt_log_reset)
bt_log.callback(trigger=bt.CHAR_READ_EVENT, handler=bt_log_read)
lora_s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_s.setblocking(False)

min_free = 512

poll = select.poll()
poll.register(uart, select.POLLIN)
poll.register(lora_s, select.POLLIN)

inline=b""
while True:
    while log and gc.mem_free() < min_free:
        cull_log()
        gc.collect()
    timeout = crypto.getrandbits(7)[0]&0x7f
    readers = poll.poll(timeout)
    #readers, writers, errors = select.select([uart, lora_s], [], [], )
    for reader in readers:
        if reader[0] is uart:
            ch=uart.read(1)
            if ch in b"\r\n":
                uart.write(b'\r\n')
                add_new_msg(inline)
                inline = b""
            elif ch in b"\x08\x7f" and inline:
                uart.write(b'\x08 \x08')
                inline = inline[:-1]
            elif ch == b"\x0c":   # form feed, clear and dump log
                uart.write(b'\x1b[2J')   # vt100 erase screen
                for msg in log:
                    uart.write(repr(msg))
                    uart.write('\r\n')
                uart.write(inline)
            else:
                uart.write(ch)
                inline = inline + ch
        elif reader[0] is lora_s:
            msg = lora_s.recv(64)
            msg = recvd_msg(msg)
            if msg:
                uart.write(repr(msg).encode('ascii')+b"\r\n")
    if not readers:
        # probably timeout. go for retransmit
        send_unsent_log()
