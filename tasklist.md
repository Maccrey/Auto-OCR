# K-OCR Web Corrector - 개발 태스크 리스트
## TDD 방식 웹 개발 체크리스트

### Phase 1: 프로젝트 설정 및 기본 구조

#### 1.1 프로젝트 초기화
- [x] 웹 프로젝트 디렉토리 구조 생성 (frontend/backend 분리)
- [x] requirements.txt 작성 및 가상환경 설정
- [x] FastAPI 기본 설정 및 main.py 작성
- [x] pytest 설정 파일 (pytest.ini) 작성
- [x] mypy 설정 파일 (mypy.ini) 작성
- [x] black/flake8 설정 파일 작성
- [x] .gitignore 파일 작성 (웹 프로젝트용)
- [x] README.md 초기 버전 작성
- [x] Docker 설정 (Dockerfile, docker-compose.yml)
- [x] .env 파일 템플릿 작성

#### 1.2 CI/CD 설정
- [x] GitHub Actions 워크플로우 설정
- [x] 자동 테스트 실행 설정 (FastAPI 테스트 포함)
- [x] 코드 품질 검사 설정
- [x] 커버리지 리포트 설정
- [x] Docker 이미지 빌드 자동화
- [x] 배포 파이프라인 설정

### Phase 2: Backend Core 모듈 개발 (TDD)

#### 2.1 TempStorage 클래스 (utils/temp_storage.py)

**테스트 작성**
- [x] test_temp_storage.py 생성
- [x] 임시 파일 저장 테스트 케이스 작성
  - [x] 파일 저장 및 고유 ID 생성 테스트
  - [x] 파일 검색 및 반환 테스트
  - [x] 파일 TTL 및 자동 삭제 테스트
- [x] 파일 접근 권한 테스트
  - [x] 업로더만 접근 가능 검증
  - [x] 잘못된 ID 접근 차단 테스트
- [x] 저장 공간 관리 테스트

**구현**
- [x] TempStorage 클래스 기본 구조 작성
- [x] save_file() 메서드 구현
- [x] get_file() 메서드 구현
- [x] delete_file() 메서드 구현
- [x] cleanup_expired_files() 메서드 구현
- [x] generate_file_id() 메서드 구현
- [x] 모든 테스트 통과 확인 (16개 테스트 모두 통과)

#### 2.2 PDFConverter 클래스 (core/pdf_converter.py)

**테스트 작성**
- [x] test_pdf_converter.py 생성
- [x] PDF to PNG 변환 테스트 케이스 작성
  - [x] 단일 페이지 PDF 변환 테스트
  - [x] 다중 페이지 PDF 변환 테스트
  - [x] 손상된 PDF 처리 테스트
- [x] PDF 검증 테스트
  - [x] 유효한 PDF 파일 검증
  - [x] 암호화된 PDF 처리 테스트
- [x] 변환 품질 및 해상도 테스트

**구현**
- [x] PDFConverter 클래스 기본 구조 작성
- [x] convert_pdf_to_png() 메서드 구현
- [x] validate_pdf() 메서드 구현
- [x] get_pdf_info() 메서드 구현
- [x] estimate_processing_time() 메서드 구현
- [x] 모든 테스트 통과 확인 (19개 테스트 모두 통과)

#### 2.3 ImageProcessor 클래스 (core/image_processor.py)

**테스트 작성**
- [x] test_image_processor.py 생성
- [x] 이미지 전처리 테스트 케이스 작성
  - [x] 흑백 변환 테스트
  - [x] CLAHE 대비 보정 테스트
  - [x] Deskew 기능 테스트
  - [x] 노이즈 제거 테스트
  - [x] Adaptive Threshold 테스트
- [x] 이미지 품질 검증 테스트
- [x] 전처리 옵션별 결과 비교 테스트

**구현**
- [x] ImageProcessor 클래스 기본 구조 작성
- [x] convert_to_grayscale() 메서드 구현
- [x] apply_clahe() 메서드 구현
- [x] deskew_image() 메서드 구현
- [x] remove_noise() 메서드 구현
- [x] apply_adaptive_threshold() 메서드 구현
- [x] preprocess_pipeline() 메서드 구현
- [x] 모든 테스트 통과 확인 (20개 테스트 모두 통과)

