from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.admin import CreateStaffRequest, StaffAccountOut
from ..schemas.common import SuccessResponse
from ..services.admin_service import create_staff_account
from ..utils.constants import ROLE_ADMIN

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[StaffAccountOut],
    summary="Create a staff account (admin only)",
)
async def create_staff_account_route(
    body: CreateStaffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Creates a new staff (officer) account, already active. Only the
    admin can call this, and it can only ever create staff accounts,
    never another admin, see scripts/create_admin.py for how the
    platform's one admin account is created.

    Raises:
        EmailAlreadyExistsError: 409, if the email is already registered.
        PhoneAlreadyExistsError: 409, if the phone is already registered.
    """
    staff = await create_staff_account(body.name, body.phone, body.email, body.password, db)
    await db.commit()

    return SuccessResponse[StaffAccountOut](
        message="Staff account created.",
        data=StaffAccountOut.model_validate(staff),
    )
