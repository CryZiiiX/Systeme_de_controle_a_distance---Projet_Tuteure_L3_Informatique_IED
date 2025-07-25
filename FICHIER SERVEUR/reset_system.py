#!/usr/bin/env python3

# /**********************************************************************************************************************************************************************************

# Nom du fichier : reset_system.py
# Rôle du fichier : Fichier gérant le nettoyage du système et le redémarrage propre.

# Auteur : Maxime BRONNY
# Version : V1
# Licence : Réalisé dans le cadre des cours "PROJET TUTEURE" L3 INFORMATIQUE IED
# Usage : python3 reset_system.py pour nettoyer le système et redémarrer proprement.

# *********************************************************************************************************************************************************************************/


# =============================================================================
# Importation des bibliothèques nécessaires
# =============================================================================

import sqlite3    # Pour gérer la base de données SQLite (nettoyage des tables Agents et Sessions)
import os         # Pour les opérations système (vérification de fichiers, suppression, etc.)
import subprocess # Pour exécuter des commandes système externes si besoin (optionnel pour des scripts ou commandes)
import psutil     # Pour gérer et tuer les processus Python existants (server.py, RamBooster_modifié.py, GUI.py)
import time       # Pour gérer les délais et temporisations (attente après l'arrêt des processus)
import sys        # Pour accéder aux arguments du script ou effectuer des opérations système avancées


# =============================================================================
# Fonction utilitaire pour arrêter les processus existants
# =============================================================================

def kill_existing_processes():
    """Tue tous les processus server.py et RamBooster_modifié.py existants"""
    print("=== Arrêt des processus existants ===")
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('server.py' in arg or 'RamBooster_modifié.py' in arg or 'GUI.py' in arg for arg in cmdline):
                print(f"Arrêt du processus {proc.info['pid']}: {' '.join(cmdline)}")
                proc.kill()
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_count > 0:
        print(f"[+] {killed_count} processus arrêtés")
        time.sleep(2)  # Attendre que les processus se terminent
    else:
        print("[+] Aucun processus à arrêter")

# =============================================================================
# Fonction utilitaire pour nettoyer la base de données
# =============================================================================

def clean_database():
    """Nettoie complètement la base de données"""
    print("\n=== Nettoyage de la base de données ===")
    
    if not os.path.exists('test.db'):
        print("[+] Aucune base de données à nettoyer")
        return
    
    try:
        conn = sqlite3.connect('test.db')
        cur = conn.cursor()
        
        # Supprimer tous les agents
        cur.execute("DELETE FROM Agents")
        agents_deleted = cur.rowcount
        
        # Supprimer toutes les sessions
        cur.execute("DELETE FROM Sessions")
        sessions_deleted = cur.rowcount
        
        # Réinitialiser les compteurs d'auto-increment
        cur.execute("DELETE FROM sqlite_sequence WHERE name='Agents'")
        
        conn.commit()
        conn.close()
        
        print(f"[+] Base nettoyée: {agents_deleted} agents, {sessions_deleted} sessions supprimés")
        
    except Exception as e:
        print(f"[-] Erreur lors du nettoyage de la base: {e}")

# =============================================================================
# Fonction utilitaire pour vérifier les ports
# =============================================================================

def check_ports():
    """Vérifie que les ports sont libres"""
    print("\n=== Vérification des ports ===")
    
    import socket
    
    ports_to_check = [5000, 5001]  # Flask et serveur socket
    
    for port in ports_to_check:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            
            if result == 0:
                print(f"[-]  Port {port} encore occupé")
            else:
                print(f"[+] Port {port} libre")
        except Exception as e:
            print(f"[-] Erreur de vérification du port {port}: {e}")

# =============================================================================
# Fonction utilitaire pour créer une base de données fraîche
# =============================================================================

def create_fresh_database():
    """Crée une base de données fraîche avec les bonnes tables"""
    print("\n=== Création d'une base fraîche ===")
    
    try:
        conn = sqlite3.connect('test.db')
        cur = conn.cursor()
        
        # Créer la table Agents si elle n'existe pas
        cur.execute('''CREATE TABLE IF NOT EXISTS Agents
                       (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Ip TEXT,
                        Hostname TEXT,
                        Username TEXT,
                        OS TEXT,
                        State TEXT,
                        Info TEXT)''')
        
        # Créer la table Sessions si elle n'existe pas
        cur.execute('''CREATE TABLE IF NOT EXISTS Sessions
                       (session_id TEXT PRIMARY KEY,
                        agent_id INTEGER,
                        ip_address TEXT,
                        machine_id TEXT,
                        created_at TIMESTAMP,
                        last_activity TIMESTAMP,
                        FOREIGN KEY (agent_id) REFERENCES Agents(ID))''')
        
        conn.commit()
        conn.close()
        
        print("[+] Base de données fraîche créée")
        
    except Exception as e:
        print(f"[-] Erreur lors de la création de la base: {e}")

# =============================================================================
# Fonction principale de nettoyage
# =============================================================================

def main():
    """Fonction principale de nettoyage"""
    print("[+] Nettoyage complet du système Client-Serveur\n")
    
    # Étape 1: Arrêter tous les processus
    kill_existing_processes()
    
    # Étape 2: Nettoyer la base de données
    clean_database()
    
    # Étape 3: Vérifier les ports
    check_ports()
    
    # Étape 4: Créer une base fraîche
    create_fresh_database()
    
    print("\n[+] Nettoyage terminé!")
    print("\nPour redémarrer le système:")
    print("1. Terminal 1: python3 GUI.py")
    print("2. Terminal 2: python3 RamBooster_modifié.py")
    print("3. Ou utilisez: python3 test_single_connection.py pour tester")

if __name__ == "__main__":
    main() 