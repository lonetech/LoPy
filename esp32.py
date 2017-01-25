# LoPy (MicroPython on ESP32) access to 64-bit timer
import uctypes

# Peripheral map:
# highaddr  4k  device
# 3ff0_0    1   dport
# 3ff0_1    1   aes
# 3ff0_2    1   rsa
# 3ff0_3    1   sha
# 3ff0_4    1   secure boot
# 3ff1_0    4   cache mmu table
# 3ff1_f    1   PID controller (per CPU)
# 3ff4_0    1   uart0
# 3ff4_2    1   spi1
# 3ff4_3    1   spi0
# 3ff4_4    1   gpio
# 3ff4_8    1   rtc (also has two blocks of 8k ram)
# 3ff4_9    1   io mux
# 3ff4_b    1   sdio slave (1/3 parts)
# 3ff4_c    1   udma1
# 3ff4_f    1   i2s0
# 3ff5_0    1   uart1
# 3ff5_3    1   i2c0
# 3ff5_4    1   udma0
# 3ff5_5    1   sdio slave (2nd of 3 parts)
# 3ff5_6    1   RMT
# 3ff5_7    1   PCNT
# 3ff5_8    1   sdio slave (3rd of 3 parts)
# 3ff5_9    1   LED PWM
# 3ff5_a    1   Efuse controller
# 3ff5_b    1   flash encryption
# 3ff5_e    1   PWM0
# 3ff5_f    1   TIMG0   (dual 64-bit general timer, tested)
# 3ff6_0    1   TIMG1   (tested)
# 3ff6_4    1   spi2
# 3ff6_5    1   spi3
# 3ff6_6    1   syscon
# 3ff6_7    1   i2c1
# 3ff6_8    1   SD/MMC (Note: only 1-bit wired on expansion board)
# 3ff6_9    2   EMAC
# 3ff6_c    1   pwm1
# 3ff6_d    1   i2s1
# 3ff6_e    1   uart2
# 3ff6_f    1   pwm2
# 3ff7_0    1   pwm3
# 3ff7_5    1   RNG


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


# GPIO registers (shouldn't be needed, there's machine.Pin)
# TRM summary tables for these are messed up
# w1t[sc] = write 1 to set/clear extras for atomic ops
GPIO_regs = {name: nr*4 | uctypes.UINT32
    for (nr, name) in enumerate("""
    - out out_w1ts out_w1tc 
    out1 out1_w1ts out1_w1tc -
    enable enable_w1ts enable_w1tc enable1
    enable1_w1ts enable1_w1tc strap in_
    in1 status status_w1ts status_w1tc
    status1 status1_w1ts status1_w1tc
    acpu_int acpu_nmi_int pcpu_int pcpu_nmi_int
    - acpi_int1 acpi_nmi_int1 pcpu_int1
    pcpu_nmi_int1
    """.split()) if name!="-"}
# Note: arrays cause allocation, not interrupt safe.
GPIO_regs['pin'] = (uctypes.ARRAY | 0x88,  40,  {
    # 1 for open drain output
    'pad_driver': uctypes.BFUINT32 | 0x00 | 2<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # disabled rising falling any low high - -
    'int_type': uctypes.BFUINT32 | 0x00 | 7<<uctypes.BF_POS | 3<<uctypes.BF_LEN, 
    'wakeup_enable': uctypes.BFUINT32 | 0x00 | 10<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'int_ena_app': uctypes.BFUINT32 | 0x00 | 13+0<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'int_ena_app_nmi': uctypes.BFUINT32 | 0x00 | 13+1<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'int_ena_pro': uctypes.BFUINT32 | 0x00 | 13+3<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'int_ena_pro_nmi': uctypes.BFUINT32 | 0x00 | 13+4<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
})
# Function block input selection (per function)
GPIO_IN_TIE1 = 0x38
GPIO_IN_TIE0 = 0x30
GPIO_regs['func_in_sel_cfg'] = (uctypes.ARRAY | 0x130,  256,  {
    # 0=gpio matrix, 1=bypass. reg name: GPIO_SIGm_IN_SEL
    'bypass': uctypes.BFUINT32 | 0x00 | 7<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # invert input value into function block
    'func_inv': uctypes.BFUINT32 | 0x00 | 6<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # selects which gpio matrix input (0-39) or 0x38=high 0x30=low
    'gpio': uctypes.BFUINT32 | 0x00 | 0<<uctypes.BF_POS | 6<<uctypes.BF_LEN, 
})
# Function block output selection (per pin)
GPIO_OUT_FUNC_GPIO = 0x100
GPIO_regs['func_out_sel_cfg'] = (uctypes.ARRAY | 0x530,  40,  {
    'oen_inv': uctypes.BFUINT32 | 0x00 | 11<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'func_oen': uctypes.BFUINT32 | 0x00 | 10<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'out_inv': uctypes.BFUINT32 | 0x00 | 11<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # 0..255=peripheral output, 256=GPIO_DATA_REG
    'func': uctypes.BFUINT32 | 0x00 | 0<<uctypes.BF_POS | 9<<uctypes.BF_LEN, 
})
GPIO = uctypes.struct(0x3ff44000,  GPIO_regs)

