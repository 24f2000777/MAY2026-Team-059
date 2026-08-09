from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.admin import (
    CreateStaffRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentOut,
    DepartmentUpdateRequest,
    OfficerListResponse,
    StaffAccountOut,
)
from ..schemas.common import SuccessResponse
from ..services.admin_service import (
    create_department,
    create_staff_account,
    delete_department,
    list_departments,
    list_officers,
    update_department_description,
)
from ..utils.constants import ROLE_ADMIN

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/officers",
    response_model=SuccessResponse[OfficerListResponse],
    summary="List all officers, for an assignment dropdown (admin only)",
)
async def list_officers_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    officers = await list_officers(db)
    return SuccessResponse[OfficerListResponse](
        message="Officers retrieved.",
        data=OfficerListResponse(officers=[StaffAccountOut.model_validate(o) for o in officers]),
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


@router.get(
    "/departments",
    response_model=SuccessResponse[DepartmentListResponse],
    summary="List all departments (admin only)",
)
async def list_departments_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    departments = await list_departments(db)
    return SuccessResponse[DepartmentListResponse](
        message="Departments retrieved.",
        data=DepartmentListResponse(departments=[DepartmentOut.model_validate(d) for d in departments]),
    )


@router.post(
    "/departments",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[DepartmentOut],
    summary="Create a department (admin only)",
)
async def create_department_route(
    body: DepartmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Creates a new department. See admin_service.create_department for
    an important caveat: a name outside the fixed DEPARTMENT_NAMES
    list (app/utils/constants.py) won't ever be picked by the AI
    routing pipeline, it's real and usable for manual assignment only
    unless that constant is also updated in code.

    Raises:
        DepartmentNameAlreadyExistsError: 409, if the name is taken.
    """
    department = await create_department(body.name, body.description, db)
    await db.commit()

    return SuccessResponse[DepartmentOut](
        message="Department created.",
        data=DepartmentOut.model_validate(department),
    )


@router.patch(
    "/departments/{department_id}",
    response_model=SuccessResponse[DepartmentOut],
    summary="Update a department's description (admin only)",
)
async def update_department_route(
    department_id: UUID,
    body: DepartmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Updates a department's description. name is not editable here,
    see admin_service.update_department_description for why renaming
    one of the fixed department names would silently break AI routing
    for it.

    Raises:
        DepartmentNotFoundError: 404, if the department doesn't exist.
    """
    department = await update_department_description(department_id, body.description, db)
    await db.commit()

    return SuccessResponse[DepartmentOut](
        message="Department updated.",
        data=DepartmentOut.model_validate(department),
    )


@router.delete(
    "/departments/{department_id}",
    response_model=SuccessResponse[None],
    summary="Delete a department (admin only)",
)
async def delete_department_route(
    department_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Deletes a department, only if no staff or complaint currently
    references it.

    Raises:
        DepartmentNotFoundError: 404, if the department doesn't exist.
        DepartmentInUseError: 409, if any staff or complaint still
            references this department.
    """
    await delete_department(department_id, db)
    await db.commit()

    return SuccessResponse[None](message="Department deleted.")