#### 2.4 OCREngine 클래스 (core/ocr_engine.py)

**테스트 작성**
- [x] test_ocr_engine.py 생성
- [x] PaddleOCR 엔진 테스트
  - [x] 엔진 초기화 테스트
  - [x] 텍스트 인식 테스트
  - [x] 신뢰도 점수 테스트
- [x] Tesseract 엔진 테스트
  - [x] 엔진 초기화 테스트
  - [x] 텍스트 인식 테스트
- [x] 앙상블 기능 테스트
- [x] 오류 처리 테스트 (엔진 로드 실패 등)

**구현**
- [x] OCREngine 베이스 클래스 작성
- [x] PaddleOCREngine 클래스 구현
- [x] TesseractEngine 클래스 구현
- [x] OCREngineManager 클래스 구현
- [x] ensemble_recognition() 메서드 구현
- [x] 모든 테스트 통과 확인 (20개 테스트 모두 통과)

#### 2.5 TextCorrector 클래스 (core/text_corrector.py)

**테스트 작성**
- [x] test_text_corrector.py 생성
- [x] 띄어쓰기 교정 테스트
  - [x] KoSpacing 기본 동작 테스트
  - [x] 다양한 텍스트 패턴 테스트 (멀티라인, 빈 텍스트, 오류 처리)
- [x] 맞춤법 교정 테스트
  - [x] 일반적인 맞춤법 오류 교정 테스트
  - [x] 특수한 경우 처리 테스트 (긴 텍스트, 오류 처리)
- [x] 사용자 정의 규칙 테스트 (기본 규칙, 패턴 규칙, OCR 특화 규칙)
- [x] diff 생성 테스트 (단순, 멀티라인, 변경사항 없음)
- [x] CER/WER 계산 테스트
- [x] 통합 테스트 및 성능 테스트

**구현**
- [x] TextCorrector 클래스 기본 구조 작성
- [x] correct_spacing() 메서드 구현 (KoSpacing)
- [x] correct_spelling() 메서드 구현 (Hanspell + 청크 처리)
- [x] apply_custom_rules() 메서드 구현 (일반 규칙, 패턴 규칙, OCR 규칙)
- [x] generate_diff() 메서드 구현 (SequenceMatcher 기반)
- [x] calculate_cer() / calculate_wer() 메서드 구현
- [x] CorrectionResult 및 DiffItem 데이터 클래스 구현
- [x] 설정 관리 및 통계 추적 기능
- [x] 규칙 import/export 기능
- [x] 모든 테스트 통과 확인 (25개 테스트 모두 통과)

#### 2.6 FileGenerator 클래스 (core/file_generator.py)

**테스트 작성**
- [x] test_file_generator.py 생성
- [x] 텍스트 파일 생성 테스트
  - [x] 기본 텍스트 파일 생성 테스트
  - [x] 한글 인코딩 처리 테스트
  - [x] 빈 텍스트 처리 테스트
- [x] 다운로드 응답 생성 테스트
- [x] 임시 파일 정리 테스트

**구현**
- [x] FileGenerator 클래스 기본 구조 작성
- [x] generate_text_file() 메서드 구현
- [x] create_download_response() 메서드 구현
- [x] cleanup_temp_files() 메서드 구현
- [x] get_file_download_url() 메서드 구현
- [x] 모든 테스트 통과 확인 (24개 테스트 모두 통과)

### Phase 3: Web API 개발

#### 3.1 Upload API (api/upload.py)

**테스트 작성**
- [ ] test_upload_api.py 생성
- [ ] 파일 업로드 엔드포인트 테스트
  - [ ] 유효한 PDF 업로드 테스트
  - [ ] 잘못된 파일 형식 거부 테스트
  - [ ] 파일 크기 제한 테스트
- [ ] 업로드 상태 확인 테스트
- [ ] 파일 검증 테스트
- [ ] 에러 처리 테스트

**구현**
- [ ] FastAPI 라우터 기본 구조 작성
- [ ] POST /api/upload 엔드포인트 구현
- [ ] GET /api/upload/{upload_id}/status 엔드포인트 구현
- [ ] 파일 검증 로직 구현
- [ ] 업로드 진행률 추적 구현
- [ ] 모든 테스트 통과 확인

