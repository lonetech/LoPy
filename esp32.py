# LoPy (MicroPython on ESP32) access to 64-bit timer
import uctypes

TIMG0T0_addr = 0x3ff5f000
TIMG0T1_addr = 0x3ff5f024
TIMG1T0_addr = 0x3ff60000
TIMG1T1_addr = 0x3ff60024

TIMG_regs = {
    'config': uctypes.UINT32 | 0x00, 
    # config register layout: bit 31 enable, 30 up (direction), 
    # bit 29 autoreload at alarm, 13:28 divider
    # 12 alarm edge interrupt, 11 alarm level interrupt, 10 alarm enable
    'enable': uctypes.BFUINT32 | 0x00 | 31<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'increase': uctypes.BFUINT32 | 0x00 | 30<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # counts up if increase=1 (default), otherwise down
    'autoreload': uctypes.BFUINT32 | 0x00 | 29<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # reloads value from loadhi:loadlo when timer reaches alarmhi:alarmlo if autoreload=1 (default)
    'divider': uctypes.BFUINT32 | 0x00 | 13<<uctypes.BF_POS | (29-13)<<uctypes.BF_LEN, 
    # divides APB clock (default 80MHz); only change when timer disabled
    # default is 1, which produces 2; 0 means 0x10000, others are verbatim.
    'edge_int_en': uctypes.BFUINT32 | 0x00 | 12<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'level_int_en': uctypes.BFUINT32 | 0x00 | 12<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'alarm_en': uctypes.BFUINT32 | 0x00 | 12<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # alarm and interrupts are disabled by default (continous counting)

    'lo': uctypes.UINT32 | 0x04, 
    'hi': uctypes.UINT32 | 0x08, 
    'update': uctypes.UINT32 | 0x0c, # write to trigger {hi,lo} := current_timer
    'alarmlo': uctypes.UINT32 | 0x10, 
    'alarmhi': uctypes.UINT32 | 0x14, 
    'loadlo': uctypes.UINT32 | 0x18, 
    'loadhi': uctypes.UINT32 | 0x1c, # NOTE: Missing in ESP32 TRM 1.1 register summary
    'load': uctypes.UINT32 | 0x20, # write to trigger load (current_timer := {loadhi,loadlo})
}

class Timer:
    "Crude wrapper class to access 64-bit timer"
    def __init__(self,  addr):
        self.regs = uctypes.struct(addr,  TIMG_regs)
    def __call__(self, value=None):
        # Note: probably not interrupt safe, uses big ints
        if value is None:
            self.regs.update = 0
            return self.regs.hi<<32 | self.regs.lo
        else:
            self.regs.loadhi = value>>32
            self.regs.loadlo = value & 0xffffffff
            self.regs.load = 0
    def alarm(self, value=None):
        if value is None:
            return self.regs.alarmhi<<32 | self.regs.alarmlo
        else:
            self.regs.alarmhi = value>>32
            self.regs.alarmlo = value & 0xffffffff

timer = [Timer(addr) for addr in (TIMG0T0_addr,  TIMG0T1_addr,  TIMG1T0_addr,  TIMG1T1_addr)]

# Let's not touch the watchdog and interrupts for now.

# Example:
# timer[0].regs.enable = 1
# timer[0]()    # reads timer count



# AES block
AES_addr = 0x3ff01000
AES_128 = 0
AES_192 = 1
AES_256 = 2
AES_enc = 0
AES_dec = 4
# mode = AES_256 | AES_enc
# Endian: FIXME unsure of true orders. they're specified, I just haven't deciphered fully.
# Bit 0 = key ascending byte order within word
# Bit 1 = key ascending word order
# Bit 2 = input text ascending byte order within word
# Bit 3 = input text ascending word order
# Bit 2 = output text ascending byte order within word
# Bit 3 = output text ascending word order
AES_regs = {
    'mode': uctypes.UINT32 | 0x008, 
    'endian': uctypes.UINT32 | 0x040, 
    
    'key_0': uctypes.UINT32 | 0x010, 
    'key_1': uctypes.UINT32 | 0x014, 
    'key_2': uctypes.UINT32 | 0x018, 
    'key_3': uctypes.UINT32 | 0x01c, 
    'key_4': uctypes.UINT32 | 0x020, 
    'key_5': uctypes.UINT32 | 0x024, 
    'key_6': uctypes.UINT32 | 0x028, 
    'key_7': uctypes.UINT32 | 0x02c, 
    
    'text_0': uctypes.UINT32 | 0x030, 
    'text_1': uctypes.UINT32 | 0x034, 
    'text_2': uctypes.UINT32 | 0x038, 
    'text_3': uctypes.UINT32 | 0x03c, 
    
    'start': uctypes.UINT32 | 0x000, # write 1 to start
    'idle': uctypes.UINT32 | 0x004, # 0 while busy, 1 otherwise
}

AES = uctypes.struct(AES_addr,  AES_regs)
# Note: AES accelerator doesn't seem to have interrupts. Poll idle.
# It finishes fast anyway (11-15 cycles encrypt, 21-22 decrypt).
# Probably any Python access needn't touch idle.


