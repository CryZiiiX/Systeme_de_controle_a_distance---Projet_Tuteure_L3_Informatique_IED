# /**********************************************************************************************************************************************************************************

# Nom du fichier : database_creation.py
# Rôle du fichier : Fichier gérant la création de la base de données.

# Auteur : Maxime BRONNY
# Version : V1
# Licence : Réalisé dans le cadre des cours "PROJET TUTEURE" L3 INFORMATIQUE IED
# Usage : python3 database_creation.py pour créer la base de données.

# *********************************************************************************************************************************************************************************/


# =============================================================================
# Importation des bibliothèques nécessaires
# =============================================================================

import sqlite3  # Pour la gestion de la base de données SQLite
import os       # Pour les opérations système (vérification de fichiers, etc.)


# =============================================================================
# Connexion à la base de données (elle sera créée si elle n'existe pas)
# =============================================================================

con = sqlite3.connect('test.db', check_same_thread=False)

cur = con.cursor()

# =============================================================================
# Création de la table Agents
# =============================================================================

cur.execute('''
CREATE TABLE IF NOT EXISTS Agents (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Ip TEXT NOT NULL,
    Hostname TEXT NOT NULL,
    Username TEXT NOT NULL,
    Info TEXT,
    OS TEXT NOT NULL,
    State TEXT NOT NULL,
    LastSeen TEXT
)
''')

# =============================================================================
# Sauvegarde et fermeture
# =============================================================================

con.commit()
con.close()

print("Base de données et table 'Agents' crées avec succès !")
