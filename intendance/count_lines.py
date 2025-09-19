import os
from collections import defaultdict

def count_lines_by_extension(directory="."):
    """
    Parcourt un répertoire et compte le nombre de lignes pour chaque extension de fichier.

    Args:
        directory (str): Le chemin du répertoire à analyser. Par défaut, le répertoire courant.
    """
    line_counts = defaultdict(int)
    file_counts = defaultdict(int)

    print(f"Analyse des fichiers dans le répertoire '{os.path.abspath(directory)}'...")

    # os.walk parcourt récursivement tous les sous-dossiers et fichiers
    for root, _, files in os.walk(directory):
        # Ignorer les répertoires cachés comme .git
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue

        for file in files:
            # Obtenir l'extension du fichier
            _, extension = os.path.splitext(file)

            # Ignorer les fichiers sans extension
            if not extension:
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Compter les lignes et les ajouter au total pour cette extension
                    num_lines = sum(1 for line in f)
                    line_counts[extension] += num_lines
                    file_counts[extension] += 1
            except Exception as e:
                print(f"  - Impossible de lire le fichier {file_path}: {e}")

    return line_counts, file_counts

def print_results(line_counts, file_counts):
    """Affiche les résultats dans un tableau formaté."""
    if not line_counts:
        print("Aucun fichier avec extension n'a été trouvé.")
        return

    print("\n" + "="*45)
    print(f"{'Extension':<15} | {'Nombre de fichiers':<20} | {'Total de lignes'}")
    print("-"*45)

    # Trier les résultats par nombre de lignes, du plus grand au plus petit
    sorted_extensions = sorted(line_counts.items(), key=lambda item: item[1], reverse=True)

    total_lines = 0
    total_files = 0
    for extension, count in sorted_extensions:
        num_files = file_counts[extension]
        print(f"{extension:<15} | {num_files:<20} | {count}")
        total_lines += count
        total_files += num_files
    
    print("-"*45)
    print(f"{'TOTAL':<15} | {total_files:<20} | {total_lines}")
    print("="*45)

if __name__ == "__main__":
    # Exécuter l'analyse depuis le répertoire où se trouve le script
    counts, files = count_lines_by_extension()
    print_results(counts, files)
