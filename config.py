# config.py
import yaml

CONFIG = None

def load_config(config_path='gen_data.yaml'):
    """
    Charge la configuration depuis le fichier YAML et la stocke dans une variable globale.
    """
    global CONFIG
    print("Chargement de la configuration...")
    if CONFIG is None:
        print("Première fois, lecture du fichier de configuration.")
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
    if CONFIG is None:
        return load_config()
    return CONFIG