IOmux = uctypes.struct(0x3ff53000,  (uctypes.ARRAY | 0x10,  40,  {
    'mcu_sel': uctypes.BFUINT32 | 0 | 12<<uctypes.BF_POS | 3<<uctypes.BF_LEN, 

    'func_drv': uctypes.BFUINT32 | 0 | 10<<uctypes.BF_POS | 2<<uctypes.BF_LEN, 
    'func_ie': uctypes.BFUINT32 | 0 | 9<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'func_wpu': uctypes.BFUINT32 | 0 | 8<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'func_wpd': uctypes.BFUINT32 | 0 | 7<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 

    # mcu prefix applies during sleep mode
    'mcu_drv': uctypes.BFUINT32 | 0 | 5<<uctypes.BF_POS | 2<<uctypes.BF_LEN, 
    'mcu_ie': uctypes.BFUINT32 | 0 | 4<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'mcu_wpu': uctypes.BFUINT32 | 0 | 3<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'mcu_wpd': uctypes.BFUINT32 | 0 | 2<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    # sleep select puts pad in sleep mode
    'slp_sel': uctypes.BFUINT32 | 0 | 1<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
    'mcu_oe': uctypes.BFUINT32 | 0 | 0<<uctypes.BF_POS | 1<<uctypes.BF_LEN, 
}))
# Experiments have shown that expboard LED = G16 = P9 = GPIO 12.
# P9 is pin on LoPy, GPIO 12 is in ESP32, perhaps G16 is GPIO on WiPy 1.0.
# The G numbers do match the funny order on WiPy 1.0, which uses CC3200,
# which in turn does have the odd gaps (GPIO 16, 17, 22, 28). 
# Could map the P numbers by testing which bits they set as I did for P9. 
# Only actually matters if we need to enable peripherals for which MicroPython doesn't work.

# Example of lighting LED on expansion board:
# from machine import Pin
# led = Pin("G16",  mode=Pin.OUT)   # sets up output enable etc
# led(1)    # turns it off
# GPIO.out_w1tc = 1<<12     # turns it on (as led(0))
# GPIO.enable_w1tc = 1<<12  # turns off the output (returns to dim light)
# TODO: why is input dim light? Is there a pulldown?


