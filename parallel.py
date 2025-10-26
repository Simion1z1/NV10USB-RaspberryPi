#!/usr/bin/env python3
"""
============================================
NV10 Parallel Mode - Raspberry Pi Controller
VERSIUNE cu suport pentru DIVIZOR DE TENSIUNE
============================================
"""

import RPi.GPIO as GPIO
import time
import threading
from datetime import datetime

# ============================================
# CONFIGURARE PINI GPIO (BCM numbering)
# ============================================
VEND1_PIN = 17  # Canal 1 - GPIO 17
VEND2_PIN = 27  # Canal 2 - GPIO 27
VEND3_PIN = 22  # Canal 3 - GPIO 22
VEND4_PIN = 23  # Canal 4 - GPIO 23
BUSY_PIN = 24   # Busy (opțional) - GPIO 24

# Valori bancnote pentru fiecare canal (RON)
CHANNEL_VALUES = [1, 5, 10, 50]  # Canal 1-4

# PARAMETRI pentru detectare pulsuri - AJUSTAȚI PENTRU DIVIZOR
DEBOUNCE_TIME = 0.050      # 50ms debounce (mai scurt!)
PULSE_MIN_TIME = 0.030     # Acceptă pulsuri de la 30ms (mai flexibil!)
PULSE_MAX_TIME = 0.600     # Până la 600ms
PULSE_TIMEOUT = 0.700      # Timeout maxim

# Mod debug - afișează TOATE schimbările de nivel
DEBUG_MODE = True

# Variabile globale
last_pulse_time = [0, 0, 0, 0]
total_bills = 0
total_amount = 0
channel_count = [0, 0, 0, 0]
running = True

# Lock pentru thread-safety
stats_lock = threading.Lock()


def print_header():
    """Afișează header-ul aplicației"""
    print()
    print("╔════════════════════════════════════════╗")
    print("║  NV10 Controller - Raspberry Pi       ║")
    print("║  Version 1.1 (Voltage Divider Support)║")
    print("╚════════════════════════════════════════╝")
    print()


