
from app.core.record_router import make_record_router
from app.core.record_service import RecordService
from app.specs.supplier import SUPPLIER

router = make_record_router(SUPPLIER, RecordService)
