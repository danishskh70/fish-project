
from app.core.record_router import make_record_router
from app.core.record_service import RecordService
from app.specs.supplier import SUPPLIER

router = make_record_router(SUPPLIER, RecordService)


# @router.post(
#     "/",
#     response_model=SupplierRead,
#     status_code=status.HTTP_201_CREATED,
# )
# def post_supplier(
#     data: SupplierCreate,
#     db: Session = Depends(get_db),
# ):
#     return create_supplier(db, data)


# @router.patch("/{supplier_id}", response_model=SupplierRead)
# def patch_supplier(
#     supplier_id: int,
#     data: SupplierUpdate,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return update_supplier(db, supplier_id, data)
#     except SupplierNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Supplier not found.",
#         ) from None
#     except EmptySupplierUpdateError:
#         raise HTTPException(
#             status_code=422,
#             detail="At least one field must be provided.",
#         ) from None


# @router.post(
#     "/{supplier_id}/deactivate",
#     response_model=SupplierRead,
# )
# def post_deactivate_supplier(
#     supplier_id: int,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return deactivate_supplier(db, supplier_id)
#     except SupplierNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Supplier not found.",
#         ) from None


# @router.post(
#     "/{supplier_id}/activate",
#     response_model=SupplierRead,
# )
# def post_activate_supplier(
#     supplier_id: int,
#     db: Session = Depends(get_db),
# ):
#     try:
#         return activate_supplier(db, supplier_id)
#     except SupplierNotFoundError:
#         raise HTTPException(
#             status_code=404,
#             detail="Supplier not found.",
#         ) from None