# Zabbix Catalog Generator

Générateur de catalogues de supervision Excel à partir de templates Zabbix exportés au format YAML.

## Périmètre de la V1

La V1 traite uniquement les sondes actives, c'est-à-dire les éléments dont le statut Zabbix est `ENABLED` :

- items actifs ;
- règles de découverte LLD actives ;
- prototypes d'items actifs appartenant à une règle LLD active ;
- déclencheurs actifs rattachés aux items et prototypes d'items.

Le filtrage porte sur le statut de l'élément et non sur son type de collecte. Les items `ZABBIX_ACTIVE`, `DEPENDENT`, `CALCULATED` ou d'autres types sont donc conservés dès lors qu'ils sont activés dans le template.

Les éléments désactivés sont ignorés à tous les niveaux. Lorsqu'une sonde possède plusieurs déclencheurs actifs, une ligne est créée pour chaque déclencheur afin de respecter la structure du modèle de catalogue.

## Installation sous Windows avec le package Wheel

Prérequis : Python 3.10 ou supérieur doit être installé et accessible depuis PowerShell.

Installation du package fourni :

```powershell
py -m pip install .\zabbix_catalog_generator-0.2.0-py3-none-any.whl
```

Vérification :

```powershell
zabbix-catalog --version
zabbix-catalog --help
```

Mise à jour vers une nouvelle version :

```powershell
py -m pip install --upgrade .\zabbix_catalog_generator-0.3.0-py3-none-any.whl
```

Désinstallation :

```powershell
py -m pip uninstall zabbix-catalog-generator
```

## Installation pour le développement

Sous Windows :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

Sous Linux ou WSL :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Utilisation

Sous PowerShell :

```powershell
zabbix-catalog "EFS- Oracle by Zabbix agent 2 - Qualif.yaml" `
  --model "Modele_Catalogue_Supervision.xlsx" `
  --output "Catalogue_Oracle.xlsx"
```

Sous Linux ou WSL :

```bash
zabbix-catalog "EFS- Oracle by Zabbix agent 2 - Qualif.yaml" \
  --model "Modele_Catalogue_Supervision.xlsx" \
  --output "Catalogue_Oracle.xlsx"
```

La feuille active du modèle est utilisée par défaut. Une autre feuille peut être choisie avec `--sheet`.

## Données alimentées

Le générateur recherche les colonnes du modèle par leur intitulé et remplit notamment :

- nom de la politique ;
- méthode de collecte ;
- propriété et type de ressource ;
- indicateur LLD ;
- ressource, clé, description et fréquence ;
- nom, expression et sévérité du déclencheur ;
- rétention de l'historique et des tendances.

Le modèle d'origine est copié, sa mise en forme est conservée et ses anciennes lignes de données sont remplacées.

## Construction du package

Depuis l'environnement de développement :

```bash
python -m build
```

ou avec `uv` :

```bash
uv build
```

Les livrables sont créés dans le dossier `dist/` :

```text
dist/
├── zabbix_catalog_generator-0.2.0-py3-none-any.whl
└── zabbix_catalog_generator-0.2.0.tar.gz
```

Contrôle du package avant distribution :

```bash
python -m twine check dist/*
```

## Développement

```bash
pytest
ruff check .
```

La pull request et les branches `agent/**` exécutent automatiquement Ruff et Pytest avec GitHub Actions.
