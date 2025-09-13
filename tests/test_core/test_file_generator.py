"""
FileGenerator 클래스 테스트 모듈

이 모듈은 파일 생성 및 다운로드 기능을 테스트합니다:
- 텍스트 파일 생성 테스트
- 다운로드 응답 생성 테스트
- 임시 파일 정리 테스트
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any

# Import from actual module
from backend.core.file_generator import FileGenerator, GeneratedFile, DownloadInfo, FileGeneratorError


class TestFileGenerator:
    """FileGenerator 클래스 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        # 정리
        generator.cleanup_all_temp_files()

    @pytest.fixture
    def sample_text(self):
        """테스트용 텍스트 데이터"""
        return """안녕하세요.
이것은 테스트 텍스트입니다.
한글 인코딩이 올바르게 처리되는지 확인합니다.

특수문자: !@#$%^&*()
숫자: 1234567890
영문: ABCDEFGHIJKLMNOPQRSTUVWXYZ
한글: 가나다라마바사아자차카타파하
"""

    def test_file_generator_initialization(self, file_generator):
        """FileGenerator 초기화 테스트"""
        assert file_generator.temp_dir is not None
        assert Path(file_generator.temp_dir).exists()
        assert file_generator.generated_files == {}

    def test_file_generator_with_custom_temp_dir(self):
        """사용자 정의 임시 디렉토리로 초기화 테스트"""
        custom_dir = tempfile.mkdtemp()
        generator = FileGenerator(custom_dir)

        assert str(generator.temp_dir) == custom_dir
        assert Path(generator.temp_dir).exists()

        # 정리
        generator.cleanup_all_temp_files()


class TestTextFileGeneration:
    """텍스트 파일 생성 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        generator.cleanup_all_temp_files()

    @pytest.fixture
    def sample_text(self):
        """테스트용 한글 텍스트"""
        return "안녕하세요.\n이것은 테스트 텍스트입니다.\n한글 인코딩 테스트: 가나다라"

    def test_generate_text_file_basic(self, file_generator, sample_text):
        """기본 텍스트 파일 생성 테스트"""
        filename = "test_output.txt"
        result = file_generator.generate_text_file(
            text=sample_text,
            filename=filename,
            process_id="test_process_123"
        )

        assert isinstance(result, GeneratedFile)
        assert result.filename == filename
        assert result.process_id == "test_process_123"
        assert result.file_path.exists()
        assert result.file_size > 0
        assert result.mime_type == "text/plain"

        # 파일 내용 검증
        with open(result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == sample_text

    def test_generate_text_file_korean_encoding(self, file_generator):
        """한글 인코딩 처리 테스트"""
        korean_text = "안녕하세요! 한국어 OCR 결과입니다.\n가나다라마바사아자차카타파하"
        filename = "korean_test.txt"

        result = file_generator.generate_text_file(
            text=korean_text,
            filename=filename,
            process_id="korean_test"
        )

        # UTF-8 인코딩으로 저장되었는지 확인
        with open(result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == korean_text

        # 다른 인코딩으로 읽어도 문제없는지 확인
        with open(result.file_path, 'rb') as f:
            raw_content = f.read()
            decoded = raw_content.decode('utf-8')
            assert decoded == korean_text

    def test_generate_text_file_empty_text(self, file_generator):
        """빈 텍스트 처리 테스트"""
        result = file_generator.generate_text_file(
            text="",
            filename="empty.txt",
            process_id="empty_test"
        )

        assert result.file_size == 0
        assert result.file_path.exists()

        with open(result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == ""

    def test_generate_text_file_special_characters(self, file_generator):
        """특수문자 처리 테스트"""
        special_text = "특수문자 테스트: !@#$%^&*()_+-=[]{}|;:,.<>?"

        result = file_generator.generate_text_file(
            text=special_text,
            filename="special.txt",
            process_id="special_test"
        )

        with open(result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == special_text

    def test_generate_text_file_long_content(self, file_generator):
        """긴 텍스트 처리 테스트"""
        long_text = "긴 텍스트 테스트\n" * 1000  # 1000줄

        result = file_generator.generate_text_file(
            text=long_text,
            filename="long_text.txt",
            process_id="long_test"
        )

        assert result.file_size > 1000  # 최소 크기 확인

        with open(result.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == long_text

    def test_generate_text_file_duplicate_filename(self, file_generator, sample_text):
        """중복 파일명 처리 테스트"""
        filename = "duplicate.txt"
        process_id = "duplicate_test"

        # 첫 번째 파일 생성
        result1 = file_generator.generate_text_file(sample_text, filename, process_id)

        # 같은 process_id로 다시 생성 (덮어쓰기)
        new_text = "새로운 내용"
        result2 = file_generator.generate_text_file(new_text, filename, process_id)

        # 새 파일이 이전 파일을 대체했는지 확인
        assert result2.file_path.exists()

        with open(result2.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == new_text


class TestDownloadResponse:
    """다운로드 응답 생성 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        generator.cleanup_all_temp_files()

    @pytest.fixture
    def generated_file(self, file_generator):
        """테스트용 생성된 파일"""
        text = "테스트 다운로드 파일"
        return file_generator.generate_text_file(
            text=text,
            filename="download_test.txt",
            process_id="download_process"
        )

    def test_create_download_response_success(self, file_generator, generated_file):
        """성공적인 다운로드 응답 생성 테스트"""
        response = file_generator.create_download_response(
            process_id="download_process"
        )

        assert isinstance(response, FileResponse)
        assert response.path == str(generated_file.file_path)
        assert response.filename == generated_file.filename
        assert response.media_type == "text/plain"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_create_download_response_not_found(self, file_generator):
        """존재하지 않는 파일 다운로드 시도 테스트"""
        with pytest.raises(HTTPException) as exc_info:
            file_generator.create_download_response("nonexistent_process")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_create_download_response_custom_filename(self, file_generator, generated_file):
        """사용자 정의 파일명으로 다운로드 응답 생성 테스트"""
        custom_filename = "custom_download_name.txt"

        response = file_generator.create_download_response(
            process_id="download_process",
            download_filename=custom_filename
        )

        assert response.filename == custom_filename
        assert custom_filename in response.headers.get("content-disposition", "")

    def test_get_file_download_url(self, file_generator, generated_file):
        """다운로드 URL 생성 테스트"""
        url = file_generator.get_file_download_url("download_process")

        assert url is not None
        assert "download_process" in url
        assert url.startswith("/api/download/") or url.startswith("/download/")

    def test_get_download_info(self, file_generator, generated_file):
        """다운로드 정보 조회 테스트"""
        info = file_generator.get_download_info("download_process")

        assert isinstance(info, DownloadInfo)
        assert info.process_id == "download_process"
        assert info.filename == generated_file.filename
        assert info.file_size == generated_file.file_size
        assert info.is_ready is True
        assert info.download_url is not None