# LED PWM function block
LEDC_regs = {
    'conf': uctypes.UINT32 | 0x190, 
    'apb_clk_sel': uctypes.BFUINT32 | 0x190 | 0<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
    
    'hsch': (uctypes.ARRAY | 0x000,  8,  {
	# Note: struct is 0x14, per summary table, not register reference
        'conf0': uctypes.UINT32 | 0x00,	# bitfield:
        'timer_sel': uctypes.BFUINT32 | 0x00 | 0<<uctypes.BF_POS | 2<<uctypes.BF_LEN,
        'sig_out_en': uctypes.BFUINT32 | 0x00 | 2<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'idle_lv': uctypes.BFUINT32 | 0x00 | 3<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        
        'hpoint': uctypes.UINT32 | 0x04,		# 20 bit
        'duty': uctypes.UINT32 | 0x08,		# 25 bit

        'conf1': uctypes.UINT32 | 0x0c,
        'duty_scale': uctypes.BFUINT32 | 0x0c | 0<<uctypes.BF_POS | 10<<uctypes.BF_LEN,
        'duty_cycle': uctypes.BFUINT32 | 0x0c | 10<<uctypes.BF_POS | 10<<uctypes.BF_LEN,	# amount to change duty cycle per cycle
        'duty_num': uctypes.BFUINT32 | 0x0c | 20<<uctypes.BF_POS | 10<<uctypes.BF_LEN,	# number of times to change it
        'duty_inc': uctypes.BFUINT32 | 0x0c | 30<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# increase or decrease
        'duty_start': uctypes.BFUINT32 | 0x0c | 31<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# write 1 to make these fields take effect
        
        'duty_r': uctypes.UINT32 | 0x10,
    }),

    'lsch': (uctypes.ARRAY | 0x0a0,  8,  {
	# Note: struct is 0x14, per summary table, not register reference
        'conf0': uctypes.UINT32 | 0x00,	# bitfield:
        'timer_sel': uctypes.BFUINT32 | 0x00 | 0<<uctypes.BF_POS | 2<<uctypes.BF_LEN,
        'sig_out_en': uctypes.BFUINT32 | 0x00 | 2<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'idle_lv': uctypes.BFUINT32 | 0x00 | 3<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'para_up': uctypes.BFUINT32 | 0x00 | 4<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# updates hpoint and duty
        
        'hpoint': uctypes.UINT32 | 0x04,		# 20 bit
        'duty': uctypes.UINT32 | 0x08,		# 25 bit

        'conf1': uctypes.UINT32 | 0x0c,
        'duty_scale': uctypes.BFUINT32 | 0x0c | 0<<uctypes.BF_POS | 10<<uctypes.BF_LEN,
        'duty_cycle': uctypes.BFUINT32 | 0x0c | 10<<uctypes.BF_POS | 10<<uctypes.BF_LEN,	# amount to change duty cycle per cycle
        'duty_num': uctypes.BFUINT32 | 0x0c | 20<<uctypes.BF_POS | 10<<uctypes.BF_LEN,	# number of times to change it
        'duty_inc': uctypes.BFUINT32 | 0x0c | 30<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# increase or decrease
        'duty_start': uctypes.BFUINT32 | 0x0c | 31<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# write 1 to make these fields take effect
        
        'duty_r': uctypes.UINT32 | 0x10,
    }),

    'hstimer': (uctypes.ARRAY | 0x140,  4,  {
        # bitfield conf
        # lim: count goes in range(0,2**lim), max 20
        'lim': uctypes.BFUINT32 | 0x0 | 0<<uctypes.BF_POS | 5<<uctypes.BF_LEN,
        'div_num': uctypes.BFUINT32 | 0x0 | 5<<uctypes.BF_POS | 18<<uctypes.BF_LEN,	# 10.8 fixed point divider
        'pause': uctypes.BFUINT32 | 0x0 | 23<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'rst': uctypes.BFUINT32 | 0x0 | 24<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'tick_sel': uctypes.BFUINT32 | 0x0 | 25<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# 1: apb_clk, 0: ref_clk

        'cnt': uctypes.UINT32 | 0x4,	# 20 bit
    }),
    
    'lstimer': (uctypes.ARRAY | 0x160,  4,  {
        # bitfield conf
        # lim: count goes in range(0,2**lim), max 20
        'lim': uctypes.BFUINT32 | 0x0 | 0<<uctypes.BF_POS | 5<<uctypes.BF_LEN,
        'div_num': uctypes.BFUINT32 | 0x0 | 5<<uctypes.BF_POS | 18<<uctypes.BF_LEN,	# 10.8 fixed point divider
        'pause': uctypes.BFUINT32 | 0x0 | 23<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'rst': uctypes.BFUINT32 | 0x0 | 24<<uctypes.BF_POS | 1<<uctypes.BF_LEN,
        'tick_sel': uctypes.BFUINT32 | 0x0 | 25<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# 1: apb_clk, 0: ref_clk
        'para_up': uctypes.BFUINT32 | 0x0 | 4<<uctypes.BF_POS | 1<<uctypes.BF_LEN,	# set to update

        'cnt': uctypes.UINT32 | 0x4,	# 20 bit
    }),

    # interrupt bitmasks
    # order from lsb: hstimer 0-3 overflow, lstimer 0-3 overflow, duty change end hs 0-7 ls 0-7
    'int_raw': uctypes.UINT32 | 0x180,	# raw interrupt status bits
    'int_st': uctypes.UINT32 | 0x184,	# masked interrupt status
    'int_ena': uctypes.UINT32 | 0x188,	# enables
    'int_clr': uctypes.UINT32 | 0x18c,	# clear
}
LEDC_addr = 0x3ff59000
LEDC = uctypes.struct(LEDC_addr, LEDC_regs)
