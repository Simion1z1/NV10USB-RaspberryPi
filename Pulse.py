#!/usr/bin/env python3
"""
NV10 Parallel Mode Controller pentru Raspberry Pi
Versiune: 1.1 - Fixed GPIO edge detection
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime
import threading
import signal
import sys

# ============================================
# CONFIGURARE PINI GPIO
# ============================================
VEND1_PIN = 17  # GPIO 17 (Pin 11 fizic) - Canal 1
VEND2_PIN = 27  # GPIO 27 (Pin 13 fizic) - Canal 2
VEND3_PIN = 22  # GPIO 22 (Pin 15 fizic) - Canal 3
VEND4_PIN = 23  # GPIO 23 (Pin 16 fizic) - Canal 4
BUSY_PIN = 24   # GPIO 24 (Pin 18 fizic) - Busy (opțional)

# ============================================
# VALORI BANCNOTE (RON)
# ============================================
CHANNEL_VALUES = {
    1: 1,    # Canal 1 = 1 RON
    2: 5,    # Canal 2 = 5 RON
    3: 10,   # Canal 3 = 10 RON
    4: 50    # Canal 4 = 50 RON
}

# ============================================
# PARAMETRI DETECTARE PULS
# ============================================
PULSE_MIN_TIME = 0.050  # 50ms
PULSE_MAX_TIME = 0.500  # 500ms
DEBOUNCE_TIME = 0.100   # 100ms
POLL_INTERVAL = 0.001   # 1ms pentru polling

# ============================================
# VARIABILE GLOBALE
# ============================================
total_bills = 0
total_amount = 0
channel_counts = {1: 0, 2: 0, 3: 0, 4: 0}
bill_history = []
running = True

# Lock pentru thread-safety
stats_lock = threading.Lock()

class NV10Controller:
    """Controller pentru NV10 în modul Parallel"""
    
    def __init__(self):
        self.last_pulse_time = {1: 0, 2: 0, 3: 0, 4: 0}
        self.last_state = {1: GPIO.HIGH, 2: GPIO.HIGH, 3: GPIO.HIGH, 4: GPIO.HIGH}
        self.setup_gpio()
        
    def setup_gpio(self):
        """Configurare pini GPIO"""
        # Cleanup GPIO existent
        GPIO.cleanup()
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configurare pini ca INPUT cu PULL-UP
        GPIO.setup(VEND1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(VEND2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(VEND3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(VEND4_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BUSY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print("✓ GPIO configurat\n")
    
    def check_channel(self, channel, pin):
        """Verifică un canal pentru pulsuri (polling method)"""
        global total_bills, total_amount, channel_counts, bill_history
        
        current_state = GPIO.input(pin)
        
        # Detectează falling edge (HIGH -> LOW)
        if current_state == GPIO.LOW and self.last_state[channel] == GPIO.HIGH:
            current_time = time.time()
            
            # Verifică debounce
            if current_time - self.last_pulse_time[channel] < DEBOUNCE_TIME:
                self.last_state[channel] = current_state
                return
            
            # Măsoară durata pulsului
            pulse_start = time.time()
            
            # Așteaptă să revină la HIGH
            timeout = pulse_start + PULSE_MAX_TIME * 2
            while GPIO.input(pin) == GPIO.LOW and time.time() < timeout:
                time.sleep(0.001)
            
            pulse_duration = time.time() - pulse_start
            
            # Verifică dacă pulsul e valid
            if PULSE_MIN_TIME <= pulse_duration <= PULSE_MAX_TIME:
                value = CHANNEL_VALUES[channel]
                
                # Actualizează statistici (thread-safe)
                with stats_lock:
                    total_bills += 1
                    total_amount += value
                    channel_counts[channel] += 1
                    bill_history.append({
                        'time': datetime.now(),
                        'channel': channel,
                        'value': value,
                        'pulse_duration': pulse_duration
                    })
                
                # Afișează mesaj
                self.display_bill_accepted(channel, value, pulse_duration)
                
                self.last_pulse_time[channel] = current_time
            else:
                print(f"⚠ Puls invalid pe canal {channel}: {pulse_duration*1000:.0f}ms")
        
        self.last_state[channel] = current_state
    
    def poll_channels(self):
        """Polling continuu pentru toate canalele"""
        while running:
            self.check_channel(1, VEND1_PIN)
            self.check_channel(2, VEND2_PIN)
            self.check_channel(3, VEND3_PIN)
            self.check_channel(4, VEND4_PIN)
            time.sleep(POLL_INTERVAL)
    
    def display_bill_accepted(self, channel, value, pulse_duration):
        """Afișează mesaj pentru bancnotă acceptată"""
        print()
        print("╔════════════════════════════════════════╗")
        print("║  ✓✓✓ BANCNOTĂ ACCEPTATĂ! ✓✓✓          ║")
        print(f"║  Canal: {channel}                                 ║")
        print(f"║  Valoare: {value} RON{' ' * (28 - len(str(value)))}║")
        print(f"║  Puls: {pulse_duration*1000:.0f}ms{' ' * (31 - len(str(int(pulse_duration*1000))))}║")
        print("╚════════════════════════════════════════╝")
        print()
        print(f"Total sesiune: {total_amount} RON")
        print()
    
    def get_connection_status(self):
        """Verifică statusul conexiunilor"""
        pins = {
            'Canal 1': VEND1_PIN,
            'Canal 2': VEND2_PIN,
            'Canal 3': VEND3_PIN,
            'Canal 4': VEND4_PIN,
            'Busy': BUSY_PIN
        }
        
        status = {}
        for name, pin in pins.items():
            state = GPIO.input(pin)
            status[name] = 'HIGH (idle)' if state == GPIO.HIGH else 'LOW (activ?)'
        
        return status
    
    def cleanup(self):
        """Curățare GPIO la oprire"""
        GPIO.cleanup()

def print_header():
    """Afișează header-ul aplicației"""
    print()
    print("╔════════════════════════════════════════╗")
    print("║  NV10 Controller - Raspberry Pi       ║")
    print("║  Parallel Mode - Version 1.1          ║")
    print("╚════════════════════════════════════════╝")
    print()

def print_connection_status(controller):
    """Afișează statusul conexiunilor"""
    print("Status conexiuni GPIO:")
    status = controller.get_connection_status()
    for name, state in status.items():
        print(f"  {name}: {state}")
    print()

def print_stats():
    """Afișează statistici detaliate"""
    with stats_lock:
        print()
        print("════════════════════════════════════════")
        print("  STATISTICI SESIUNE")
        print("════════════════════════════════════════")
        print(f"Total bancnote: {total_bills} buc")
        print(f"Total valoare: {total_amount} RON")
        
        if total_bills > 0:
            print(f"Medie/bancnotă: {total_amount / total_bills:.2f} RON")
        
        print()
        print("Detalii pe canal:")
        for channel in sorted(channel_counts.keys()):
            count = channel_counts[channel]
            if count > 0:
                value = CHANNEL_VALUES[channel]
                print(f"  Canal {channel} ({value} RON): {count} buc = {count * value} RON")
        
        # Ultimele 10 bancnote
        if bill_history:
            print()
            print("Ultimele 10 bancnote:")
            for bill in bill_history[-10:][::-1]:
                timestamp = bill['time'].strftime('%H:%M:%S')
                print(f"  [{timestamp}] Canal {bill['channel']}: {bill['value']} RON")
        
        print("════════════════════════════════════════")
        print()

def reset_stats():
    """Resetează statisticile"""
    global total_bills, total_amount, channel_counts, bill_history
    
    with stats_lock:
        total_bills = 0
        total_amount = 0
        channel_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        bill_history = []
    
    print()
    print("✓ Statistici resetate")
    print()

def print_help():
    """Afișează comenzile disponibile"""
    print()
    print("════════════════════════════════════════")
    print("  COMENZI DISPONIBILE")
    print("════════════════════════════════════════")
    print("  s - Afișează statistici")
    print("  r - Reset statistici")
    print("  c - Verifică conexiuni")
    print("  h - Help (această listă)")
    print("  q - Quit (oprește aplicația)")
    print("════════════════════════════════════════")
    print()

def command_thread():
    """Thread pentru comenzi de la tastatură"""
    global running
    
    print("Tastează 'h' pentru help\n")
    
    while running:
        try:
            cmd = input().strip().lower()
            
            if cmd == 's':
                print_stats()
            elif cmd == 'r':
                reset_stats()
            elif cmd == 'c':
                print_connection_status(controller)
            elif cmd == 'h':
                print_help()
            elif cmd == 'q':
                print("\nOprire...")
                running = False
                break
            elif cmd:
                print("✗ Comandă necunoscută. Tastează 'h' pentru help.")
        
        except EOFError:
            break
        except KeyboardInterrupt:
            running = False
            break

def signal_handler(sig, frame):
    """Handler pentru Ctrl+C"""
    global running
    print("\n\nOprire prin Ctrl+C...")
    running = False

def status_thread():
    """Thread pentru afișare status periodic"""
    last_status = time.time()
    
    while running:
        if time.time() - last_status > 60:  # La 60 secunde
            with stats_lock:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Alive | Total: {total_amount} RON ({total_bills} bancnote)")
            last_status = time.time()
        
        time.sleep(1)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Afișează header
    print_header()
    
    # Inițializare controller
    print("Inițializare GPIO...")
    controller = NV10Controller()
    
    # Afișează configurație
    print("Configurare pini (BCM numbering):")
    print(f"  Canal 1: GPIO {VEND1_PIN} = {CHANNEL_VALUES[1]} RON")
    print(f"  Canal 2: GPIO {VEND2_PIN} = {CHANNEL_VALUES[2]} RON")
    print(f"  Canal 3: GPIO {VEND3_PIN} = {CHANNEL_VALUES[3]} RON")
    print(f"  Canal 4: GPIO {VEND4_PIN} = {CHANNEL_VALUES[4]} RON")
    print(f"  Busy: GPIO {BUSY_PIN}")
    print()
    
    # Verifică conexiuni
    print_connection_status(controller)
    
    print("════════════════════════════════════════")
    print("  GATA DE FUNCȚIONARE!")
    print("════════════════════════════════════════")
    print()
    print("IMPORTANTE:")
    print("  • NV10 trebuie setat în modul PAR")
    print("  • Inhibits (Pin 5-8) trebuie la GND")
    print("  • LED ar trebui APRINS!")
    print()
    print("Introdu o bancnotă pentru test...")
    print()
    
    # Pornește thread-uri
    poll_thread = threading.Thread(target=controller.poll_channels, daemon=True)
    poll_thread.start()
    
    cmd_thread = threading.Thread(target=command_thread, daemon=True)
    cmd_thread.start()
    
    stat_thread = threading.Thread(target=status_thread, daemon=True)
    stat_thread.start()
    
    # Loop principal
    try:
        while running:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        pass
    
    finally:
        # Cleanup
        running = False
        time.sleep(0.5)  # Așteaptă thread-urile să termine
        
        print("\nCurățare GPIO...")
        controller.cleanup()
        print("✓ GPIO cleanup complet")
        print("\nStatistici finale:")
        print_stats()
        print("La revedere!")