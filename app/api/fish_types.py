
from app.core.record_router import make_record_router
from app.core.record_service import RecordService
from app.specs.fish_type import FISH_TYPE

router = make_record_router(FISH_TYPE, RecordService)

