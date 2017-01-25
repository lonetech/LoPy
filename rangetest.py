# Code to test LoPy range.
# Use the onboard RGB LED and some silly test packets

import network, socket, select, pycom, binascii, machine

def loratest():
	button = machine.Pin('G17', pull=machine.Pin.PULL_UP)
	lora=network.LoRa(mode=network.LoRa.LORA, sf=12, bandwidth=network.LoRa.BW_250KHZ, coding_rate=network.LoRa.CODING_4_8, preamble=24)
	s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
	s.settimeout(5)
	me = lora.mac()
	sawother=0
	sawresponsetome=0
	sawnoise=0
	pycom.heartbeat(False)
	got=None
	while button():
		rs, ws, es = select.select([s], [], [], 5)
		if rs:
			got = s.recv(64)
			if got.startswith(b"PING") and got[4:]!=me:
				sawother = 5
				s.send(b"PONG"+got[4:]+me)
			elif got.startswith(b"PONG"+me):
				sawresponsetome = 5
			else:
				sawnoise = 5
		else:
			s.send(b"PING"+me)

		pycom.rgbled(0x40000*sawnoise + 0x400*sawresponsetome + 0x4*sawother)
		if sawother: sawother -= 1
		if sawnoise: sawnoise -= 1
		if sawresponsetome: sawresponsetome -= 1
		#print(sawother, sawnoise, sawresponsetome, got)
	print("Exiting due to button press.")

if __name__=='main':
	print("Starting lora test")
	loratest()

