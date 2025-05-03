# fine-tuning-app-backend/api/tasks.py

import time
import os
import logging
from celery import shared_task
from django.conf import settings
from .models import FineTuningJob, FineTuningJobStatus, AIModel, Dataset # Importez AIModel et Dataset

# Configuration du logger
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_fine_tuning_task(self, job_id):
    """Tâche Celery pour exécuter un job de fine-tuning."""
    try:
        # Utiliser select_related pour optimiser la récupération des objets liés
        job = FineTuningJob.objects.select_related("model", "dataset").get(id=job_id)
    except FineTuningJob.DoesNotExist:
        logger.error(f"FineTuningJob avec ID {job_id} non trouvé.")
        return f"Job {job_id} not found."

    # Mettre à jour le statut et sauvegarder l'ID de la tâche Celery
    job.status = FineTuningJobStatus.RUNNING
    job.celery_task_id = self.request.id
    job.error_message = None # Réinitialiser les erreurs précédentes
    job.save(update_fields=["status", "celery_task_id", "error_message", "updated_at"])

    logger.info(f"Démarrage du FineTuningJob {job_id} pour le modèle {job.model.name} et le dataset {job.dataset.name}.")
    logger.info(f"Hyperparamètres: {job.hyperparameters}")

    try:
        # --- Début de la logique de Fine-Tuning (Placeholder) ---
        # Récupérer les chemins des fichiers
        # Note: job.model.upload_path et job.dataset.upload_path sont des FieldFile
        # Pour obtenir le chemin absolu dans le conteneur:
        model_file_path = os.path.join(settings.MEDIA_ROOT, job.model.upload_path.name) if job.model.upload_path else None
        dataset_file_path = os.path.join(settings.MEDIA_ROOT, job.dataset.upload_path.name)

        # Vérifier l'existence des fichiers
        if not model_file_path or not os.path.exists(model_file_path):
             raise FileNotFoundError(f"Fichier modèle introuvable: {model_file_path}")
        if not os.path.exists(dataset_file_path):
             raise FileNotFoundError(f"Fichier dataset introuvable: {dataset_file_path}")

        # Récupérer les hyperparamètres avec des valeurs par défaut robustes
        lr = float(job.hyperparameters.get("lr", 1e-5))
        epochs = int(job.hyperparameters.get("epochs", 1))
        batch_size = int(job.hyperparameters.get("batch_size", 8))

        logger.info(f"Chemin modèle: {model_file_path}")
        logger.info(f"Chemin dataset: {dataset_file_path}")
        logger.info(f"Paramètres utilisés: lr={lr}, epochs={epochs}, batch_size={batch_size}")

        # *** Placeholder pour le script ML ***
        # Ici, vous intégreriez votre logique avec Hugging Face transformers, PyTorch, etc.
        # Exemple très simplifié :
        logger.info("Chargement du modèle et du tokenizer (simulation)...")
        # from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
        # model = AutoModelForSequenceClassification.from_pretrained(model_file_path)
        # tokenizer = AutoTokenizer.from_pretrained(model_file_path) # Ou un tokenizer compatible
        time.sleep(2)
        
        logger.info("Chargement et prétraitement du dataset (simulation)...")
        # Ici, lire le dataset (ex: CSV avec pandas), le tokeniser
        # import pandas as pd
        # df = pd.read_csv(dataset_file_path)
        # tokenized_datasets = ... # Utiliser tokenizer sur df['text_column']
        time.sleep(3)

        logger.info("Configuration de l'entraînement (simulation)...")
        # output_dir = os.path.join(settings.MEDIA_ROOT, 'fine_tuned_models', f'job_{job_id}')
        # os.makedirs(output_dir, exist_ok=True)
        # training_args = TrainingArguments(...)
        # trainer = Trainer(...)
        time.sleep(1)

        logger.info("Lancement de l'entraînement (simulation)...")
        # Simuler un temps d'entraînement
        total_sleep_time = 15
        for i in range(total_sleep_time):
            logger.info(f"Entraînement simulé... {i+1}/{total_sleep_time}s")
            time.sleep(1)
        # trainer.train() # Appel réel
        logger.info("Entraînement (simulation) terminé.")

        # Sauvegarde du modèle (simulation)
        # trainer.save_model(output_dir)
        output_model_relative_path = os.path.join("fine_tuned_models", f"job_{job_id}")
        # Simuler la création du dossier de sortie
        simulated_output_dir = os.path.join(settings.MEDIA_ROOT, output_model_relative_path)
        os.makedirs(simulated_output_dir, exist_ok=True)
        with open(os.path.join(simulated_output_dir, "model_fine_tuned.txt"), "w") as f:
            f.write(f"Modèle fine-tuné pour Job {job_id}")
        logger.info(f"Modèle sauvegardé (simulation) dans: {output_model_relative_path}")
        # --- Fin de la logique de Fine-Tuning (Placeholder) ---

        # Mise à jour du statut et sauvegarde du chemin de sortie
        job.status = FineTuningJobStatus.SUCCESS
        job.output_model_path = output_model_relative_path # Chemin relatif à MEDIA_ROOT
        job.error_message = None
        job.save(update_fields=["status", "output_model_path", "error_message", "updated_at"])
        logger.info(f"FineTuningJob {job_id} terminé avec succès.")
        return f"Job {job_id} completed successfully."

    except FileNotFoundError as e:
        logger.error(f"Erreur fichier pour Job {job_id}: {e}")
        job.status = FineTuningJobStatus.FAILED
        job.error_message = f"Erreur fichier: {e}"
        job.save(update_fields=["status", "error_message", "updated_at"])
        # Ne pas relancer pour une erreur de fichier manquant
        # raise self.reraise(exc=e, traceback=traceback) # Alternative
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de l'exécution du FineTuningJob {job_id}: {e}")
        job.status = FineTuningJobStatus.FAILED
        job.error_message = f"Erreur interne: {str(e)[:500]}..." # Tronquer les longs messages
        job.save(update_fields=["status", "error_message", "updated_at"])
        # Renvoyer l'exception pour que Celery marque la tâche comme échouée et potentiellement retente
        raise
