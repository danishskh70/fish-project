
from app.core.record_router import make_record_router
from app.core.record_service import RecordService
from app.specs.customer import CUSTOMER

router = make_record_router(CUSTOMER, RecordService)


# @router.post(
#     "/",
#     response_model=CustomerRead,
#     status_code=status.HTTP_201_CREATED,
# )
# def post_customer(
#     data: CustomerCreate,
#     db: Session = Depends(get_db),
# ):
#     return create_customer(db, data)


# @router.patch("/{customer_id}", response_model=CustomerRead)
# def patch_customer(
#     customer_id: int,
#     data: CustomerUpdate,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return update_customer(db, customer_id, data)
#     except CustomerNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Customer not found.",
#         ) from None


# @router.post(
#     "/{customer_id}/deactivate",
#     response_model=CustomerRead,
# )
# def post_deactivate_customer(
#     customer_id: int,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return deactivate_customer(db, customer_id)
#     except CustomerNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Customer not found.",
#         ) from None


# @router.post(
#     "/{customer_id}/activate",
#     response_model=CustomerRead,
# )
# def post_activate_customer(
#     customer_id: int,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return activate_customer(db, customer_id)
#     except CustomerNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Customer not found.",
#         ) from None