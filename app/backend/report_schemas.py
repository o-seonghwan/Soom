
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# =========================================
# 1. 공통 타입
# =========================================

ReportType = Literal[
    "smoking",
    "cigarette_butt",
    "other",
]

ReportStatus = Literal[
    "pending",
    "verified",
    "rejected",
]

ReviewStatus = Literal[
    "verified",
    "rejected",
]

Coordinate = tuple[float, float]

KOREA_TIMEZONE = ZoneInfo("Asia/Seoul")


# =========================================
# 2. 사용자 제보 등록
# =========================================

class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: Coordinate
    type: ReportType
    observedAt: datetime

    description: str = Field(
        default="",
        max_length=2000,
    )

    @field_validator("location")
    @classmethod
    def validate_location(cls, value):
        lat, lng = value

        if not (-90 <= lat <= 90):
            raise ValueError("위도 범위가 올바르지 않습니다.")

        if not (-180 <= lng <= 180):
            raise ValueError("경도 범위가 올바르지 않습니다.")

        return value

    @field_validator("observedAt")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None:
            return value.replace(
                tzinfo=KOREA_TIMEZONE
            )

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value):
        return value.strip()


# =========================================
# 3. 제보 조회 응답
# =========================================

class ReportResponse(BaseModel):
    id: str
    location: Coordinate
    type: ReportType
    observedAt: datetime
    description: str
    status: ReportStatus
    createdAt: datetime


# =========================================
# 4. 관리자 검토 요청
# =========================================

class ReportReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReviewStatus

    reviewNote: str = Field(
        default="",
        max_length=1000,
    )

    @field_validator("reviewNote")
    @classmethod
    def normalize_review_note(cls, value):
        return value.strip()


# =========================================
# 5. 관리자 검토 결과
# =========================================

class AdminReportResponse(ReportResponse):
    reviewedAt: datetime | None = None
    reviewNote: str | None = None