def setup_gpio():
    """Configurează pinii GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # ✅ FĂRĂ pull-up intern - divizorul face pull-up extern
    GPIO.setup(VEND1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    GPIO.setup(VEND2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    GPIO.setup(VEND3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    GPIO.setup(VEND4_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    GPIO.setup(BUSY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    
    print("✓ GPIO configurat (BCM mode)")
    print("✓ Pini INPUT fără pull-up intern (divizor extern activ)")
    print()


def print_settings():
    """Afișează setările de detectare"""
    print("Setări detectare puls:")
    print(f"  Minim: {PULSE_MIN_TIME * 1000:.0f} ms")
    print(f"  Maxim: {PULSE_MAX_TIME * 1000:.0f} ms")
    print(f"  Timeout: {PULSE_TIMEOUT * 1000:.0f} ms")
    print(f"  Debug mode: {'ON ✓' if DEBUG_MODE else 'OFF'}")
    print()


def print_connection_status():
    """Verifică și afișează starea conexiunilor"""
    print("Status conexiuni:")
    
    pins = [VEND1_PIN, VEND2_PIN, VEND3_PIN, VEND4_PIN]
    pin_names = ["VEND1", "VEND2", "VEND3", "VEND4"]
    
    for i, (pin, name) in enumerate(zip(pins, pin_names)):
        state = GPIO.input(pin)
        status = "HIGH ✓" if state else "LOW ⚠️"
        print(f"  Canal {i+1} ({name}, GPIO {pin}): {status}")
    
    busy_state = GPIO.input(BUSY_PIN)
    busy_status = "HIGH ✓" if busy_state else "LOW"
    print(f"  Busy (GPIO {BUSY_PIN}): {busy_status}")
    print()


def test_pins_realtime():
    """Test în timp real - vezi exact ce se întâmplă pe pini"""
    print("\n" + "="*50)
    print("🔍 TEST PINI ÎN TIMP REAL")
    print("Apasă Ctrl+C pentru a opri")
    print("Introdu o bancnotă pentru a vedea pulsurile...")
    print("="*50 + "\n")
    
    pins = [
        (VEND1_PIN, "V1"),
        (VEND2_PIN, "V2"),
        (VEND3_PIN, "V3"),
        (VEND4_PIN, "V4"),
        (BUSY_PIN, "BSY")
    ]
    
    # Memorează starea anterioară
    prev_states = [GPIO.input(pin) for pin, _ in pins]
    
    try:
        counter = 0
        while True:
            current_states = [GPIO.input(pin) for pin, _ in pins]
            
            # Verifică dacă s-a schimbat ceva
            changed = False
            for i, (current, prev) in enumerate(zip(current_states, prev_states)):
                if current != prev:
                    changed = True
                    pin, name = pins[i]
                    transition = "HIGH→LOW" if prev and not current else "LOW→HIGH"
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp}] {name} (GPIO {pin}): {transition}")
            
            # Afișează starea curentă periodic
            if counter % 100 == 0:  # La fiecare secundă
                states_str = []
                for i, (pin, name) in enumerate(pins):
                    state = "HIGH" if current_states[i] else "LOW "
                    states_str.append(f"{name}:{state}")
                
                print(f"\r[Status] {' | '.join(states_str)}", end='', flush=True)
            
            prev_states = current_states
            counter += 1
            time.sleep(0.01)  # 100Hz
            
    except KeyboardInterrupt:
        print("\n\n✓ Test oprit\n")


def process_bill(channel, value, pulse_width):
    """Procesează o bancnotă acceptată"""
    global total_bills, total_amount, channel_count
    
    with stats_lock:
        total_bills += 1
        total_amount += value
        channel_count[channel - 1] += 1
    
    # Afișează mesaj mare
    print()
    print("╔════════════════════════════════════════╗")
    print("║  ✓✓✓ BANCNOTĂ ACCEPTATĂ! ✓✓✓          ║")
    print(f"║  Canal: {channel}                                 ║")
    
    value_str = f"  Valoare: {value} RON"
    padding = 40 - len(value_str)
    print(f"║{value_str}{' ' * padding}║")
    
    pulse_str = f"  Durata puls: {pulse_width:.1f} ms"
    padding = 40 - len(pulse_str)
    print(f"║{pulse_str}{' ' * padding}║")
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    time_str = f"  Ora: {timestamp}"
    padding = 40 - len(time_str)
    print(f"║{time_str}{' ' * padding}║")
    
    print("╚════════════════════════════════════════╝")
    print()
    print(f"Total sesiune: {total_amount} RON")
    print()


def check_channel(channel, pin):
    """Verifică un canal pentru pulsuri - VERSIUNE ÎMBUNĂTĂȚITĂ"""
    global last_pulse_time
    
    channel_index = channel - 1
    last_state = GPIO.input(pin)
    edge_count = 0
    
    while running:
        current_state = GPIO.input(pin)
        
        # Detectează orice schimbare (pentru debug)
        if DEBUG_MODE and current_state != last_state:
            edge_count += 1
            if edge_count % 10 == 0:  # Nu spam-ui consola
                transition = "HIGH→LOW" if last_state else "LOW→HIGH"
                print(f"[Debug] Canal {channel}: {transition}")
        
        # Detectează falling edge (HIGH -> LOW) = start puls
        if current_state == GPIO.LOW and last_state == GPIO.HIGH:
            current_time = time.time()
            
            # Verifică debounce
            if (current_time - last_pulse_time[channel_index]) > DEBOUNCE_TIME:
                
                pulse_start = time.time()
                
                # Măsoară durata pulsului cu precizie mare
                while GPIO.input(pin) == GPIO.LOW and \
                      (time.time() - pulse_start) < PULSE_TIMEOUT:
                    time.sleep(0.00001)  # 10 microsecunde!
                
                pulse_width = (time.time() - pulse_start) * 1000  # ms
                
                # Debug - afișează ORICE puls
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] Canal {channel} - Puls: {pulse_width:.1f} ms", end="")
                
                # Verifică dacă pulsul e valid
                if PULSE_MIN_TIME * 1000 <= pulse_width <= PULSE_MAX_TIME * 1000:
                    print(" → VALID ✓")
                    value = CHANNEL_VALUES[channel_index]
                    process_bill(channel, value, pulse_width)
                    last_pulse_time[channel_index] = time.time()
                    
                elif pulse_width < PULSE_MIN_TIME * 1000:
                    print(" → Prea scurt ✗")
                    
                elif pulse_width >= PULSE_TIMEOUT * 1000:
                    print(" → Timeout ✗")
                    
                else:
                    print(" → Prea lung ✗")
        
        last_state = current_state
        time.sleep(0.0001)  # 0.1ms - foarte rapid!


def print_stats():
    """Afișează statisticile sesiunii"""
    print()
    print("════════════════════════════════════════")
    print("  STATISTICI SESIUNE")
    print("════════════════════════════════════════")
    print(f"Total bancnote: {total_bills} buc")
    print(f"Total valoare: {total_amount} RON")
    print()
    
    if total_bills > 0:
        print("Detalii pe canal:")
        for i in range(4):
            if channel_count[i] > 0:
                value = CHANNEL_VALUES[i]
                count = channel_count[i]
                total = count * value
                print(f"  • Canal {i+1} ({value} RON): {count} buc = {total} RON")
    else:
        print("  Nicio bancnotă procesată încă")
    
    print("════════════════════════════════════════")
    print()


def reset_stats():
    """Resetează statisticile"""
    global total_bills, total_amount, channel_count
    
    with stats_lock:
        total_bills = 0
        total_amount = 0
        channel_count = [0, 0, 0, 0]
    
    print()
    print("✓ Statistici resetate")
    print()


def set_channel_value(channel, value):
    """Setează valoarea unui canal"""
    if 1 <= channel <= 4:
        CHANNEL_VALUES[channel - 1] = value
        print(f"✓ Canal {channel} setat la {value} RON")
    else:
        print("✗ Canal invalid (trebuie 1-4)")


def toggle_debug():
    """Activează/dezactivează modul debug"""
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    status = "ACTIVAT ✓" if DEBUG_MODE else "DEZACTIVAT"
    print(f"\n✓ Mod debug {status}\n")


def print_help():
    """Afișează lista de comenzi"""
    print()
    print("════════════════════════════════════════")
    print("  COMENZI DISPONIBILE")
    print("════════════════════════════════════════")
    print("  r - Reset statistici")
    print("  s - Afișează statistici")
    print("  c - Verifică conexiuni")
    print("  t - Test pini în timp real")
    print("  d - Toggle debug mode")
    print("  h - Help (această listă)")
    print("  v1=10 - Setează canal 1 la 10 RON")
    print("  v2=50 - Setează canal 2 la 50 RON")
    print("  q - Quit (ieșire)")
    print("════════════════════════════════════════")
    print()


def command_listener():
    """Thread pentru comenzi de la tastatură"""
    global running, CHANNEL_VALUES
    
    while running:
        try:
            cmd = input().strip().lower()
            
            if cmd == 'r':
                reset_stats()
            elif cmd == 's':
                print_stats()
            elif cmd == 'c':
                print_connection_status()
            elif cmd == 't':
                test_pins_realtime()
            elif cmd == 'd':
                toggle_debug()
            elif cmd == 'h':
                print_help()
            elif cmd == 'q':
                print("\nÎnchidere aplicație...")
                running = False
            elif cmd.startswith('v'):
                # Comandă setare valoare: v1=5
                try:
                    parts = cmd.split('=')
                    channel = int(parts[0][1:])
                    value = int(parts[1])
                    set_channel_value(channel, value)
                except:
                    print("✗ Format invalid. Exemplu: v1=10")
            elif cmd:
                print("✗ Comandă necunoscută. Tastează 'h' pentru help.")
                
        except EOFError:
            break
        except Exception as e:
            print(f"Eroare: {e}")


def main():
    """Funcția principală"""
    global running
    
    try:
        print_header()
        setup_gpio()
        print_settings()
        print_connection_status()
        
        print("════════════════════════════════════════")
        print("  GATA DE FUNCȚIONARE!")
        print("════════════════════════════════════════")
        print()
        print("Valori canale:")
        for i in range(4):
            print(f"  Canal {i+1}: {CHANNEL_VALUES[i]} RON")
        print()
        
        # Opțiune test pini
        print("⚠️  IMPORTANT: Dacă nu detectezi bancnote:")
        print("   Tastează 't' pentru test pini în timp real")
        print("   Tastează 'h' pentru toate comenzile")
        print()
        print("Introdu o bancnotă...")
        print()
        
        # Pornește thread-uri pentru fiecare canal
        threads = []
        channels_data = [
            (1, VEND1_PIN),
            (2, VEND2_PIN),
            (3, VEND3_PIN),
            (4, VEND4_PIN)
        ]
        
        for channel, pin in channels_data:
            t = threading.Thread(target=check_channel, args=(channel, pin), daemon=True)
            t.start()
            threads.append(t)
        
        # Pornește thread pentru comenzi
        cmd_thread = threading.Thread(target=command_listener, daemon=True)
        cmd_thread.start()
        
        # Statistici periodice (opțional, la 60 secunde)
        # last_stats_time = time.time()
        
        while running:
            time.sleep(1)
            
            # Dezactivat - doar dacă vrei statistici automate
            # if time.time() - last_stats_time > 60:
            #     print_stats()
            #     last_stats_time = time.time()
        
    except KeyboardInterrupt:
        print("\n\nÎntrerupere de la tastatură (Ctrl+C)")
    
    finally:
        print("\nCurățare GPIO...")
        GPIO.cleanup()
        print("✓ Aplicație închisă")


if __name__ == "__main__":
    main()