# fine-tuning-app-backend/api/tasks.py

import os
import logging
import pandas as pd
import zipfile
import shutil
from celery import shared_task
from django.conf import settings
from django.db import transaction
from .models import FineTuningJob, FineTuningJobStatus

# Imports pour le Machine Learning
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset as HFDataset, load_dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import torch

# Configuration du logger
logger = logging.getLogger(__name__)


def compute_metrics(pred):
    """Calcule les métriques pour l'évaluation."""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    acc = accuracy_score(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }

# Fonction de template pour formater les données


def decompress_and_flatten_model_if_needed(model_instance):
    """
    Vérifie si le modèle est un .zip. Si oui, le décompresse,
    aplatit la structure si nécessaire, met à jour le chemin en BDD
    et retourne le chemin du dossier. Sinon, retourne le chemin existant.
    """
    model_path_rel = model_instance.upload_path
    if not model_path_rel or not model_path_rel.name.lower().endswith('.zip'):
        # Ce n'est pas un zip, on retourne le chemin du dossier tel quel
        return os.path.join(settings.MEDIA_ROOT, model_path_rel.name)

    logger.info(f"Décompression du modèle zip: {model_path_rel.name}")
    zip_path_abs = os.path.join(settings.MEDIA_ROOT, model_path_rel.name)
    
    # Définir le répertoire de destination final
    final_dir_rel = os.path.splitext(model_path_rel.name)[0]
    final_dir_abs = os.path.join(settings.MEDIA_ROOT, final_dir_rel)

    # Utiliser un dossier temporaire pour l'extraction
    temp_extraction_dir = f"{final_dir_abs}_temp"
    if os.path.exists(temp_extraction_dir):
        shutil.rmtree(temp_extraction_dir)
    os.makedirs(temp_extraction_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path_abs, 'r') as zip_ref:
            zip_ref.extractall(temp_extraction_dir)

        # Logique d'aplatissement
        items_in_temp = os.listdir(temp_extraction_dir)
        source_dir_to_move = temp_extraction_dir
        if len(items_in_temp) == 1 and os.path.isdir(os.path.join(temp_extraction_dir, items_in_temp[0])):
            source_dir_to_move = os.path.join(temp_extraction_dir, items_in_temp[0])
        
        # Déplacer le contenu vers la destination finale
        if os.path.exists(final_dir_abs):
            shutil.rmtree(final_dir_abs)
        shutil.copytree(source_dir_to_move, final_dir_abs)
        
        # Mettre à jour la BDD pour pointer vers le nouveau dossier
        model_instance.upload_path.name = final_dir_rel
        model_instance.save(update_fields=['upload_path'])
        
        # Nettoyage
        shutil.rmtree(temp_extraction_dir)
        os.remove(zip_path_abs)

        logger.info(f"Décompression réussie. Nouveau chemin: {final_dir_abs}")
        return final_dir_abs

    except Exception as e:
        logger.error(f"Erreur lors de la décompression: {e}")
        # Nettoyage en cas d'erreur
        if os.path.exists(temp_extraction_dir):
            shutil.rmtree(temp_extraction_dir)
        raise  # Propager l'erreur pour que le job échoue