class TestTempFileCleanup:
    """임시 파일 정리 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        # 테스트 후 남은 파일들 정리
        try:
            generator.cleanup_all_temp_files()
        except:
            pass

    def test_cleanup_temp_files_single(self, file_generator):
        """단일 프로세스 임시 파일 정리 테스트"""
        # 파일 생성
        generated_file = file_generator.generate_text_file(
            text="cleanup test",
            filename="cleanup.txt",
            process_id="cleanup_test"
        )

        # 파일이 존재하는지 확인
        assert generated_file.file_path.exists()
        assert "cleanup_test" in file_generator.generated_files

        # 정리 실행
        cleaned_files = file_generator.cleanup_temp_files("cleanup_test")

        # 정리 결과 확인
        assert len(cleaned_files) == 1
        assert not generated_file.file_path.exists()
        assert "cleanup_test" not in file_generator.generated_files

    def test_cleanup_temp_files_nonexistent(self, file_generator):
        """존재하지 않는 프로세스 정리 테스트"""
        cleaned_files = file_generator.cleanup_temp_files("nonexistent")
        assert len(cleaned_files) == 0

    def test_cleanup_all_temp_files(self, file_generator):
        """전체 임시 파일 정리 테스트"""
        # 여러 파일 생성
        files = []
        for i in range(3):
            generated_file = file_generator.generate_text_file(
                text=f"test file {i}",
                filename=f"test_{i}.txt",
                process_id=f"process_{i}"
            )
            files.append(generated_file)

        # 모든 파일이 존재하는지 확인
        for file in files:
            assert file.file_path.exists()
        assert len(file_generator.generated_files) == 3

        # 전체 정리 실행
        cleaned_count = file_generator.cleanup_all_temp_files()

        # 정리 결과 확인
        assert cleaned_count >= 3
        for file in files:
            assert not file.file_path.exists()
        assert len(file_generator.generated_files) == 0

    def test_cleanup_expired_files(self, file_generator):
        """만료된 파일 정리 테스트"""
        # 파일 생성
        generated_file = file_generator.generate_text_file(
            text="expire test",
            filename="expire.txt",
            process_id="expire_test"
        )

        # 파일 생성 시간을 과거로 설정 (모킹)
        import time
        old_time = time.time() - 3600  # 1시간 전

        with patch('time.time', return_value=old_time):
            # 파일 재생성으로 과거 시간 설정
            file_generator.generated_files["expire_test"].created_at = old_time

        # 만료된 파일 정리 (30분 = 1800초)
        cleaned_files = file_generator.cleanup_expired_files(max_age_seconds=1800)

        assert len(cleaned_files) >= 1
        assert not generated_file.file_path.exists()


class TestErrorHandling:
    """오류 처리 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        generator.cleanup_all_temp_files()

    def test_generate_file_permission_error(self, file_generator):
        """파일 생성 권한 오류 처리 테스트"""
        # 읽기 전용 디렉토리로 변경
        os.chmod(file_generator.temp_dir, 0o444)

        try:
            with pytest.raises(FileGeneratorError):
                file_generator.generate_text_file(
                    text="permission test",
                    filename="permission.txt",
                    process_id="permission_test"
                )
        finally:
            # 권한 복구
            os.chmod(file_generator.temp_dir, 0o755)

    def test_invalid_filename_handling(self, file_generator):
        """잘못된 파일명 처리 테스트"""
        # 잘못된 문자가 포함된 파일명
        invalid_filenames = [
            "file<>name.txt",
            "file|name.txt",
            "file*name.txt",
            "file?name.txt"
        ]

        for invalid_name in invalid_filenames:
            # 잘못된 파일명은 자동으로 정리되어야 함
            result = file_generator.generate_text_file(
                text="invalid filename test",
                filename=invalid_name,
                process_id=f"invalid_{invalid_name}"
            )

            # 파일이 생성되었는지 확인 (정리된 이름으로)
            assert result.file_path.exists()

    def test_disk_space_simulation(self, file_generator):
        """디스크 공간 부족 시뮬레이션 (모킹)"""
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with pytest.raises(FileGeneratorError):
                file_generator.generate_text_file(
                    text="disk space test",
                    filename="diskspace.txt",
                    process_id="diskspace_test"
                )


