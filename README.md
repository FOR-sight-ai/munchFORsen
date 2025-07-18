# Proxy Server

[![Build Executables](https://github.com/VOTRE-USERNAME/VOTRE-REPO/actions/workflows/build-executables.yml/badge.svg)](https://github.com/VOTRE-USERNAME/VOTRE-REPO/actions/workflows/build-executables.yml)
[![Latest Release](https://img.shields.io/github/v/release/VOTRE-USERNAME/VOTRE-REPO)](https://github.com/VOTRE-USERNAME/VOTRE-REPO/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/VOTRE-USERNAME/VOTRE-REPO/total)](https://github.com/VOTRE-USERNAME/VOTRE-REPO/releases)

Un serveur proxy FastAPI pour les requêtes HTTP avec logging et replay de requêtes.

## Fonctionnalités

- Proxy HTTP avec FastAPI
- Logging automatique des requêtes
- Replay de requêtes depuis les logs
- Support pour la modification des headers et URL cibles

## Installation

### Développement

```bash
# Cloner le dépôt
git clone <votre-repo>
cd proxy

# Installer les dépendances avec UV
uv sync

# Lancer le serveur
uv run uvicorn proxy:app --reload
```

### Exécutables pré-compilés

Des exécutables sont automatiquement générés à **chaque commit sur la branche main** via GitHub Actions :

1. Allez dans la section [Releases](../../releases)
2. La dernière release contient les exécutables pour votre plateforme :
   - `proxy-vX.X.X-windows.exe` pour Windows  
   - `proxy-vX.X.X-macos` pour macOS

#### 🚀 Téléchargement automatique

**Script rapide (recommandé) :**
```bash
# macOS/Linux
curl -s https://raw.githubusercontent.com/VOTRE-USERNAME/VOTRE-REPO/main/download-latest.sh | bash

# Windows (PowerShell)
iwr https://raw.githubusercontent.com/VOTRE-USERNAME/VOTRE-REPO/main/download-latest.ps1 | iex
```

**Téléchargement manuel :**
```bash
# macOS/Linux  
./download-latest.sh

# Windows
.\download-latest.ps1
```

## Construction locale

### Prérequis

- Python 3.12+
- UV (gestionnaire de paquets)

### Construire l'exécutable

**Sur macOS/Linux :**
```bash
./build.sh
```

**Sur Windows :**
```cmd
build.bat
```

Ou manuellement :
```bash
uv add pyinstaller
uv run pyinstaller proxy.spec
```

L'exécutable sera créé dans le dossier `dist/`.

## Utilisation

### Lancer le serveur

```bash
# Avec Python
uv run uvicorn proxy:app --host 0.0.0.0 --port 8000

# Avec l'exécutable
./dist/proxy --host 0.0.0.0 --port 8000
```

### Configuration

- **URL cible par défaut** : `https://openrouter.ai/api/v1/chat/completions`
- **Port par défaut** : 8000
- **Logs** : Sauvegardés dans le dossier `logs/`

### Endpoints

- `POST /chat/completions` - Proxy vers l'URL cible
- `GET /replay/{filename}` - Rejouer une requête depuis les logs

## CI/CD

Le projet utilise GitHub Actions pour :

1. **Build automatique** : Construction d'exécutables à **chaque commit sur main**
2. **Versioning automatique** : Numéro de version basé sur le nombre de commits (`v1.0.XXX`)
3. **Tests** : Vérification que les exécutables fonctionnent
4. **Releases automatiques** : Publication automatique avec liens de téléchargement
5. **Nettoyage automatique** : Conservation des 10 dernières releases seulement

### 🔄 Processus de release automatique

À chaque `git push` sur la branche `main` :
1. ✅ Compilation pour Windows et macOS
2. ✅ Tests des exécutables  
3. ✅ Création d'une release `v1.0.XXX` (XXX = numéro de commit)
4. ✅ Publication avec liens de téléchargement directs
5. ✅ Nettoyage des anciennes releases

**Aucune action manuelle requise !** 🎉

## Structure du projet

```
proxy/
├── proxy.py                   # Code principal
├── proxy.spec                 # Configuration PyInstaller
├── pyproject.toml             # Configuration UV/Python
├── build.sh                   # Script de build (macOS/Linux)
├── build.bat                  # Script de build (Windows)
├── clean.sh                   # Script de nettoyage (macOS/Linux)
├── clean.bat                  # Script de nettoyage (Windows)
├── download-latest.sh         # Téléchargement auto (macOS/Linux)
├── download-latest.ps1        # Téléchargement auto (Windows)
├── logs/                      # Logs des requêtes
└── .github/
    └── workflows/
        └── build-executables.yml  # GitHub Actions
```

## Développement

### Ajouter des dépendances

```bash
uv add <package>
```

### Tester localement

```bash
# Lancer les tests
uv run pytest

# Lancer le serveur en mode développement
uv run uvicorn proxy:app --reload
```

## Troubleshooting

### Problèmes de construction

1. **PyInstaller manquant** : Exécutez `uv add pyinstaller`
2. **Dépendances manquantes** : Vérifiez le fichier `proxy.spec`
3. **Erreur de permissions** : Rendez le script exécutable avec `chmod +x build.sh`

### Problèmes d'exécution

1. **Port déjà utilisé** : Changez le port avec `--port <autre-port>`
2. **Logs non créés** : Vérifiez les permissions du dossier `logs/`

## License

[Votre license ici]