#### 3.2 Processing API (api/processing.py)

**테스트 작성**
- [ ] test_processing_api.py 생성
- [ ] 처리 시작 엔드포인트 테스트
- [ ] 처리 상태 확인 테스트
- [ ] 설정 변경 테스트
- [ ] 비동기 작업 처리 테스트
- [ ] 오류 시나리오 테스트

**구현**
- [ ] POST /api/process/{upload_id} 엔드포인트 구현
- [ ] GET /api/process/{process_id}/status 엔드포인트 구현
- [ ] POST /api/process/{process_id}/settings 엔드포인트 구현
- [ ] Celery 비동기 태스크 구현
- [ ] 실시간 상태 업데이트 구현
- [ ] 모든 테스트 통과 확인

#### 3.3 Download API (api/download.py)

**테스트 작성**
- [ ] test_download_api.py 생성
- [ ] 파일 다운로드 테스트
- [ ] 권한 확인 테스트
- [ ] 파일 만료 처리 테스트
- [ ] 임시 파일 정리 테스트

**구현**
- [ ] GET /api/download/{process_id} 엔드포인트 구현
- [ ] DELETE /api/download/{process_id} 엔드포인트 구현
- [ ] 파일 접근 권한 검증 구현
- [ ] 자동 파일 정리 구현
- [ ] 모든 테스트 통과 확인

### Phase 4: Frontend 개발

#### 4.1 메인 페이지 (templates/index.html)

**테스트 작성**
- [ ] 프론트엔드 테스트 환경 설정 (Jest/Cypress)
- [ ] 페이지 로딩 테스트
- [ ] 파일 업로드 UI 테스트
- [ ] 드래그 앤 드롭 기능 테스트
- [ ] 반응형 디자인 테스트

**구현**
- [ ] HTML 기본 구조 작성
- [ ] CSS 스타일링 구현
- [ ] JavaScript 파일 업로드 로직 구현
- [ ] 드래그 앤 드롭 기능 구현
- [ ] 진행률 표시 UI 구현
- [ ] 모든 테스트 통과 확인

#### 4.2 설정 패널 (static/js/settings.js)

**테스트 작성**
- [ ] 설정 패널 표시/숨김 테스트
- [ ] 전처리 옵션 토글 테스트
- [ ] OCR 엔진 선택 테스트
- [ ] 설정값 저장 테스트

**구현**
- [ ] 설정 패널 UI 구현
- [ ] 전처리 옵션 컨트롤 구현
- [ ] OCR 엔진 선택 드롭다운 구현
- [ ] 설정값 localStorage 저장 구현
- [ ] 모든 테스트 통과 확인

#### 4.3 진행률 표시 (static/js/progress.js)

**테스트 작성**
- [ ] 진행률 업데이트 테스트
- [ ] 단계별 상태 표시 테스트
- [ ] WebSocket 연결 테스트
- [ ] 에러 상태 표시 테스트

**구현**
- [ ] 진행률 바 UI 구현
- [ ] 단계별 진행 상태 표시 구현
- [ ] 실시간 상태 업데이트 (폴링/WebSocket) 구현
- [ ] 에러 처리 및 표시 구현
- [ ] 모든 테스트 통과 확인

#### 4.4 결과 다운로드 페이지 (templates/result.html)

**테스트 작성**
- [ ] 결과 페이지 로딩 테스트
- [ ] 다운로드 버튼 기능 테스트
- [ ] 새 파일 업로드 테스트
- [ ] 페이지 네비게이션 테스트

**구현**
- [ ] 결과 페이지 HTML 구조 작성
- [ ] 다운로드 버튼 구현
- [ ] 처리 결과 정보 표시 구현
- [ ] 새 파일 처리 링크 구현
- [ ] 모든 테스트 통과 확인

### Phase 5: 통합 테스트 및 최적화

#### 5.1 통합 테스트

**API 통합 테스트**
- [ ] test_api_integration.py 생성
- [ ] 전체 API 워크플로우 테스트
  - [ ] 업로드 → 처리 → 다운로드 전체 플로우
  - [ ] 다양한 PDF 문서 테스트
  - [ ] 동시 요청 처리 테스트
