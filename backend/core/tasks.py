"""
Celery tasks for document processing

This module defines background tasks for OCR processing workflow:
- PDF to PNG conversion
- Image preprocessing
- OCR text recognition
- Text correction
- File generation
"""

from typing import Dict, Any, Optional
from celery import Celery
from celery import current_task
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Create Celery app (in production this would be configured with Redis/RabbitMQ)
celery_app = Celery('k_ocr_tasks')

# Basic configuration for testing
# NOTE: Disabling task_always_eager to allow proper async execution
celery_app.conf.update(
    broker_url='memory://',  # In-memory broker for testing
    result_backend='cache+memory://',  # In-memory result backend
    task_always_eager=False,  # Must be False for state updates to work
    task_eager_propagates=False,
)


@celery_app.task(bind=True, name='process_document')
def process_document(self, upload_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main document processing task

    Args:
        upload_id: ID of uploaded file
        options: Processing options (DPI, OCR engine, etc.)

    Returns:
        Dict containing processing results

    Raises:
        Exception: If processing fails
    """
    import time

    try:
        logger.info(f"Starting document processing for upload_id: {upload_id}")

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'initializing', 'progress': 0}
        )
        time.sleep(1)

        # Step 1: PDF to PNG conversion
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'converting_pdf', 'progress': 20}
        )
        time.sleep(1)

        # Step 2: Image preprocessing
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'preprocessing_images', 'progress': 40}
        )
        time.sleep(1)

        # Step 3: OCR processing
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'ocr_processing', 'progress': 60}
        )
        time.sleep(1)

        # Step 4: Text correction
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'text_correction', 'progress': 80}
        )
        time.sleep(1)

        # Step 5: File generation
        self.update_state(
            state='PROGRESS',
            meta={'current_step': 'generating_files', 'progress': 90}
        )
        time.sleep(1)

        # Task will automatically set state to SUCCESS when returning

        # Complete - return result to mark task as SUCCESS
        # NOTE: This is a placeholder. Actual processing should be implemented here.
        result = {
            'upload_id': upload_id,
            'text': 'Celery task completed but actual OCR processing not implemented.\nUse BackgroundTasks for actual processing.',
            'download_url': f'/api/download/{upload_id}',
            'pages': 0,
            'confidence': 0.0,
            'processing_time': 6.0,
            'options': options
        }

        logger.info(f"Document processing completed for upload_id: {upload_id}")

        return result

    except Exception as e:
        logger.error(f"Document processing failed for upload_id {upload_id}: {e}")
        logger.error(traceback.format_exc())

        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'upload_id': upload_id,
                'traceback': traceback.format_exc()
            }
        )

        raise e


@celery_app.task(bind=True, name='batch_process_documents')
def batch_process_documents(self, upload_ids: list, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Batch process multiple documents

    Args:
        upload_ids: List of upload IDs to process
        options: Processing options

    Returns:
        Dict containing batch processing results
    """
    try:
        logger.info(f"Starting batch processing for {len(upload_ids)} documents")

        results = []
        total_docs = len(upload_ids)

        for i, upload_id in enumerate(upload_ids):
            progress = int((i / total_docs) * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_step': f'processing_document_{i+1}_of_{total_docs}',
                    'progress': progress,
                    'completed': i,
                    'total': total_docs
                }
            )

            # Process individual document
            result = process_document.apply_async(
                args=[upload_id, options],
                task_id=f"batch_item_{upload_id}"
            ).get()

            results.append(result)

        batch_result = {
            'batch_id': self.request.id,
            'total_processed': len(results),
            'results': results,
            'success_count': len([r for r in results if 'error' not in r]),
            'failed_count': len([r for r in results if 'error' in r])
        }

        logger.info(f"Batch processing completed. Success: {batch_result['success_count']}, Failed: {batch_result['failed_count']}")

        return batch_result

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        logger.error(traceback.format_exc())

        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'upload_ids': upload_ids,
                'traceback': traceback.format_exc()
            }
        )

        raise e


def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get task result by task ID

    Args:
        task_id: Celery task ID

    Returns:
        Task result or None if not found
    """
    try:
        result = celery_app.AsyncResult(task_id)

        if result.state == 'PENDING':
            return {
                'state': 'PENDING',
                'progress': 0,
                'current_step': 'queued'
            }
        elif result.state == 'PROGRESS':
            return {
                'state': 'PROGRESS',
                **result.info
            }
        elif result.state == 'SUCCESS':
            return {
                'state': 'SUCCESS',
                'progress': 100,
                'result': result.result
            }
        elif result.state == 'FAILURE':
            return {
                'state': 'FAILURE',
                'error': str(result.info),
                'progress': 0
            }
        else:
            return {
                'state': result.state,
                'info': result.info
            }

    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        return None


def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task

    Args:
        task_id: Celery task ID

    Returns:
        True if cancelled successfully, False otherwise
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Task {task_id} cancelled")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return False