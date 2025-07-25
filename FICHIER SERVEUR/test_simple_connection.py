#!/usr/bin/env python3

# /**********************************************************************************************************************************************************************************

# Nom du fichier : test_simple_connection.py
# Rôle du fichier : Fichier gérant le test de connexion persistante.

# Auteur : Maxime BRONNY
# Version : V1
# Licence : Réalisé dans le cadre des cours "PROJET TUTEURE" L3 INFORMATIQUE IED
# Usage : python3 test_simple_connection.py pour tester la connexion persistante.

# *********************************************************************************************************************************************************************************/


# =============================================================================
# Importation des bibliothèques nécessaires
# =============================================================================

import socket
import time
import threading

# =============================================================================
# Fonction utilitaire pour tester la connexion persistante
# =============================================================================

def simple_persistent_test():
    """Test de connexion persistante simple"""
    print("=== Test de connexion persistante simple ===")
    
    try:
        # Se connecter au serveur
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)  # Timeout de 10 secondes pour la connexion
        s.connect(('192.168.1.58', 5001))
        s.settimeout(None)  # Enlever le timeout après connexion
        print("[+] Connecté au serveur")
        
        # Variables de suivi
        message_count = 0
        heartbeat_count = 0
        start_time = time.time()
        last_heartbeat = time.time()
        
        # Boucle principale - écouter pendant 60 secondes
        while time.time() - start_time < 60:
            try:
                # Vérifier s'il y a des données à recevoir (non-bloquant)
                s.settimeout(1)  # Timeout court
                data = s.recv(1024)
                
                if data:
                    message_count += 1
                    msg = data.decode('utf-8', errors='ignore')
                    print(f"[{message_count}] Reçu: {msg[:50]}{'...' if len(msg) > 50 else ''}")
                    
                    # Répondre de manière appropriée
                    if msg == 'TEST':
                        s.send(b'OK')
                        print(f"[{message_count}] → Répondu: OK")
                    elif 'systeminfo' in msg:
                        response = "Modèle du système: Test Machine\nNom de l'hôte: TestClient"
                        s.send(response.encode())
                        print(f"[{message_count}] → Répondu: systeminfo")
                    elif 'mkdir' in msg:
                        s.send(b'Repertoire cree')
                        print(f"[{message_count}] → Répondu: mkdir")
                    elif msg == 'quit':
                        print("Reçu quit, fermeture...")
                        break
                    else:
                        s.send(b'Commande effectuee')
                        print(f"[{message_count}] → Répondu: Commande effectuee")
                
            except socket.timeout:
                # Pas de données reçues, c'est normal
                pass
            except Exception as e:
                print(f" Erreur: {e}")
                break
            
            # Envoyer un heartbeat toutes les 10 secondes
            current_time = time.time()
            if current_time - last_heartbeat >= 10:
                try:
                    s.send(b'HEARTBEAT')
                    heartbeat_count += 1
                    last_heartbeat = current_time
                    print(f"Heartbeat #{heartbeat_count} envoyé")
                except Exception as e:
                    print(f"[-] Erreur heartbeat: {e}")
                    break
        
        # Statistiques finales
        duration = time.time() - start_time
        print(f"\nStatistiques:")
        print(f"   - Durée de connexion: {duration:.1f} secondes")
        print(f"   - Messages reçus: {message_count}")
        print(f"   - Heartbeats envoyés: {heartbeat_count}")
        print(f"   - Connexion stable: {'[+] Oui' if duration > 50 else '[-] Non'}")
        
        s.close()
        print("[+] Connexion fermée proprement")
        
    except Exception as e:
        print(f"[-] Erreur de connexion: {e}")

# =============================================================================
# Fonction utilitaire pour surveiller les connexions réseau
# =============================================================================

def monitor_network():
    """Surveille les connexions réseau"""
    import subprocess
    
    print("\n=== Surveillance réseau ===")
    
    for i in range(12):  # 12 vérifications sur 60 secondes
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            connections = []
            
            for line in result.stdout.split('\n'):
                if '5001' in line and 'ESTABLISHED' in line:
                    connections.append(line.strip())
            
            print(f"[{i+1}/12] Connexions actives: {len(connections)}")
            
            time.sleep(5)
            
        except Exception as e:
            print(f"Erreur surveillance: {e}")
            break

# =============================================================================
# Fonction principale pour tester la connexion persistante
# =============================================================================

if __name__ == "__main__":
    print("[+] Test de connexion persistante simplifiée\n")
    
    # Lancer la surveillance en arrière-plan
    monitor_thread = threading.Thread(target=monitor_network, daemon=True)
    monitor_thread.start()
    
    # Test principal
    simple_persistent_test()
    
    print("\n[+] Test terminé") 