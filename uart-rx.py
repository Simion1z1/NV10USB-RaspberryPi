#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
NV10 Bill Acceptor Monitor - Raspberry Pi via USB
Arduino → USB → Raspberry Pi
═══════════════════════════════════════════════════════
"""

import serial
import serial.tools.list_ports
import json
import time
import threading
from datetime import datetime
import sys

# ════════════════════════════════════════════
# CONFIGURARE
# ════════════════════════════════════════════
BAUD_RATE = 115200
running = True

# ════════════════════════════════════════════
# FUNCȚII HELPER
# ════════════════════════════════════════════

def find_arduino():
    """Găsește automat portul Arduino conectat pe USB"""
    print("🔍 Căutare Arduino pe USB...")
    
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Arduino Uno/Nano/Mega au VID:PID specific
        description = port.description.lower()
        
        if any(keyword in description for keyword in 
               ['arduino', 'ch340', 'ch341', 'cp2102', 'ftdi', 'usb serial']):
            print(f"✓ Arduino găsit: {port.device}")
            print(f"  Descriere: {port.description}")
            return port.device
    
    # Dacă nu găsește automat, listează toate porturile
    print("\n⚠️  Arduino nu a fost detectat automat.")
    print("\nPorturi seriale disponibile:")
    
    if not ports:
        print("  (niciun port serial găsit)")
        return None
    
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port.device} - {port.description}")
    
    return None


def print_header():
    """Header aplicație"""
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║        NV10 Bill Acceptor Monitor                 ║")
    print("║        Raspberry Pi + Arduino (USB)               ║")
    print("╚════════════════════════════════════════════════════╝")
    print()


def print_bill_accepted(data):
    """Afișează mesaj frumos când e acceptată bancnota"""
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
    
    # Ora
    time_str = f"  ⏰ Ora:        {timestamp}"
    padding = 52 - len(time_str)
    print(f"║{time_str}{' ' * padding}║")
    
    # Canal
    channel_str = f"  📍 Canal:      {channel}"
    padding = 52 - len(channel_str)
    print(f"║{channel_str}{' ' * padding}║")
    
    # Valoare
    value_str = f"  💵 Valoare:    {value} RON"
    padding = 52 - len(value_str)
    print(f"║{value_str}{' ' * padding}║")
    
    # Puls
    pulse_str = f"  ⚡ Puls:       {pulse_ms} ms"
    padding = 52 - len(pulse_str)
    print(f"║{pulse_str}{' ' * padding}║")
    
    print("╠════════════════════════════════════════════════════╣")
    
    # Total
    total_str = f"  📊 Total bancnote: {total_bills} buc"
    padding = 52 - len(total_str)
    print(f"║{total_str}{' ' * padding}║")
    
    amount_str = f"  💰 Total valoare:  {total_amount} RON"
    padding = 52 - len(amount_str)
    print(f"║{amount_str}{' ' * padding}║")
    
    print("╚════════════════════════════════════════════════════╝")
    print()


def print_statistics(data):
    """Afișează statistici detaliate"""
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
            count = ch.get('count', 0)
            if count > 0:
                channel = ch.get('channel', '?')
                value = ch.get('value', 0)
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
            
            if cmd == 'quit' or cmd == 'q' or cmd == 'exit':
                print("\n🛑 Oprire aplicație...")
                running = False
                break
            
            elif cmd == 'status' or cmd == 's':
                ser.write(b'STATUS\n')
                print("⏳ Solicitare statistici...")
            
            elif cmd == 'reset' or cmd == 'r':
                ser.write(b'RESET\n')
                print("⏳ Resetare statistici...")
            
            elif cmd == 'help' or cmd == 'h':
                print("\nComenzi:")
                print("  status - Statistici")
                print("  reset  - Reset")
                print("  quit   - Ieșire")
                print()
            
            elif cmd:
                print(f"⚠️  Comandă necunoscută: '{cmd}'")
                print("   Tastează 'help' pentru comenzi")
        
        except EOFError:
            break
        except Exception as e:
            if running:
                print(f"❌ Eroare comandă: {e}")


def main():
    """Funcția principală"""
    global running
    
    print_header()
    
    # Găsește Arduino
    arduino_port = find_arduino()
    
    if not arduino_port:
        print("\n❌ Nu s-a putut găsi Arduino!")
        print("\n🔧 Verificări:")
        print("  1. Arduino e conectat pe USB?")
        print("  2. Rulează: ls -l /dev/ttyUSB* /dev/ttyACM*")
        print("  3. Ai permisiuni? (sudo usermod -a -G dialout $USER)")
        print()
        
        # Permite specificare manuală
        manual = input("Introdu portul manual (ex: /dev/ttyUSB0) sau Enter pentru a ieși: ").strip()
        if manual:
            arduino_port = manual
        else:
            sys.exit(1)
    
    # Conectare
    print(f"\n🔌 Conectare la {arduino_port}...")
    
    try:
        ser = serial.Serial(arduino_port, BAUD_RATE, timeout=1)
        print("✓ Conectat cu succes!")
        print(f"✓ Baud rate: {BAUD_RATE}")
        
        time.sleep(2)  # Așteaptă reset Arduino după deschidere serial
        
    except serial.SerialException as e:
        print(f"\n❌ Eroare conexiune: {e}")
        print("\n🔧 Posibile cauze:")
        print("  - Port ocupat de altă aplicație")
        print("  - Lipsă permisiuni (sudo usermod -a -G dialout $USER)")
        print("  - Arduino defect sau cablu USB defect")
        sys.exit(1)
    
    print()
    print("═" * 54)
    print("  ✅ SISTEM GATA!")
    print("═" * 54)
    print()
    print("👉 Introdu o bancnotă în NV10 pentru test...")
    print("   (Tastează 'help' pentru comenzi)")
    print()
    
    # Pornește thread pentru comenzi
    cmd_thread = threading.Thread(target=command_listener, args=(ser,), daemon=True)
    cmd_thread.start()
    
    # Loop principal - citește date de la Arduino
    try:
        while running:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # Încearcă să parseze JSON
                    try:
                        data = json.loads(line)
                        
                        # Mesaj de status (Arduino pornit)
                        if data.get('status') == 'ready':
                            device = data.get('device', 'Arduino')
                            print(f"✓ {device} conectat și gata!")
                            print()
                        
                        # Bancnotă acceptată
                        elif data.get('event') == 'bill_accepted':
                            print_bill_accepted(data)
                        
                        # Răspuns la comandă
                        elif data.get('status') == 'ok':
                            msg = data.get('msg')
                            if msg:
                                print(f"✓ {msg}")
                            
                            # Statistici
                            if 'total_bills' in data:
                                print_statistics(data)
                        
                        # Alte mesaje
                        else:
                            print(f"[Info] {json.dumps(data)}")
                    
                    except json.JSONDecodeError:
                        # Nu e JSON, afișează ca text
                        if line:
                            print(f"[Arduino] {line}")
                
                except Exception as e:
                    print(f"❌ Eroare procesare: {e}")
            
            time.sleep(0.01)  # 10ms delay
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Întrerupere Ctrl+C")
        running = False
    
    finally:
        # Cleanup
        print("\n" + "═" * 54)
        print("  📊 STATISTICI FINALE")
        print("═" * 54)
        
        try:
            # Solicită statistici finale
            ser.write(b'STATUS\n')
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                data = json.loads(line)
                print_statistics(data)
        except:
            pass
        
        ser.close()
        print("\n✓ Port serial închis")
        print("✓ Aplicație oprită")
        print()


if __name__ == "__main__":
    main()