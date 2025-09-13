"""
TextCorrector 모듈

이 모듈은 한국어 텍스트 교정 기능을 제공합니다:
- KoSpacing을 이용한 띄어쓰기 교정
- py-hanspell을 이용한 맞춤법 교정
- 사용자 정의 규칙 적용
- OCR 특화 오류 패턴 교정
- 편집 거리 기반 CER/WER 계산
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Union
from difflib import SequenceMatcher
import Levenshtein
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)


class TextCorrectionError(Exception):
    """텍스트 교정 관련 오류"""
    pass


@dataclass
class DiffItem:
    """텍스트 변경 항목"""
    line_number: int
    original: str
    corrected: str
    change_type: str  # 'insert', 'delete', 'replace', 'none'
    position: Tuple[int, int] = (0, 0)  # (start, end) position in line

    def __post_init__(self):
        """초기화 후 검증"""
        valid_types = ['insert', 'delete', 'replace', 'none']
        if self.change_type not in valid_types:
            raise ValueError(f"Invalid change_type: {self.change_type}")


@dataclass
class CorrectionResult:
    """텍스트 교정 결과"""
    original_text: str
    corrected_text: str
    corrections: List[DiffItem]
    cer_score: float  # Character Error Rate
    wer_score: float  # Word Error Rate
    spacing_changes: int = 0
    spelling_changes: int = 0
    custom_rule_changes: int = 0
    processing_time: float = 0.0

    def __post_init__(self):
        """초기화 후 검증"""
        if self.cer_score < 0.0 or self.cer_score > 1.0:
            raise ValueError("CER score must be between 0.0 and 1.0")
        if self.wer_score < 0.0 or self.wer_score > 1.0:
            raise ValueError("WER score must be between 0.0 and 1.0")


class TextCorrector:
    """한국어 텍스트 교정 클래스"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        TextCorrector 초기화
        
        Args:
            config: 교정 설정 딕셔너리
        """
        self.config = self._load_default_config()
        if config:
            self.config.update(config)
        
        # 사용자 정의 규칙
        self.custom_rules: Dict[str, str] = {}
        self.pattern_rules: Dict[str, str] = {}
        self.ocr_correction_rules: Dict[str, str] = {}
        
        # 통계 정보
        self.correction_statistics = {
            'total_corrections': 0,
            'total_processing_time': 0.0,
            'cer_scores': [],
            'wer_scores': [],
            'spacing_corrections': 0,
            'spelling_corrections': 0,
            'custom_rule_corrections': 0
        }
        
        # 의존성 초기화
        self._kospacing = None
        self._hanspell = None
        self._initialize_dependencies()
    
    def _load_default_config(self) -> Dict:
        """기본 설정 로드"""
        return {
            'spacing': {
                'enabled': True,
                'confidence_threshold': 0.8,
                'batch_size': 1000
            },
            'spelling': {
                'enabled': True,
                'chunk_size': 500,
                'max_retries': 3
            },
            'custom_rules': {
                'case_sensitive': False,
                'use_regex': True,
                'max_rules': 1000
            },
            'performance': {
                'enable_caching': True,
                'cache_size': 100,
                'timeout_seconds': 30
            }
        }
    
    def _initialize_dependencies(self) -> None:
        """의존성 초기화"""
        try:
            # KoSpacing 초기화
            spacing_enabled = self.config['spacing']['enabled']
            if spacing_enabled:
                try:
                    import kospacing
                    self._kospacing = kospacing
                    logger.info("KoSpacing loaded successfully")
                except ImportError:
                    logger.warning("KoSpacing not available. Spacing correction will be disabled.")
                    self.config['spacing']['enabled'] = False
            
            # py-hanspell 초기화
            spelling_enabled = self.config['spelling']['enabled']
            if spelling_enabled:
                try:
                    import hanspell
                    self._hanspell = hanspell
                    logger.info("py-hanspell loaded successfully")
                except ImportError:
                    logger.warning("py-hanspell not available. Spelling correction will be disabled.")
                    self.config['spelling']['enabled'] = False
                    
        except Exception as e:
            logger.error(f"Failed to initialize dependencies: {e}")
    
    def correct_spacing(self, text: str) -> str:
        """
        띄어쓰기 교정
        
        Args:
            text: 교정할 텍스트
            
        Returns:
            str: 띄어쓰기가 교정된 텍스트
            
        Raises:
            TextCorrectionError: 교정 실패 시
        """
        if not text or not text.strip():
            return text
        
        if not self.config['spacing']['enabled'] or not self._kospacing:
            logger.warning("Spacing correction is disabled")
            return text
        
        try:
            # 멀티라인 텍스트 처리
            lines = text.split('\n')
            corrected_lines = []
            
            for line in lines:
                if line.strip():  # 빈 라인이 아닌 경우만 처리
                    corrected_line = self._kospacing.spacing(line.strip())
                    corrected_lines.append(corrected_line)
                else:
                    corrected_lines.append(line)
            
            result = '\n'.join(corrected_lines)
            logger.debug(f"Spacing correction completed: {len(text)} -> {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Spacing correction failed: {e}")
            raise TextCorrectionError(f"Spacing correction failed: {e}")
    
    def correct_spelling(self, text: str) -> str:
        """
        맞춤법 교정
        
        Args:
            text: 교정할 텍스트
            
        Returns:
            str: 맞춤법이 교정된 텍스트
            
        Raises:
            TextCorrectionError: 교정 실패 시
        """
        if not text or not text.strip():
            return text
        
        if not self.config['spelling']['enabled'] or not self._hanspell:
            logger.warning("Spelling correction is disabled")
            return text
        
        try:
            chunk_size = self.config['spelling']['chunk_size']
            
            # 긴 텍스트는 청크로 나누어 처리
            if len(text) <= chunk_size:
                return self._correct_spelling_chunk(text)
            
            # 텍스트를 청크로 분할
            chunks = self._split_text_into_chunks(text, chunk_size)
            corrected_chunks = []
            
            for chunk in chunks:
                corrected_chunk = self._correct_spelling_chunk(chunk)
                corrected_chunks.append(corrected_chunk)
            
            result = ''.join(corrected_chunks)
            logger.debug(f"Spelling correction completed: {len(chunks)} chunks processed")
            return result
            
        except Exception as e:
            logger.error(f"Spelling correction failed: {e}")
            raise TextCorrectionError(f"Spelling correction failed: {e}")
    
    def _correct_spelling_chunk(self, text: str) -> str:
        """단일 청크 맞춤법 교정"""
        try:
            result = self._hanspell.spell_checker.check(text)
            return result.checked
        except Exception as e:
            logger.warning(f"Spelling correction failed for chunk: {e}")
            # 설정에 따라 오류 발생 또는 원본 반환
            if self.config['spelling'].get('raise_on_error', False):
                raise TextCorrectionError(f"Spelling correction failed: {e}")
            return text  # 실패 시 원본 반환
    
    def _split_text_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """텍스트를 적절한 크기로 분할"""
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # 청크 크기만큼 자르되, 단어 경계에서 끊기도록 조정
            end_pos = min(current_pos + chunk_size, len(text))
            
            if end_pos < len(text):
                # 단어 경계 찾기
                for i in range(end_pos, current_pos, -1):
                    if text[i] in ' \n\t.!?':
                        end_pos = i + 1
                        break
            
            chunk = text[current_pos:end_pos]
            chunks.append(chunk)
            current_pos = end_pos
        
        return chunks
    
    def add_custom_rules(self, rules: Dict[str, str]) -> None:
        """사용자 정의 규칙 추가"""
        if len(self.custom_rules) + len(rules) > self.config['custom_rules']['max_rules']:
            raise ValueError(f"Too many custom rules. Maximum: {self.config['custom_rules']['max_rules']}")
        
        self.custom_rules.update(rules)
        logger.info(f"Added {len(rules)} custom rules")
    
    def add_pattern_rules(self, pattern_rules: Dict[str, str]) -> None:
        """정규표현식 기반 규칙 추가"""
        for pattern, replacement in pattern_rules.items():
            try:
                # 패턴 유효성 검사
                re.compile(pattern)
                self.pattern_rules[pattern] = replacement
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        logger.info(f"Added {len(pattern_rules)} pattern rules")
    
    def add_ocr_correction_rules(self, ocr_rules: Dict[str, str]) -> None:
        """OCR 특화 교정 규칙 추가"""
        self.ocr_correction_rules.update(ocr_rules)
        logger.info(f"Added {len(ocr_rules)} OCR correction rules")
    
    def apply_custom_rules(self, text: str) -> str:
        """
        사용자 정의 규칙 적용
        
        Args:
            text: 교정할 텍스트
            
        Returns:
            str: 규칙이 적용된 텍스트
        """
        if not text:
            return text
        
        result = text
        case_sensitive = self.config['custom_rules']['case_sensitive']
        
        # 일반 치환 규칙 적용
        for old, new in self.custom_rules.items():
            if case_sensitive:
                result = result.replace(old, new)
            else:
                # 대소문자 무시 치환 (한국어에서는 대부분 의미 없음)
                result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)
        
        # 정규표현식 규칙 적용
        if self.config['custom_rules']['use_regex']:
            for pattern, replacement in self.pattern_rules.items():
                try:
                    result = re.sub(pattern, replacement, result)
                except re.error as e:
                    logger.warning(f"Regex substitution failed for pattern '{pattern}': {e}")
        
        # OCR 특화 규칙 적용
        for old, new in self.ocr_correction_rules.items():
            result = result.replace(old, new)
        
        return result
    
    def generate_diff(self, original: str, corrected: str) -> List[DiffItem]:
        """
        원본과 교정된 텍스트 간의 차이점 생성
        
        Args:
            original: 원본 텍스트
            corrected: 교정된 텍스트
            
        Returns:
            List[DiffItem]: 변경사항 목록
        """
        diff_items = []
        
        # 라인별로 비교
        original_lines = original.split('\n')
        corrected_lines = corrected.split('\n')
        
        matcher = SequenceMatcher(None, original_lines, corrected_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            elif tag == 'replace':
                for k in range(max(i2 - i1, j2 - j1)):
                    orig_line = original_lines[i1 + k] if i1 + k < i2 else ""
                    corr_line = corrected_lines[j1 + k] if j1 + k < j2 else ""
                    
                    if orig_line != corr_line:
                        diff_item = DiffItem(
                            line_number=i1 + k + 1,
                            original=orig_line,
                            corrected=corr_line,
                            change_type='replace'
                        )
                        diff_items.append(diff_item)
            
            elif tag == 'delete':
                for k in range(i1, i2):
                    diff_item = DiffItem(
                        line_number=k + 1,
                        original=original_lines[k],
                        corrected="",
                        change_type='delete'
                    )
                    diff_items.append(diff_item)
            
            elif tag == 'insert':
                for k in range(j1, j2):
                    diff_item = DiffItem(
                        line_number=k + 1,
                        original="",
                        corrected=corrected_lines[k],
                        change_type='insert'
                    )
                    diff_items.append(diff_item)
        
        return diff_items
    
    def calculate_cer(self, original: str, corrected: str) -> float:
        """
        Character Error Rate (CER) 계산
        
        Args:
            original: 원본 텍스트
            corrected: 교정된 텍스트
            
        Returns:
            float: CER 점수 (0.0 ~ 1.0)
        """
        if not original:
            return 0.0 if not corrected else 1.0
        
        # Levenshtein 거리 계산
        edit_distance = Levenshtein.distance(original, corrected)
        cer = edit_distance / len(original)
        
        return min(cer, 1.0)  # 1.0을 초과하지 않도록 제한
    
    def calculate_wer(self, original: str, corrected: str) -> float:
        """
        Word Error Rate (WER) 계산
        
        Args:
            original: 원본 텍스트
            corrected: 교정된 텍스트
            
        Returns:
            float: WER 점수 (0.0 ~ 1.0)
        """
        original_words = original.split()
        corrected_words = corrected.split()
        
        if not original_words:
            return 0.0 if not corrected_words else 1.0
        
        # 단어 레벨 편집 거리 계산 (문자열로 변환)
        original_str = ' '.join(original_words)
        corrected_str = ' '.join(corrected_words)
        
        # SequenceMatcher를 사용하여 단어 레벨 편집 거리 계산
        matcher = SequenceMatcher(None, original_words, corrected_words)
        
        # 편집 연산 수 계산
        edit_distance = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                edit_distance += max(i2 - i1, j2 - j1)
        
        wer = edit_distance / len(original_words)
        
        return min(wer, 1.0)  # 1.0을 초과하지 않도록 제한
    
    def correct_text(self,
                     text: str,
                     apply_spacing: bool = True,
                     apply_spelling: bool = True,
                     apply_custom_rules: bool = True) -> CorrectionResult:
        """
        종합적인 텍스트 교정
        
        Args:
            text: 교정할 텍스트
            apply_spacing: 띄어쓰기 교정 적용 여부
            apply_spelling: 맞춤법 교정 적용 여부
            apply_custom_rules: 사용자 정의 규칙 적용 여부
            
        Returns:
            CorrectionResult: 교정 결과
        """
        start_time = time.time()
        original_text = text
        corrected_text = text
        
        spacing_changes = 0
        spelling_changes = 0
        custom_rule_changes = 0
        
        try:
            # 1. 띄어쓰기 교정
            if apply_spacing:
                before_spacing = corrected_text
                corrected_text = self.correct_spacing(corrected_text)
                if corrected_text != before_spacing:
                    spacing_changes = 1
            
            # 2. 맞춤법 교정
            if apply_spelling:
                before_spelling = corrected_text
                corrected_text = self.correct_spelling(corrected_text)
                if corrected_text != before_spelling:
                    spelling_changes = 1
            
            # 3. 사용자 정의 규칙 적용
            if apply_custom_rules:
                before_custom = corrected_text
                corrected_text = self.apply_custom_rules(corrected_text)
                if corrected_text != before_custom:
                    custom_rule_changes = 1
            
            # 4. 차이점 생성
            corrections = self.generate_diff(original_text, corrected_text)
            
            # 5. CER/WER 계산
            cer_score = self.calculate_cer(original_text, corrected_text)
            wer_score = self.calculate_wer(original_text, corrected_text)
            
            processing_time = time.time() - start_time
            
            # 결과 생성
            result = CorrectionResult(
                original_text=original_text,
                corrected_text=corrected_text,
                corrections=corrections,
                cer_score=cer_score,
                wer_score=wer_score,
                spacing_changes=spacing_changes,
                spelling_changes=spelling_changes,
                custom_rule_changes=custom_rule_changes,
                processing_time=processing_time
            )
            
            # 통계 업데이트
            self._update_statistics(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Text correction failed: {e}")
            raise TextCorrectionError(f"Text correction failed: {e}")
    
    def _update_statistics(self, result: CorrectionResult) -> None:
        """통계 정보 업데이트"""
        stats = self.correction_statistics
        
        stats['total_corrections'] += 1
        stats['total_processing_time'] += result.processing_time
        stats['cer_scores'].append(result.cer_score)
        stats['wer_scores'].append(result.wer_score)
        stats['spacing_corrections'] += result.spacing_changes
        stats['spelling_corrections'] += result.spelling_changes
        stats['custom_rule_corrections'] += result.custom_rule_changes
        
        # 히스토리 크기 제한 (최근 1000개)
        if len(stats['cer_scores']) > 1000:
            stats['cer_scores'] = stats['cer_scores'][-1000:]
        if len(stats['wer_scores']) > 1000:
            stats['wer_scores'] = stats['wer_scores'][-1000:]
    
    def get_correction_statistics(self) -> Dict:
        """교정 통계 정보 반환"""
        stats = self.correction_statistics.copy()
        
        if stats['cer_scores']:
            stats['average_cer'] = sum(stats['cer_scores']) / len(stats['cer_scores'])
            stats['min_cer'] = min(stats['cer_scores'])
            stats['max_cer'] = max(stats['cer_scores'])
        
        if stats['wer_scores']:
            stats['average_wer'] = sum(stats['wer_scores']) / len(stats['wer_scores'])
            stats['min_wer'] = min(stats['wer_scores'])
            stats['max_wer'] = max(stats['wer_scores'])
        
        if stats['total_corrections'] > 0:
            stats['average_processing_time'] = (
                stats['total_processing_time'] / stats['total_corrections']
            )
        
        return stats
    
    def clear_statistics(self) -> None:
        """통계 정보 초기화"""
        self.correction_statistics = {
            'total_corrections': 0,
            'total_processing_time': 0.0,
            'cer_scores': [],
            'wer_scores': [],
            'spacing_corrections': 0,
            'spelling_corrections': 0,
            'custom_rule_corrections': 0
        }
    
    def export_rules(self, file_path: Union[str, Path]) -> None:
        """사용자 정의 규칙을 파일로 내보내기"""
        import json
        
        rules_data = {
            'custom_rules': self.custom_rules,
            'pattern_rules': self.pattern_rules,
            'ocr_correction_rules': self.ocr_correction_rules,
            'config': self.config
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Rules exported to {file_path}")
    
    def import_rules(self, file_path: Union[str, Path]) -> None:
        """파일에서 사용자 정의 규칙 가져오기"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            if 'custom_rules' in rules_data:
                self.add_custom_rules(rules_data['custom_rules'])
            
            if 'pattern_rules' in rules_data:
                self.add_pattern_rules(rules_data['pattern_rules'])
            
            if 'ocr_correction_rules' in rules_data:
                self.add_ocr_correction_rules(rules_data['ocr_correction_rules'])
            
            if 'config' in rules_data:
                self.config.update(rules_data['config'])
            
            logger.info(f"Rules imported from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to import rules from {file_path}: {e}")
            raise TextCorrectionError(f"Failed to import rules: {e}")
    
    def get_correction_info(self) -> Dict:
        """교정기 정보 반환"""
        return {
            'config': self.config,
            'custom_rules_count': len(self.custom_rules),
            'pattern_rules_count': len(self.pattern_rules),
            'ocr_rules_count': len(self.ocr_correction_rules),
            'dependencies': {
                'kospacing_available': self._kospacing is not None,
                'hanspell_available': self._hanspell is not None
            },
            'statistics': self.get_correction_statistics()
        }