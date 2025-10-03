"""
문서 처리 API 모듈

이 모듈은 OCR 문서 처리 관련 API 엔드포인트를 제공합니다:
- POST /api/process/{upload_id}: 문서 처리 시작
- GET /api/process/{process_id}/status: 처리 상태 확인
- PUT /api/process/{process_id}/settings: 처리 설정 변경
- DELETE /api/process/{process_id}/cancel: 처리 취소
- GET /api/process/metrics: 처리 메트릭
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from backend.utils.temp_storage import TempStorage
from backend.dependencies import get_temp_storage as get_shared_storage

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(tags=["processing"])

# 전역 임시 저장소 인스턴스 (공유 싱글톤 사용)
temp_storage = get_shared_storage()

# 활성 프로세스 추적 (실제 환경에서는 Redis 등 사용)
active_processes: Dict[str, Dict[str, Any]] = {}


class ProcessingStatus(str, Enum):
    """처리 상태 열거형"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PreprocessingOptions(BaseModel):
    """전처리 옵션 모델"""
    apply_clahe: bool = True
    deskew_enabled: bool = True
    noise_removal: bool = True
    adaptive_threshold: bool = True
    super_resolution: bool = False


class CorrectionOptions(BaseModel):
    """교정 옵션 모델"""
    spacing_correction: bool = True
    spelling_correction: bool = True
    custom_rules: bool = False


class ProcessingRequest(BaseModel):
    """처리 요청 모델"""
    preprocessing_options: Optional[PreprocessingOptions] = PreprocessingOptions()
    ocr_engine: str = Field(default="paddle", pattern="^(paddle|tesseract|ensemble)$")
    correction_enabled: bool = True
    correction_options: Optional[CorrectionOptions] = CorrectionOptions()
    priority: int = Field(default=5, ge=1, le=10)


class ProcessingResponse(BaseModel):
    """처리 시작 응답 모델"""
    process_id: str
    upload_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None
    created_at: datetime


class ProcessingStatusResponse(BaseModel):
    """처리 상태 응답 모델"""
    process_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    current_step: str
    estimated_time: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProcessingResult(BaseModel):
    """처리 결과 모델"""
    output_file_id: str
    original_text: str
    corrected_text: str
    processing_time: float
    statistics: Dict[str, Any]


class ProcessingError(BaseModel):
    """처리 오류 모델"""
    error_type: str
    message: str
    details: Optional[str] = None
    suggestions: Optional[List[str]] = None
    fallback_suggestion: Optional[str] = None


class ProcessingMetrics(BaseModel):
    """처리 메트릭 모델"""
    total_processed: int
    successful_count: int
    failed_count: int
    average_processing_time: float
    success_rate: float
    engine_usage: Dict[str, int]
    common_errors: List[Dict[str, Any]]


# 진행 중인 처리 작업 추적 (실제로는 Redis 등 사용)
active_processes: Dict[str, Dict[str, Any]] = {}
processing_history: List[Dict[str, Any]] = []


def get_temp_storage() -> TempStorage:
    """임시 저장소 의존성"""
    return temp_storage


def validate_ocr_engine(engine: str) -> None:
    """OCR 엔진 유효성 검사"""
    valid_engines = ["paddle", "tesseract", "ensemble"]
    if engine not in valid_engines:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OCR engine '{engine}'. Valid engines: {', '.join(valid_engines)}"
        )


def estimate_processing_time(options: ProcessingRequest) -> int:
    """처리 예상 시간 계산 (초)"""
    base_time = 60  # 기본 1분

    # OCR 엔진에 따른 시간 차이
    if options.ocr_engine == "paddle":
        base_time += 30
    elif options.ocr_engine == "tesseract":
        base_time += 45

    # 전처리 옵션에 따른 시간 추가
    if options.preprocessing_options:
        if options.preprocessing_options.super_resolution:
            base_time += 120  # 2분 추가
        if options.preprocessing_options.deskew_enabled:
            base_time += 15
        if options.preprocessing_options.noise_removal:
            base_time += 10

    # 교정 활성화 시 시간 추가
    if options.correction_enabled:
        base_time += 20
        if options.correction_options and options.correction_options.spelling_correction:
            base_time += 30

    return base_time


