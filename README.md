
## Installation

### Installer UV

- Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
- Linux
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installer le projet

- Clone le repo 

```
git clone https://github.com/EFROBOT/robot-main.git
```
- Puis
```bash
cd efrobot
uv sync
```

## Utilisation

### Lancer le serveur

```bash
uv run start
```

### Commandes de développement

```bash
# Vérifier le code
uv run ruff check .

# Formater le code
uv run ruff format .
```


## Raspberry Pi

- Username : ````efrobot````
- Mot de passe : ````efrobot````
- IP : ````10.42.0.1````

## Info Projects

### Ports raspy

|GPIO| Fonction |
| ---|:---:|
|GPIO 17 | Switch |
|GPIO 17 | Switch gnd |
GPIO  | Servomoteur
GPIO x | 5v Servomoteur
GPIO x | gnd Servomoteur
GPIO 2 | Ficelle
GPIO 10 | data Bandeau Led
GPIO x | 5v Bandeau Led
GPIO x | gnd Bandeau Led


### CPU repartition 

|Coeur| Fonction |
| ---|:---:|
|0 | Lidar / Com with STM32 |
|1 | Camera  |
|2 | / |
|3 | Serveur |
