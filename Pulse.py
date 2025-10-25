from essp import SSPDevice

def main():
    print("═" * 60)
    print("  NV10 Test cu ITL eSSP Library")
    print("═" * 60)
    
    # Conectare
    nv10 = SSPDevice()
    
    try:
        # Conectează la primul device găsit
        nv10.connect(port='COM7')
        print("✓ Conectat la NV10\n")
        
        # Sync
        nv10.sync()
        print("✓ SYNC OK\n")
        
        # Informații
        print(f"Firmware: {nv10.get_firmware_version()}")
        print(f"Dataset: {nv10.get_dataset_version()}\n")
        
        # Enable
        nv10.enable()
        print("✓ NV10 ACTIVAT - LED ar trebui să fie APRINS!\n")
        
        print("═" * 60)
        print("  Introdu o bancnotă...")
        print("  Ctrl+C pentru stop")
        print("═" * 60)
        print()
        
        # Polling loop
        while True:
            events = nv10.poll()
            
            for event in events:
                if event['type'] == 'credit':
                    print(f"\n╔════════════════════════════════════╗")
                    print(f"║  BANCNOTĂ ACCEPTATĂ!               ║")
                    print(f"║  Valoare: {event['value']} RON           ║")
                    print(f"╚════════════════════════════════════╝\n")
                elif event['type'] == 'read':
                    print(f"  → Bancnotă citită: {event['value']} RON")
                elif event['type'] == 'rejected':
                    print(f"  → Bancnotă respinsă")
            
    except KeyboardInterrupt:
        print("\nOprire...")
    finally:
        nv10.disable()
        nv10.disconnect()
        print("✓ Închis")

if __name__ == "__main__":
    main()