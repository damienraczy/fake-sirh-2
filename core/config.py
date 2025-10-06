# config.py
import yaml

CONFIG = None

def load_config(config_path: str):
    """
    Charge la configuration depuis le fichier YAML et la stocke dans une variable globale.
    """
    global CONFIG
    print("Chargement de la configuration...")
    # On force la relecture si un chemin est spécifié, sinon on utilise le cache
    if CONFIG is None or config_path != 'config.yaml':
        print(f"Lecture du fichier de configuration : {config_path}")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                CONFIG = yaml.safe_load(f)
            print("Configuration chargée avec succès.")
        except FileNotFoundError:
            print(f"Erreur: Le fichier de configuration '{config_path}' n'a pas été trouvé.")
            exit(1)
        except yaml.YAMLError as e:
            print(f"Erreur de syntaxe dans le fichier YAML: {e}")
            exit(1)
    print("Configuration déjà chargée, utilisation de la version en mémoire.")
    return CONFIG

def get_config():
    """
    Retourne la configuration chargée. Lance le chargement si ce n'est pas déjà fait.
    """
    global CONFIG
    # if CONFIG is None:
    #     return load_config(config_path)
    return CONFIG