"""메타데이터 서비스 관련 구현"""
import asyncio
import aiohttp
from typing import Optional, Protocol
from ..models.metadata import SnapshotMetadata
from ..utils.logger import get_logger
from ..exceptions import ApiError, MetadataError

class MetadataService(Protocol):
    """메타데이터 서비스 프로토콜"""
    
    async def register_snapshot(self, metadata: SnapshotMetadata) -> None:
        """스냅샷 메타데이터를 등록합니다.
        
        Args:
            metadata: 등록할 스냅샷 메타데이터
            
        Raises:
            MetadataError: 메타데이터 등록 실패 시
            ApiError: API 통신 실패 시
        """
        ...

class ApiMetadataService:
    """HTTP API 기반 메타데이터 서비스"""
    
    def __init__(self, api_url: str = "http://localhost:5000", timeout: float = 5.0):
        self.api_url = api_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug(f"메타데이터 서비스 초기화: {api_url}")
        
    async def __aenter__(self) -> 'ApiMetadataService':
        """비동기 컨텍스트 매니저 진입
        
        Returns:
            ApiMetadataService: 현재 인스턴스
            
        Raises:
            ApiError: API 세션 생성 실패 시
        """
        try:
            self.session = aiohttp.ClientSession()
            return self
        except Exception as e:
            raise ApiError(f"API 세션 생성 실패: {e}") from e
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                raise ApiError(f"API 세션 종료 실패: {e}") from e
            finally:
                self.session = None
        
    async def register_snapshot(self, metadata: SnapshotMetadata) -> None:
        """스냅샷 메타데이터를 API 서버에 등록
        
        Args:
            metadata: 등록할 스냅샷 메타데이터
            
        Raises:
            MetadataError: 메타데이터 등록 실패 시
            ApiError: API 통신 실패 시
        """
        if not self.session:
            try:
                self.session = aiohttp.ClientSession()
            except Exception as e:
                raise ApiError(f"API 세션 생성 실패: {e}") from e
            
        try:
            async with self.session.post(
                f"{self.api_url}/snapshots",
                json=metadata,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    self.logger.info(f"메타데이터 등록 성공: {metadata['snapshot_path']}")
                    return
                else:
                    response_text = await response.text()
                    raise MetadataError(f"메타데이터 등록 실패: {response.status} - {response_text}")
                    
        except asyncio.TimeoutError as e:
            raise ApiError(f"메타데이터 등록 시간 초과: {metadata['snapshot_path']}") from e
        except aiohttp.ClientError as e:
            raise ApiError(f"API 요청 실패: {e}") from e
        except Exception as e:
            raise MetadataError(f"메타데이터 등록 중 오류 발생: {e}") from e 