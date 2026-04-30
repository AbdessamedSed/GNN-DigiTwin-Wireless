#!/bin/bash
#SBATCH --job-name=Simu5G_All
#SBATCH --partition=main
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/home/%u/logs/%j.out
#SBATCH --error=/home/%u/logs/%j.err

cd /home/abdessamedseddiki/omnet/FiveG_network/simulations


# Lancer le script python
echo "Démarrage de l'automatisation des simulations..."
python3 master_script.py