@shared_task(bind=True)
def run_fine_tuning_task(self, job_id, model_pk, dataset_pk):
    """
    Tâche Celery pour exécuter un job de fine-tuning.
    Reçoit maintenant les PKs pour récupérer les objets frais.
    """
    job = None  # S'assurer que job est défini
    try:
        # Utiliser transaction.atomic pour s'assurer que les opérations sur la BDD sont sûres
        with transaction.atomic():
            # On récupère tous les objets nécessaires au début
            job = FineTuningJob.objects.select_related('model', 'dataset').get(pk=job_id)
            
            # VÉRIFICATIONS DE ROBUSTESSE
            if not job.model:
                raise ValueError(f"Job {job_id} n'est pas lié à un modèle.")
            if not job.dataset:
                raise ValueError(f"Job {job_id} n'est pas lié à un dataset.")
            if not job.model.path:
                raise ValueError(f"Le modèle '{job.model.name}' (ID: {job.model.id}) n'a pas de chemin de fichier associé.")
            if not job.dataset.upload_path:
                raise ValueError(f"Le Dataset '{job.dataset.name}' (ID: {job.dataset.id}) n'a pas de chemin de fichier associé.")

            model_instance = job.model
            dataset_instance = job.dataset

            job.celery_task_id = self.request.id
            job.status = FineTuningJobStatus.RUNNING
            job.save(update_fields=['celery_task_id', 'status'])

        # --- Début de la logique de fine-tuning ---
        
        # ÉTAPE 1: Décompresser le modèle si nécessaire
        # model_instance.path devrait déjà pointer vers le répertoire décompressé
        # configuré par AIModelViewSet lors de l'upload.
        model_path = model_instance.path 
        if not os.path.isdir(model_path):
            # Sécurité : Vérifier si le chemin est absolu et existe
            # AIModel.path est stocké comme un chemin absolu.
            logger.error(f"Le chemin du modèle '{model_path}' pour AIModel ID {model_instance.id} n'est pas un répertoire valide ou n'existe pas.")
            raise ValueError(f"Chemin du modèle invalide pour AIModel ID {model_instance.id}")
        
        # Construire le chemin du dataset de manière sécurisée
        dataset_upload_path = dataset_instance.upload_path
        if not dataset_upload_path:
            raise ValueError("Le chemin du dataset est manquant dans le job.")
        dataset_path = os.path.join(settings.MEDIA_ROOT, dataset_upload_path.name)
        
        # 2. Chargement du dataset
        logger.info(f"Chargement du dataset depuis: {dataset_path}")
        file_extension = os.path.splitext(dataset_path)[1].lower()

        if file_extension == '.jsonl':
            raw_dataset = load_dataset('json', data_files=dataset_path)
        elif file_extension == '.csv':
            raw_dataset = load_dataset('csv', data_files=dataset_path)
        else:
            raise TypeError(f"Type de fichier non supporté '{file_extension}'. Utilisez .csv ou .jsonl.")

        print(f"DEBUG: Colonnes dans raw_dataset APRES load_dataset: {raw_dataset.column_names}", flush=True)
        
        # Déterminer le split à utiliser
        dataset_to_process = raw_dataset['train'] if 'train' in raw_dataset else raw_dataset

        # 3. Détecter le nombre de labels et configurer le modèle en conséquence
        label_column = 'label'
        if label_column not in dataset_to_process.column_names:
            raise ValueError(f"La colonne '{label_column}' est introuvable. Colonnes disponibles: {dataset_to_process.column_names}")
        
        unique_labels = dataset_to_process.unique(label_column)
        num_labels = len(unique_labels)
        logger.info(f"Nombre de labels uniques détectés: {num_labels}. Labels: {unique_labels}")

        # 4. Chargement du tokenizer et du modèle
        logger.info(f"Chargement du tokenizer depuis: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        logger.info(f"Chargement du modèle pour la classification de séquences depuis: {model_path}")
        model = AutoModelForSequenceClassification.from_pretrained(model_path, num_labels=num_labels)

        # Configurer le pad_token APRÈS avoir chargé le tokenizer et le modèle
        if tokenizer.pad_token is None:
            logger.warning("Le pad_token n'est pas défini. Utilisation de eos_token comme pad_token.")
            tokenizer.pad_token = tokenizer.eos_token
            model.config.pad_token_id = tokenizer.pad_token_id

        # 5. Prétraitement et tokenisation
        def preprocess_function(examples):
            tokenized_batch = tokenizer(examples['text'], truncation=True, padding='max_length', max_length=256)
            tokenized_batch['labels'] = examples['label']
            return tokenized_batch

        logger.info("Tokenisation du dataset...")
        print(f"DEBUG: Colonnes dans dataset_to_process AVANT .map(): {dataset_to_process.column_names}", flush=True)
        tokenized_dataset = dataset_to_process.map(preprocess_function, batched=True)
        
        # 6. Configuration de l'entraîneur (Trainer)
        output_dir = os.path.join(settings.MEDIA_ROOT, 'models', f"{job.model.name}-finetuned-{job.id}")
        
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=job.hyperparameters.get('num_train_epochs', 3),
            per_device_train_batch_size=job.hyperparameters.get('batch_size', 2),
            logging_dir=f"{output_dir}/logs",
            logging_steps=1, # Logguer à chaque étape pour un meilleur suivi
            learning_rate=job.hyperparameters.get('learning_rate', 5e-5),
            weight_decay=0.01,
            warmup_steps=10,
            save_strategy="epoch",
            load_best_model_at_end=False,
            report_to="none",
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
        )
        
        # 7. Démarrage de l'entraînement
        logger.info("Début de l'entraînement...")
        trainer.train()
        logger.info("Entraînement terminé.")
        
        # 7. Sauvegarde du modèle final
        logger.info(f"Sauvegarde du modèle dans: {output_dir}")
        trainer.save_model(output_dir)

        # 8. Mise à jour finale du statut en cas de succès
        with transaction.atomic():
            job.output_model_path = output_dir
            job.status = FineTuningJobStatus.SUCCESS
            job.save(update_fields=['output_model_path', 'status'])
            
    except Exception as e:
        # En cas d'erreur, mettre à jour le statut et enregistrer le message d'erreur
        try:
            with transaction.atomic():
                job = FineTuningJob.objects.select_for_update().get(pk=job_id)
                job.status = FineTuningJobStatus.FAILED
                job.error_message = str(e)
                job.save(update_fields=['status', 'error_message'])
        except FineTuningJob.DoesNotExist:
            # Si le job n'existe plus, on ne peut rien faire
            logger.warning(f"Le job {job_id} n'a pas pu être trouvé pour marquer l'échec.")
            pass
        
        # Renvoyer l'exception pour que Celery la marque comme FAILED
        raise e