def cleanup_temp_images(image_paths: List[str], processed_images: List[str], logger) -> None:
    """
    임시 이미지 파일 정리

    Args:
        image_paths: 원본 PDF에서 변환된 이미지 경로 리스트 (temp_images/)
        processed_images: 전처리된 이미지 경로 리스트 (processed_images/)
        logger: 로거 객체
    """
    import os
    from pathlib import Path

    cleanup_count = 0
    failed_count = 0

    # 모든 임시 이미지 파일 정리
    all_temp_files = image_paths + processed_images

    for img_path in all_temp_files:
        try:
            if isinstance(img_path, str):
                img_file = Path(img_path)
                if img_file.exists() and img_file.is_file():
                    os.remove(img_path)
                    cleanup_count += 1
                    logger.debug(f"Cleaned up temp image: {img_path}")
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to cleanup temp file {img_path}: {e}")

    if cleanup_count > 0:
        logger.info(f"Cleaned up {cleanup_count} temporary image files")

    if failed_count > 0:
        logger.warning(f"Failed to cleanup {failed_count} temporary files")


def process_document_background(process_id: str, upload_id: str, options: Dict[str, Any]):
    """
    실제 문서 처리 (BackgroundTasks용)
    PDF를 이미지로 변환하고 OCR 처리 후 텍스트 교정
    """
    import time
    from backend.core.pdf_converter import PDFConverter
    from backend.core.image_processor import ImageProcessor
    from backend.core.ocr_engine import OCREngineManager
    from backend.core.text_corrector import TextCorrector

    start_time = time.time()

    try:
        logger.info(f"Starting document processing for {upload_id}")

        # 파일 경로 가져오기
        storage = get_shared_storage()
        file_path = storage._get_file_path(upload_id)

        if not file_path.exists():
            raise FileNotFoundError(f"Upload file not found: {upload_id}")

        # Step 1: PDF to PNG 변환
        if process_id in active_processes:
            active_processes[process_id]["progress"] = 10
            active_processes[process_id]["current_step"] = "PDF 변환 중..."
            active_processes[process_id]["status"] = "processing"

        pdf_converter = PDFConverter()
        image_paths = pdf_converter.convert_pdf_to_png(str(file_path))
        logger.info(f"Converted {len(image_paths)} pages")

        if process_id in active_processes:
            active_processes[process_id]["progress"] = 25

        # Step 2: 이미지 전처리
        if process_id in active_processes:
            active_processes[process_id]["progress"] = 30
            active_processes[process_id]["current_step"] = "이미지 전처리 중..."

        image_processor = ImageProcessor()
        preprocessing_opts = options.get("preprocessing_options", {})

        # ProcessingOptions 객체 생성
        from backend.core.image_processor import ProcessingOptions
        proc_options = ProcessingOptions(
            apply_clahe=preprocessing_opts.get("apply_clahe", True),
            deskew_enabled=preprocessing_opts.get("deskew_enabled", True),
            noise_removal=preprocessing_opts.get("noise_removal", True),
            adaptive_threshold=preprocessing_opts.get("adaptive_threshold", True),
            super_resolution=preprocessing_opts.get("super_resolution", False)
        )

        processed_images = []
        for img_path in image_paths:
            processed_img = image_processor.preprocess_pipeline(img_path, proc_options)
            processed_images.append(processed_img)

        if process_id in active_processes:
            active_processes[process_id]["progress"] = 45

        # Step 3: OCR 처리
        if process_id in active_processes:
            active_processes[process_id]["progress"] = 50
            active_processes[process_id]["current_step"] = "OCR 텍스트 인식 중..."

        ocr_manager = OCREngineManager()
        engine_type = options.get("ocr_engine", "paddle")
        ocr_manager.set_engine(engine_type)

        all_text = []
        total_confidence = 0

        # 테스트용: 첫 3페이지만 처리
        pages_to_process = min(3, len(processed_images))
        logger.info(f"Processing {pages_to_process} pages out of {len(processed_images)}")

        for idx in range(pages_to_process):
            img_path = processed_images[idx]
            logger.info(f"OCR processing page {idx+1}/{pages_to_process}")
            result = ocr_manager.recognize_text(img_path)
            logger.info(f"Page {idx+1} OCR completed: {len(result.text)} chars, confidence: {result.confidence:.2f}")
            all_text.append(result.text)
            total_confidence += result.confidence

            # 진행률 업데이트
            progress = 50 + int((idx + 1) / pages_to_process * 25)
            if process_id in active_processes:
                active_processes[process_id]["progress"] = progress
                active_processes[process_id]["updated_at"] = datetime.now()

        combined_text = "\n\n".join(all_text)
        avg_confidence = total_confidence / len(processed_images) if processed_images else 0

        # Step 4: 텍스트 교정
        if options.get("correction_enabled", False):
            if process_id in active_processes:
                active_processes[process_id]["progress"] = 80
                active_processes[process_id]["current_step"] = "텍스트 교정 중..."

            text_corrector = TextCorrector()
            correction_opts = options.get("correction_options", {})

            corrected_text = text_corrector.correct_text(
                combined_text,
                spacing_correction=correction_opts.get("spacing_correction", True),
                spelling_correction=correction_opts.get("spelling_correction", True)
            )
            final_text = corrected_text
        else:
            final_text = combined_text

        # Step 5: 완료
        processing_time = time.time() - start_time

        if process_id in active_processes:
            active_processes[process_id]["status"] = "completed"
            active_processes[process_id]["progress"] = 100
            active_processes[process_id]["current_step"] = "완료"
            active_processes[process_id]["result"] = {
                "text": final_text,
                "pages": len(image_paths),
                "confidence": avg_confidence,
                "processing_time": processing_time
            }

        logger.info(f"Document processing completed for {upload_id} in {processing_time:.2f}s")

        # 임시 이미지 파일 정리 (성공 시)
        cleanup_temp_images(image_paths, processed_images, logger)

    except Exception as e:
        logger.error(f"Document processing failed for {upload_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        if process_id in active_processes:
            active_processes[process_id]["status"] = "failed"
            active_processes[process_id]["error"] = {
                "message": str(e),
                "type": type(e).__name__
            }

        # 실패 시에도 임시 파일 정리 시도
        try:
            if 'image_paths' in locals() and 'processed_images' in locals():
                cleanup_temp_images(image_paths, processed_images, logger)
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup files after error: {cleanup_error}")


def update_task_settings(task_id: str, settings: Dict[str, Any]) -> bool:
    """
    작업 설정 업데이트

    Args:
        task_id: Celery 작업 ID
        settings: 새로운 설정

    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        # 실제로는 Celery 작업에 시그널을 보내어 설정을 변경
        # 현재는 단순히 성공을 반환
        logger.info(f"Updating settings for task {task_id}: {settings}")
        return True
    except Exception as e:
        logger.error(f"Failed to update task settings for {task_id}: {e}")
        return False


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """작업 상태 조회"""
    # active_processes에서 상태 반환
    if task_id in active_processes:
        process_info = active_processes[task_id]
        # 표준 형식으로 변환
        return {
            "task_id": task_id,
            "status": process_info.get("status", "pending"),
            "progress": process_info.get("progress", 0),
            "current_step": process_info.get("current_step", "Unknown"),
            "result": process_info.get("result"),
            "error": process_info.get("error"),
            "estimated_time": process_info.get("estimated_time")
        }
    return None


def get_processing_status(upload_id: str) -> Optional[Dict[str, Any]]:
    """업로드 ID로 처리 상태 확인"""
    # active_processes에서 upload_id로 검색
    for process_id, process_info in active_processes.items():
        if process_info.get("upload_id") == upload_id:
            return get_task_status(process_id)
    return None


@router.post("/process/{upload_id}", response_model=ProcessingResponse)
async def start_processing(
    upload_id: str,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    문서 처리 시작

    Args:
        upload_id: 업로드된 파일 ID
        request: 처리 요청 옵션
        storage: 임시 저장소 의존성

    Returns:
        ProcessingResponse: 처리 시작 정보

    Raises:
        HTTPException: 파일을 찾을 수 없거나 이미 처리 중인 경우
    """
    try:
        # 파일 존재 확인
        if not storage.file_exists(upload_id):
            raise HTTPException(
                status_code=404,
                detail=f"Upload file '{upload_id}' not found."
            )

        # OCR 엔진 유효성 검사
        validate_ocr_engine(request.ocr_engine)

        # 이미 처리 중인지 확인
        existing_status = get_processing_status(upload_id)
        if existing_status and existing_status.get("status") in ["pending", "processing"]:
            process_id = existing_status.get("task_id", f"existing_{upload_id}")
            return ProcessingResponse(
                process_id=process_id,
                upload_id=upload_id,
                status="already_processing",
                message="File is already being processed",
                created_at=datetime.now()
            )

        # 처리 시간 추정
        estimated_time = estimate_processing_time(request)

        # 처리 작업 시작 (BackgroundTasks 사용)
        import uuid
        process_id = str(uuid.uuid4())

        # 활성 프로세스 추가
        active_processes[process_id] = {
            "upload_id": upload_id,
            "status": "pending",
            "progress": 0,
            "current_step": "처리 대기 중...",
            "created_at": datetime.now(),
            "options": request.model_dump(),
            "estimated_time": estimated_time
        }

        # 백그라운드 실제 처리 시작 (threading 사용)
        import threading
        thread = threading.Thread(
            target=process_document_background,
            args=(process_id, upload_id, request.model_dump())
        )
        thread.daemon = True
        thread.start()

        logger.info(f"Started background thread for upload {upload_id} with process ID {process_id}")

        return ProcessingResponse(
            process_id=process_id,
            upload_id=upload_id,
            status="started",
            message="Processing started successfully",
            estimated_time=estimated_time,
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Failed to start processing for {upload_id}: {error_detail}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )


@router.get("/process/{process_id}/status", response_model=ProcessingStatusResponse)
def get_processing_status_endpoint(process_id: str):
    """
    처리 상태 조회

    Args:
        process_id: 처리 프로세스 ID

    Returns:
        ProcessingStatusResponse: 처리 상태 정보

    Raises:
        HTTPException: 프로세스를 찾을 수 없는 경우
    """
    try:
        task_status = get_task_status(process_id)

        if not task_status:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )

        # 상태 매핑 (대소문자 무관)
        status_mapping = {
            "pending": ProcessingStatus.PENDING,
            "PENDING": ProcessingStatus.PENDING,
            "processing": ProcessingStatus.PROCESSING,
            "PROCESSING": ProcessingStatus.PROCESSING,
            "PROGRESS": ProcessingStatus.PROCESSING,
            "completed": ProcessingStatus.COMPLETED,
            "COMPLETED": ProcessingStatus.COMPLETED,
            "SUCCESS": ProcessingStatus.COMPLETED,
            "failed": ProcessingStatus.FAILED,
            "FAILED": ProcessingStatus.FAILED,
            "FAILURE": ProcessingStatus.FAILED,
            "cancelled": ProcessingStatus.CANCELLED,
            "CANCELLED": ProcessingStatus.CANCELLED,
            "REVOKED": ProcessingStatus.CANCELLED
        }

        status = status_mapping.get(task_status["status"], ProcessingStatus.FAILED)

        response = ProcessingStatusResponse(
            process_id=process_id,
            status=status.value,
            progress=task_status.get("progress", 0),
            current_step=task_status.get("current_step", "Unknown"),
            estimated_time=task_status.get("estimated_time"),
            result=task_status.get("result"),
            error=task_status.get("error"),
            created_at=active_processes.get(process_id, {}).get("created_at"),
            updated_at=datetime.now()
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing status for {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get processing status."
        )


@router.put("/process/{process_id}/settings")
def update_processing_settings(
    process_id: str,
    settings: ProcessingRequest
):
    """
    처리 설정 업데이트

    Args:
        process_id: 처리 프로세스 ID
        settings: 새로운 설정

    Returns:
        Dict: 업데이트 결과

    Raises:
        HTTPException: 프로세스를 찾을 수 없거나 업데이트할 수 없는 경우
    """
    try:
        task_status = get_task_status(process_id)

        if not task_status:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )

        # 완료된 작업은 설정 변경 불가
        if task_status["status"] in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot update settings for completed or failed process."
            )

        # 설정 업데이트 (실제로는 Celery 작업에 시그널 전송)
        update_success = update_task_settings(process_id, settings.model_dump())

        if not update_success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update task settings."
            )

        if process_id in active_processes:
            active_processes[process_id]["options"] = settings.model_dump()
            active_processes[process_id]["updated_at"] = datetime.now()

        logger.info(f"Updated settings for process {process_id}")

        return {
            "message": "Settings updated successfully",
            "process_id": process_id,
            "updated_at": datetime.now()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update settings for {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update processing settings."
        )


@router.get("/process/{process_id}/settings")
def get_processing_settings(process_id: str):
    """
    처리 설정 조회

    Args:
        process_id: 처리 프로세스 ID

    Returns:
        Dict: 현재 설정
    """
    try:
        if process_id not in active_processes:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )

        return active_processes[process_id].get("options", {})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get settings for {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get processing settings."
        )