class TestFileMetadata:
    """파일 메타데이터 테스트"""

    @pytest.fixture
    def file_generator(self):
        """FileGenerator 인스턴스 생성"""
        temp_dir = tempfile.mkdtemp()
        generator = FileGenerator(temp_dir)
        yield generator
        generator.cleanup_all_temp_files()

    def test_file_metadata_tracking(self, file_generator):
        """파일 메타데이터 추적 테스트"""
        text = "metadata test content"
        result = file_generator.generate_text_file(
            text=text,
            filename="metadata.txt",
            process_id="metadata_test"
        )

        # 메타데이터 확인
        assert result.file_size == len(text.encode('utf-8'))
        assert result.created_at is not None
        assert result.mime_type == "text/plain"
        assert result.process_id == "metadata_test"

    def test_get_all_generated_files(self, file_generator):
        """생성된 모든 파일 목록 조회 테스트"""
        # 여러 파일 생성
        for i in range(3):
            file_generator.generate_text_file(
                text=f"file {i}",
                filename=f"list_{i}.txt",
                process_id=f"list_process_{i}"
            )

        all_files = file_generator.get_all_generated_files()

        assert len(all_files) == 3
        for process_id, file_info in all_files.items():
            assert process_id.startswith("list_process_")
            assert isinstance(file_info, GeneratedFile)

    def test_file_exists_check(self, file_generator):
        """파일 존재 확인 테스트"""
        # 파일 생성
        file_generator.generate_text_file(
            text="exists test",
            filename="exists.txt",
            process_id="exists_test"
        )

        # 존재 확인
        assert file_generator.file_exists("exists_test") is True
        assert file_generator.file_exists("nonexistent") is False

    def test_get_file_stats(self, file_generator):
        """파일 통계 조회 테스트"""
        # 여러 파일 생성
        total_size = 0
        for i in range(5):
            text = f"stats test file {i} " * 10
            file_generator.generate_text_file(
                text=text,
                filename=f"stats_{i}.txt",
                process_id=f"stats_process_{i}"
            )
            total_size += len(text.encode('utf-8'))

        stats = file_generator.get_file_stats()

        assert stats["total_files"] == 5
        assert stats["total_size"] >= total_size
        assert stats["temp_dir"] == str(file_generator.temp_dir)