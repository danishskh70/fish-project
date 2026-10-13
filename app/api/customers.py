
from app.core.record_router import make_record_router
from app.core.record_service import RecordService
from app.specs.customer import CUSTOMER

router = make_record_router(CUSTOMER, RecordService)
