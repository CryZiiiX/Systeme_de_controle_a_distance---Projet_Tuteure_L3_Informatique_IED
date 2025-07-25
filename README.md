# Projet Tuteuré - Système de Contrôle à Distance

## 📋 Description

Ce projet implémente un système de contrôle à distance composé d'un serveur de commande et de clients agents. Il a été développé dans le cadre du cours "PROJET TUTEURE" L3 INFORMATIQUE IED.

**Auteur :** Maxime BRONNY  
**Version :** V1  
**Licence :** Projet académique IED

## 🏗️ Architecture du Projet

### FICHIER SERVEUR/
Contient tous les composants du serveur de contrôle :

- **`server.py`** - Serveur principal gérant les connexions TCP/IP avec les agents
- **`GUI.py`** - Interface graphique de gestion du serveur
- **`database_creation.py`** - Script de création et gestion de la base de données SQLite
- **`reset_system.py`** - Utilitaire de réinitialisation du système
- **`test_simple_connection.py`** - Tests de connexion
- **`templates/`** - Templates HTML pour l'interface web Flask
  - Interface de gestion des agents
  - Filtres et affichages
  - Pages d'exécution de commandes

### FICHIERS CLIENTS INVISIBLES/
Version invisible des agents clients :

- **`RamBooster.py`** - Agent client principal avec fonctionnalités de keylogging
- **`RamBooster.exe`** - Version compilée de l'agent
- **`setup_env.bat`** - Script de configuration de l'environnement
- **`RunInvisible.vbs`** - Script VBS pour exécution invisible
- **`script_extractsam.ps1`** - Script PowerShell d'extraction SAM
- **`extractsam.exe`** - Utilitaire d'extraction compilé

### FICHIERS CLIENTS VISIBLE & TESTS/
Version visible pour tests et développement (mêmes fichiers que la version invisible)

## 🚀 Fonctionnalités

### Serveur
- **Interface graphique** complète pour la gestion
- **API Flask** pour l'interface web
- **Base de données SQLite** pour le stockage des agents
- **Gestion multi-threading** pour connexions simultanées
- **Système d'authentification** et de sessions
- **Logs et monitoring** en temps réel

### Clients/Agents
- **Connexion TCP persistante** au serveur
- **Keylogger intégré** pour capture de frappes
- **Exécution de commandes** à distance
- **Mode invisible** pour déploiement discret
- **Auto-configuration** de l'environnement
- **Extraction de données système**

## 🛠️ Installation et Utilisation

### Prérequis
- Python 3.x
- Bibliothèques Python : `socket`, `flask`, `sqlite3`, `pynput`, `threading`
- Windows (pour les scripts .bat et .vbs)

### Lancement du Serveur
```bash
# Démarrer l'interface graphique du serveur
python3 GUI.py

# Ou directement le serveur
python3 server.py
```

### Déploiement des Agents
```bash
# Version visible (pour tests)
python3 RamBooster.py

# Version invisible (production)
# Exécuter RunInvisible.vbs ou RamBooster.exe
```

## 🔧 Configuration

Le serveur utilise une configuration réseau TCP/IP avec gestion automatique des ports et adresses IP. La base de données SQLite stocke :
- Informations des agents connectés
- Sessions actives
- Logs d'activité
- Commandes exécutées

## ⚠️ Avertissements

Ce projet est développé à des fins éducatives dans le cadre d'un projet tuteuré. L'utilisation de ce système doit respecter :
- Les lois locales sur la surveillance et la vie privée
- Les politiques de sécurité informatique
- L'autorisation explicite des utilisateurs surveillés

## 📁 Structure des Fichiers

```
PROGRAMMES FINAUX/
├── FICHIER SERVEUR/
│   ├── server.py
│   ├── GUI.py
│   ├── database_creation.py
│   ├── reset_system.py
│   ├── test_simple_connection.py
│   └── templates/
│       ├── agents.html
│       ├── agentsfiltre.html
│       ├── agentsfiltreaffichage.html
│       ├── agentsinfo.html
│       ├── allinone.html
│       ├── execute.html
│       ├── executefiltre.html
│       └── index.html
├── FICHIERS CLIENTS INVISIBLES/
│   ├── RamBooster.py
│   ├── RamBooster.exe
│   ├── setup_env.bat
│   ├── RunInvisible.vbs
│   ├── script_extractsam.ps1
│   ├── extractsam.exe
│   └── mon_icone.ico
└── FICHIERS CLIENTS VISIBLE & TESTS/
    ├── RamBooster.py
    ├── RamBooster.exe
    ├── setup_env.bat
    ├── RunInvisible.vbs
    ├── script_extractsam.ps1
    ├── extractsam.exe
    └── mon_icone.ico
```

## 🔍 Technologies Utilisées

- **Python 3** - Langage principal
- **Flask** - Framework web pour l'interface
- **SQLite** - Base de données
- **Socket** - Communication réseau TCP/IP
- **Threading** - Gestion des connexions multiples
- **pynput** - Capture des événements clavier
- **HTML/CSS** - Interface web
- **PowerShell/Batch** - Scripts système Windows
- **VBScript** - Exécution invisible

---

*Projet réalisé dans le cadre des études L3 Informatique IED* 