- [ ] 성능 테스트
  - [ ] 응답 시간 테스트
  - [ ] 동시 사용자 부하 테스트
  - [ ] 메모리 사용량 모니터링

#### 5.2 사용성 테스트
- [ ] 웹 UI 반응성 테스트 (Lighthouse)
- [ ] 크로스 브라우저 호환성 테스트
- [ ] 모바일 반응형 테스트
- [ ] 접근성 테스트 (WAVE, axe-core)
- [ ] 사용자 시나리오 테스트

### Phase 6: 패키징 및 배포

#### 6.1 Docker 컨테이너화
- [ ] Dockerfile 작성 (멀티 스테이지 빌드)
- [ ] docker-compose.yml 설정 (Redis, Celery 포함)
- [ ] OCR 모델 파일 포함 설정
- [ ] 환경 변수 설정 및 최적화

#### 6.2 클라우드 배포 준비
- [ ] 클라우드 배포용 설정 파일 작성
- [ ] 로드 밸런서 설정
- [ ] 자동 스케일링 설정
- [ ] 모니터링 및 로깅 설정

#### 6.3 배포 테스트
- [ ] 로컬 Docker 환경 테스트
- [ ] 스테이징 환경 배포 테스트
- [ ] 프로덕션 환경 배포 테스트
- [ ] 자동 배포 파이프라인 테스트

### Phase 7: 문서화 및 품질 보증

#### 7.1 사용자 문서
- [ ] 웹 서비스 사용 가이드 작성
- [ ] FAQ 문서 작성
- [ ] 지원되는 브라우저 및 시스템 요구사항 문서
- [ ] 문제 해결 가이드 작성

#### 7.2 개발자 문서
- [ ] FastAPI 자동 생성 API 문서 설정
- [ ] 개발 환경 설정 가이드 작성
- [ ] 아키텍처 문서 업데이트
- [ ] Docker 배포 가이드 작성

#### 7.3 최종 품질 검사
- [ ] 전체 테스트 스위트 실행 (단위/통합/E2E)
- [ ] 코드 커버리지 85% 이상 확인
- [ ] 코드 품질 검사 (mypy, flake8) 통과
- [ ] 웹 보안 취약점 스캔
- [ ] 성능 및 부하 테스트 실행
- [ ] 접근성 검사 통과

### 체크포인트

#### Milestone 1: Backend Core 모듈 완료
- [ ] 모든 Core 모듈 테스트 통과
- [ ] 기본 OCR 파이프라인 동작 확인
- [ ] API 엔드포인트 기본 구현 완료
- [ ] 코드 커버리지 80% 이상

#### Milestone 2: Web API 완료
- [ ] 모든 API 엔드포인트 테스트 통과
- [ ] 파일 업로드/다운로드 기능 완료
- [ ] 비동기 처리 시스템 동작 확인

#### Milestone 3: Frontend 완료
- [ ] 모든 웹 페이지 구현 완료
- [ ] 사용자 인터페이스 테스트 통과
- [ ] 크로스 브라우저 호환성 확인

#### Milestone 4: 통합 및 최적화 완료
- [ ] E2E 테스트 모두 통과
- [ ] 성능 요구사항 달성
- [ ] 보안 검사 통과

#### Milestone 5: 배포 준비 완료
- [ ] Docker 컨테이너화 완료
- [ ] 클라우드 배포 테스트 완료
- [ ] 문서화 완료
- [ ] 최종 품질 검사 통과

### 개발 가이드라인

#### TDD 사이클
1. **RED**: 실패하는 테스트 작성
2. **GREEN**: 테스트를 통과하는 최소한의 코드 작성
3. **REFACTOR**: 코드 품질 개선 및 중복 제거

#### 커밋 메시지 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
test: 테스트 추가 또는 수정
refactor: 리팩토링
docs: 문서 수정
style: 코드 스타일 수정
chore: 빌드 관련 수정
```

#### 브랜치 전략
- `main`: 배포 가능한 안정 버전
- `develop`: 개발 중인 버전
- `feature/`: 기능별 브랜치
- `hotfix/`: 긴급 수정 브랜치

#### 코드 품질 기준
- 테스트 커버리지 > 85%
- 모든 함수에 타입 힌트 적용
- Docstring 작성 (Google 스타일)
- PEP 8 준수 (Black 포매터 사용)