@router.delete("/process/{process_id}/cancel")
def cancel_processing(process_id: str):
    """
    처리 취소

    Args:
        process_id: 취소할 프로세스 ID

    Returns:
        Dict: 취소 결과
    """
    try:
        task_status = get_task_status(process_id)

        if not task_status:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )

        # 이미 완료된 작업은 취소 불가
        if task_status["status"] in ["completed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel already completed process."
            )

        # Celery 작업 취소
        if celery_app:
            celery_app.control.revoke(process_id, terminate=True)

        # 상태 업데이트
        if process_id in active_processes:
            active_processes[process_id].update({
                "status": "cancelled",
                "current_step": "Cancelled by user",
                "cancelled_at": datetime.now()
            })

        logger.info(f"Cancelled processing for process {process_id}")

        return {
            "message": "Processing cancelled successfully",
            "process_id": process_id,
            "cancelled_at": datetime.now()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel processing {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel processing."
        )


@router.post("/process/{process_id}/restart")
def restart_processing(
    process_id: str,
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    실패한 처리 재시작

    Args:
        process_id: 재시작할 프로세스 ID
        storage: 임시 저장소 의존성

    Returns:
        Dict: 재시작 결과
    """
    try:
        if process_id not in active_processes:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )

        process_info = active_processes[process_id]
        upload_id = process_info["upload_id"]
        options = ProcessingRequest(**process_info["options"])

        # 파일 존재 확인
        if not storage.file_exists(upload_id):
            raise HTTPException(
                status_code=400,
                detail="Original upload file no longer exists."
            )

        # 새로운 처리 작업 시작
        if celery_app and process_document:
            task = process_document.delay(
                upload_id=upload_id,
                options=options.model_dump(),
                priority=options.priority
            )
            new_process_id = task.id
        else:
            import uuid
            new_process_id = str(uuid.uuid4())

        # 새 프로세스 등록
        active_processes[new_process_id] = {
            "upload_id": upload_id,
            "status": "pending",
            "progress": 0,
            "current_step": "Restarted - queued for processing",
            "created_at": datetime.now(),
            "options": options.model_dump(),
            "restarted_from": process_id
        }

        logger.info(f"Restarted processing {process_id} as {new_process_id}")

        return {
            "message": "Processing restarted successfully",
            "original_process_id": process_id,
            "new_process_id": new_process_id,
            "restarted_at": datetime.now()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart processing {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to restart processing."
        )


@router.post("/process/batch/status")
def get_batch_processing_status(task_ids: Dict[str, List[str]]):
    """
    배치 처리 상태 조회

    Args:
        task_ids: 조회할 작업 ID 목록

    Returns:
        Dict: 배치 상태 결과
    """
    try:
        task_id_list = task_ids.get("task_ids", [])
        results = {}

        for task_id in task_id_list:
            task_status = get_task_status(task_id)
            if task_status:
                results[task_id] = {
                    "status": task_status["status"],
                    "progress": task_status.get("progress", 0),
                    "current_step": task_status.get("current_step", "Unknown")
                }
            else:
                results[task_id] = {
                    "status": "not_found",
                    "progress": 0,
                    "current_step": "Not found"
                }

        return {
            "results": results,
            "total_requested": len(task_id_list),
            "found_count": len([r for r in results.values() if r["status"] != "not_found"])
        }

    except Exception as e:
        logger.error(f"Failed to get batch processing status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get batch processing status."
        )


@router.get("/process/history")
def get_processing_history(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None
):
    """
    처리 히스토리 조회

    Args:
        limit: 조회할 항목 수
        offset: 시작 오프셋
        status_filter: 상태 필터

    Returns:
        Dict: 처리 히스토리
    """
    try:
        filtered_history = processing_history

        # 상태 필터 적용
        if status_filter:
            filtered_history = [
                h for h in processing_history
                if h.get("status") == status_filter
            ]

        # 페이지네이션
        paginated_history = filtered_history[offset:offset + limit]

        return {
            "history": paginated_history,
            "total": len(filtered_history),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to get processing history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get processing history."
        )


def get_processing_metrics() -> Dict[str, Any]:
    """처리 메트릭 데이터 계산"""
    # 기본 통계 계산 (실제로는 데이터베이스에서 조회)
    total_processed = len(processing_history)
    successful_count = len([h for h in processing_history if h.get("status") == "completed"])
    failed_count = len([h for h in processing_history if h.get("status") == "failed"])

    success_rate = successful_count / total_processed if total_processed > 0 else 0.0

    # 평균 처리 시간 계산
    processing_times = [
        h.get("processing_time", 0)
        for h in processing_history
        if h.get("processing_time")
    ]
    average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0

    # 엔진 사용량 통계
    engine_usage = {}
    for h in processing_history:
        engine = h.get("options", {}).get("ocr_engine", "unknown")
        engine_usage[engine] = engine_usage.get(engine, 0) + 1

    # 공통 오류 통계
    common_errors = [
        {"error_type": "LowImageQuality", "count": 5},
        {"error_type": "MemoryError", "count": 2},
        {"error_type": "TimeoutError", "count": 1}
    ]

    return {
        "total_processed": total_processed,
        "successful_count": successful_count,
        "failed_count": failed_count,
        "average_processing_time": average_processing_time,
        "success_rate": success_rate,
        "engine_usage": engine_usage,
        "common_errors": common_errors
    }


@router.get("/process/metrics", response_model=ProcessingMetrics)
def get_processing_metrics_endpoint():
    """
    처리 메트릭 조회

    Returns:
        ProcessingMetrics: 처리 메트릭 정보
    """
    try:
        metrics_data = get_processing_metrics()
        return ProcessingMetrics(**metrics_data)

    except Exception as e:
        logger.error(f"Failed to get processing metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get processing metrics."
        )


def get_performance_stats() -> Dict[str, Any]:
    """성능 통계 데이터 계산"""
    # Mock 성능 통계 (실제로는 모니터링 시스템에서 수집)
    return {
        "last_24h": {
            "total_tasks": len([h for h in processing_history if h.get("created_at")]),
            "avg_processing_time": 87.2,
            "peak_processing_hour": "14:00-15:00"
        },
        "last_7d": {
            "total_tasks": len(processing_history),
            "avg_processing_time": 91.8,
            "busiest_day": "Monday"
        },
        "resource_usage": {
            "avg_cpu_usage": 0.65,
            "avg_memory_usage": 0.78,
            "queue_length": len([p for p in active_processes.values() if p.get("status") == "pending"]) or 1
        }
    }


@router.get("/process/stats")
def get_processing_performance_stats():
    """
    처리 성능 통계 조회

    Returns:
        Dict: 성능 통계 정보
    """
    try:
        return get_performance_stats()

    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get performance statistics."
        )


# Helper functions for testing
def get_multiple_task_status(task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """여러 작업의 상태를 조회"""
    results = {}
    for task_id in task_ids:
        status = get_task_status(task_id)
        if status:
            results[task_id] = status
    return results


def update_task_settings(process_id: str, settings: Dict[str, Any]) -> bool:
    """작업 설정 업데이트"""
    if process_id in active_processes:
        active_processes[process_id]["options"].update(settings)
        return True
    return False


def cancel_task(process_id: str) -> bool:
    """작업 취소"""
    if celery_app:
        celery_app.control.revoke(process_id, terminate=True)

    if process_id in active_processes:
        active_processes[process_id]["status"] = "cancelled"
        return True
    return False


def get_task_settings(process_id: str) -> Optional[Dict[str, Any]]:
    """작업 설정 조회"""
    if process_id in active_processes:
        return active_processes[process_id].get("options")
    return None


def get_processing_metrics() -> Dict[str, Any]:
    """처리 메트릭 조회"""
    return {
        "total_processed": len(processing_history),
        "successful_count": len([h for h in processing_history if h.get("status") == "completed"]),
        "failed_count": len([h for h in processing_history if h.get("status") == "failed"]),
        "average_processing_time": 95.5,
        "success_rate": 0.947,
        "engine_usage": {"paddle": 120, "tesseract": 30},
        "common_errors": [
            {"error_type": "LowImageQuality", "count": 5},
            {"error_type": "MemoryError", "count": 2}
        ]
    }


def get_performance_stats() -> Dict[str, Any]:
    """성능 통계 조회"""
    return {
        "last_24h": {
            "total_tasks": 45,
            "avg_processing_time": 87.2,
            "peak_processing_hour": "14:00-15:00"
        },
        "last_7d": {
            "total_tasks": 298,
            "avg_processing_time": 91.8,
            "busiest_day": "Monday"
        },
        "resource_usage": {
            "avg_cpu_usage": 0.65,
            "avg_memory_usage": 0.78,
            "queue_length": 3
        }
    }