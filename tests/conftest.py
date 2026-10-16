import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.session import Base
from app.models.customer import Customer  # noqa: F401
from app.models.fish_type import FishType  # noqa: F401
from app.models.packing_list import PackingList  # noqa: F401
from app.models.packing_list_item import PackingListItem  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.supplier_delivery import SupplierDelivery, SupplierDeliveryItem  # noqa: F401
from app.models.supplier_list import SupplierList  # noqa: F401
from app.models.supplier_list_item import SupplierListItem  # noqa: F401
from app.models.trip import Trip  # noqa: F401
from app.models.trip_customer import TripCustomer  # noqa: F401
from app.models.trip_customer_requirement import TripCustomerRequirement  # noqa: F401
from app.models.trip_fish_type import TripFishType  # noqa: F401
from main import app


@pytest.fixture
def test_session_local():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    try:
        yield TestSessionLocal
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def db_session(test_session_local):
    with test_session_local() as db:
        yield db


@pytest.fixture
def client(test_session_local):
    def override_get_db():
        with test_session_local() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
