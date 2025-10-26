#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
NV10 Bill Acceptor Monitor - Raspberry Pi via USB
Arduino → USB → Raspberry Pi
Cu retry logic pentru Arduino reset
═══════════════════════════════════════════════════════
"""

import serial
import serial.tools.list_ports
import json
import time
import threading
from datetime import datetime
import sys
import os

# ════════════════════════════════════════════
# CONFIGURARE
# ════════════════════════════════════════════
BAUD_RATE = 115200
running = True
RETRY_ATTEMPTS = 5
RETRY_DELAY = 2

# ════════════════════════════════════════════
# FUNCȚII HELPER
# ════════════════════════════════════════════

def find_arduino(show_details=True):
    """Găsește automat portul Arduino conectat pe USB"""
    if show_details:
        print("🔍 Căutare Arduino pe USB...")
    
    ports = serial.tools.list_ports.comports()
    
    # Caută Arduino specific (idVendor=2341 pentru Arduino original)
    for port in ports:
        # Check by VID:PID
        if port.vid == 0x2341:  # Arduino VID
            if show_details:
                print(f"✓ Arduino găsit: {port.device}")
                print(f"  Descriere: {port.description}")
                print(f"  Serial: {port.serial_number}")
            return port.device
        
        # Fallback: check by description
        description = port.description.lower()
        if any(keyword in description for keyword in 
               ['arduino', 'ch340', 'ch341', 'cp2102', 'ftdi', 'acm']):
            if show_details:
                print(f"✓ Dispozitiv găsit: {port.device}")
                print(f"  Descriere: {port.description}")
            return port.device
    
    return None


def wait_for_arduino(max_wait=10):
    """Așteaptă ca Arduino să apară (după reset)"""
    print(f"⏳ Așteptare Arduino (max {max_wait}s)...")
    
    for i in range(max_wait):
        port = find_arduino(show_details=False)
        if port:
            print(f"✓ Arduino disponibil pe {port}")
            return port
        
        # Progress indicator
        print(f"   {i+1}/{max_wait}s...", end='\r')
        time.sleep(1)
    
    print()
    return None


def connect_to_arduino(port, retry=True):
    """Conectează la Arduino cu retry logic"""
    
    for attempt in range(RETRY_ATTEMPTS if retry else 1):
        try:
            if attempt > 0:
                print(f"\n🔄 Încercare {attempt + 1}/{RETRY_ATTEMPTS}...")
                time.sleep(RETRY_DELAY)
                
                # Re-check dacă portul există
                if not os.path.exists(port):
                    print(f"⚠️  Port {port} nu mai există, căutare din nou...")
                    new_port = wait_for_arduino(max_wait=5)
                    if new_port:
                        port = new_port
                    else:
                        continue
            
            print(f"🔌 Conectare la {port}...")
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            print("✓ Port deschis!")
            
            print("⏳ Așteptare reset Arduino (3 secunde)...")
            time.sleep(3)  # Arduino se resetează când se deschide serial
            
            # Verifică că portul încă funcționează
            if ser.is_open:
                print("✓ Conexiune stabilă!")
                return ser
            
        except serial.SerialException as e:
            print(f"❌ Eroare: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                print(f"   Se reîncearcă în {RETRY_DELAY} secunde...")
            
        except Exception as e:
            print(f"❌ Eroare neașteptată: {e}")
            break
    
    return None


def print_header():
    """Header aplicație"""
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║        NV10 Bill Acceptor Monitor                 ║")
    print("║        Raspberry Pi + Arduino (USB)               ║")
    print("║        With Auto-Reconnect                        ║")
    print("╚════════════════════════════════════════════════════╝")
    print()


def print_bill_accepted(data):
    """Afișează mesaj când e acceptată bancnota"""
    channel = data.get('channel', '?')
    value = data.get('value', 0)
    pulse_ms = data.get('pulse_ms', 0)
    total_bills = data.get('total_bills', 0)
    total_amount = data.get('total_amount', 0)
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║          ✓✓✓ BANCNOTĂ ACCEPTATĂ! ✓✓✓              ║")
    print("╠════════════════════════════════════════════════════╣")
    print(f"║  ⏰ Ora:        {timestamp}                           ║")
    print(f"║  📍 Canal:      {channel}                                  ║")
    print(f"║  💵 Valoare:    {value} RON                              ║")
    print(f"║  ⚡ Puls:       {pulse_ms} ms                              ║")
    print("╠════════════════════════════════════════════════════╣")
    print(f"║  📊 Total bancnote: {total_bills} buc                          ║")
    print(f"║  💰 Total valoare:  {total_amount} RON                          ║")
    print("╚════════════════════════════════════════════════════╝")
    print()


def print_statistics(data):
    """Afișează statistici"""
    print()
    print("═" * 54)
    print("  📊 STATISTICI SESIUNE")
    print("═" * 54)
    print(f"  Total bancnote: {data.get('total_bills', 0)} buc")
    print(f"  Total valoare:  {data.get('total_amount', 0)} RON")
    
    if 'channels' in data and data['channels']:
        print()
        print("  Detalii pe canal:")
        for ch in data['channels']:
            if ch.get('count', 0) > 0:
                channel = ch.get('channel', '?')
                value = ch.get('value', 0)
                count = ch.get('count', 0)
                total = count * value
                print(f"    • Canal {channel} ({value} RON): {count} buc = {total} RON")
    
    print("═" * 54)
    print()


def command_listener(ser):
    """Thread pentru comenzi interactive"""
    global running
    
    print("\n💡 Comenzi disponibile:")
    print("   status - Afișează statistici")
    print("   reset  - Resetează totaluri")
    print("   quit   - Ieșire")
    print()
    
    while running:
        try:
            cmd = input().strip().lower()
            
            if cmd in ['quit', 'q', 'exit']:
                print("\n🛑 Oprire aplicație...")
                running = False
                break
            
            elif cmd in ['status', 's']:
                if ser and ser.is_open:
                    ser.write(b'STATUS\n')
                    print("⏳ Solicitare statistici...")
                else:
                    print("⚠️  Nu e conectat la Arduino!")
            
            elif cmd in ['reset', 'r']:
                if ser and ser.is_open:
                    ser.write(b'RESET\n')
                    print("⏳ Resetare statistici...")
                else:
                    print("⚠️  Nu e conectat la Arduino!")
            
            elif cmd in ['help', 'h']:
                print("\nComenzi:")
                print("  status - Statistici")
                print("  reset  - Reset")
                print("  quit   - Ieșire")
                print()
            
            elif cmd:
                print(f"⚠️  Comandă necunoscută: '{cmd}'")
        
        except (EOFError, KeyboardInterrupt):
            running = False
            break
        except Exception as e:
            if running:
                print(f"❌ Eroare: {e}")


def main():
    """Funcția principală"""
    global running
    
    print_header()
    
    # Găsește Arduino
    arduino_port = find_arduino()
    
    if not arduino_port:
        print("\n❌ Arduino nu a fost găsit!")
        print("\n🔧 Verificări:")
        print("  1. Scoate și bagă Arduino din USB")
        print("  2. Așteaptă 3 secunde")
        print("  3. Rulează din nou scriptul")
        print()
        sys.exit(1)
    
    # Conectare cu retry
    ser = connect_to_arduino(arduino_port, retry=True)
    
    if not ser:
        print("\n❌ Nu s-a putut conecta la Arduino!")
        print("🔧 Încearcă:")
        print("  1. Reconectează Arduino")
        print("  2. Verifică că Arduino are cod încărcat")
        print("  3. Testează cu: sudo cat /dev/ttyACM0")
        sys.exit(1)
    
    print()
    print("═" * 54)
    print("  ✅ SISTEM GATA!")
    print("═" * 54)
    print()
    print("👉 Introdu o bancnotă în NV10...")
    print()
    
    # Pornește thread pentru comenzi
    cmd_thread = threading.Thread(target=command_listener, args=(ser,), daemon=True)
    cmd_thread.start()
    
    # Loop principal
    reconnect_attempts = 0
    max_reconnect = 3
    
    try:
        while running:
            try:
                if ser and ser.is_open and ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # Reset reconnect counter on successful read
                    reconnect_attempts = 0
                    
                    try:
                        data = json.loads(line)
                        
                        if data.get('status') == 'ready':
                            device = data.get('device', 'Arduino')
                            print(f"✓ {device} conectat și gata!")
                            print()
                        
                        elif data.get('event') == 'bill_accepted':
                            print_bill_accepted(data)
                        
                        elif data.get('status') == 'ok':
                            msg = data.get('msg')
                            if msg:
                                print(f"✓ {msg}")
                            
                            if 'total_bills' in data:
                                print_statistics(data)
                        
                        else:
                            print(f"[Info] {json.dumps(data)}")
                    
                    except json.JSONDecodeError:
                        if line:
                            print(f"[Arduino] {line}")
                
                elif not ser or not ser.is_open:
                    raise serial.SerialException("Port închis")
                
            except serial.SerialException as e:
                reconnect_attempts += 1
                print(f"\n⚠️  Conexiune pierdută: {e}")
                
                if reconnect_attempts >= max_reconnect:
                    print(f"❌ Prea multe încercări ({max_reconnect}), oprire...")
                    running = False
                    break
                
                print(f"🔄 Reconectare ({reconnect_attempts}/{max_reconnect})...")
                
                if ser:
                    try:
                        ser.close()
                    except:
                        pass
                
                time.sleep(2)
                
                # Caută din nou Arduino
                new_port = wait_for_arduino(max_wait=10)
                if new_port:
                    ser = connect_to_arduino(new_port, retry=False)
                    if ser:
                        print("✓ Reconectat cu succes!")
                        reconnect_attempts = 0
                    else:
                        print("❌ Reconectare eșuată")
                else:
                    print("❌ Arduino nu mai e disponibil")
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Ctrl+C")
        running = False
    
    finally:
        print("\n" + "═" * 54)
        print("  📊 STATISTICI FINALE")
        print("═" * 54)
        
        if ser and ser.is_open:
            try:
                ser.write(b'STATUS\n')
                time.sleep(0.5)
                
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    data = json.loads(line)
                    print_statistics(data)
            except:
                pass
            
            ser.close()
        
        print("\n✓ Aplicație oprită")
        print()


if __name__ == "__main__":
    main()