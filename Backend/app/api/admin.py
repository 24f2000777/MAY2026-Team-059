from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.admin import (
    AssignStaffDepartmentRequest,
    CreateStaffRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentOut,
    DepartmentUpdateRequest,
    OfficerListResponse,
    StaffAccountOut,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    UserComplaintSummary,
    UserDetailResponse,
    UserListResponse,
    UserOut,
)
from ..schemas.common import SuccessResponse
from ..schemas.complaint import ComplaintCategory, ComplaintStatus
from ..services.admin_service import (
    assign_staff_department,
    create_department,
    create_staff_account,
    delete_department,
    get_user_detail,
    list_departments,
    list_officers,
    list_users,
    update_department_description,
    update_user_role,
    update_user_status,
)
from ..services.complaint_service import export_complaints_csv
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
        DepartmentNotFoundError: 404, if department_id is given but
            doesn't match a real department.
    """
    staff = await create_staff_account(
        body.name, body.phone, body.email, body.password, db, department_id=body.department_id
    )
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


@router.get(
    "/export",
    summary="Export filtered complaints as CSV (admin only)",
)
async def export_complaints_route(
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    category: Optional[ComplaintCategory] = Query(None),
    ward_code: Optional[str] = Query(None, max_length=5),
    assigned_to: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Streams back every complaint matching the given filters as a CSV
    file, same filter set as GET /complaints. Not wrapped in the usual
    SuccessResponse envelope, the response body is the file itself,
    same reasoning uploaded attachments are served as plain files
    rather than JSON.
    """
    csv_body = await export_complaints_csv(
        current_user,
        db,
        status=status_filter.value if status_filter else None,
        category=category.value if category else None,
        ward_code=ward_code,
        assigned_to=assigned_to,
    )
    filename = f"complaints_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/users",
    response_model=SuccessResponse[UserListResponse],
    summary="List all users, any role, filterable and paginated (admin only)",
)
async def list_users_route(
    role: Optional[Literal["citizen", "staff", "admin"]] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=200, description="Matches name, email, or phone"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """List every user on the platform, not just staff (see GET /admin/officers for that)."""
    users, total = await list_users(role, is_active, search, page, per_page, db)
    return SuccessResponse[UserListResponse](
        message="Users retrieved.",
        data=UserListResponse(users=[UserOut.model_validate(u) for u in users]),
        meta={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total else 0,
        },
    )


@router.get(
    "/users/{user_id}",
    response_model=SuccessResponse[UserDetailResponse],
    summary="Get a user's profile plus their complaint history (admin only)",
)
async def get_user_detail_route(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    complaints covers both directions a user can relate to a
    complaint: ones a citizen filed, or ones assigned to a staff
    member, whichever applies to this user's role.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
    """
    user, complaints = await get_user_detail(user_id, db)
    return SuccessResponse[UserDetailResponse](
        message="User retrieved.",
        data=UserDetailResponse(
            user=UserOut.model_validate(user),
            complaints=[UserComplaintSummary.model_validate(c) for c in complaints],
        ),
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=SuccessResponse[UserOut],
    summary="Activate or deactivate a user (admin only)",
)
async def update_user_status_route(
    user_id: UUID,
    body: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        CannotModifySelfError: 409, deactivating your own account is a
            self-lockout risk.
        CannotDeactivateLastAdminError: 409, if this would leave the
            platform with zero active admins.
    """
    user = await update_user_status(user_id, body.is_active, current_user, db)
    await db.commit()

    return SuccessResponse[UserOut](
        message="User status updated.",
        data=UserOut.model_validate(user),
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=SuccessResponse[UserOut],
    summary="Change a user's role between citizen and staff (admin only)",
)
async def update_user_role_route(
    user_id: UUID,
    body: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    role only accepts citizen/staff (enforced by the request schema),
    promoting to admin isn't possible through this endpoint at all.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        CannotModifySelfError: 409, changing your own role is a
            self-lockout risk.
        CannotChangeAdminRoleError: 409, this endpoint can't touch the
            admin account's role.
    """
    user = await update_user_role(user_id, body.role, current_user, db)
    await db.commit()

    return SuccessResponse[UserOut](
        message="User role updated.",
        data=UserOut.model_validate(user),
    )


@router.patch(
    "/users/{user_id}/department",
    response_model=SuccessResponse[UserOut],
    summary="Assign or unassign a staff member's department (admin only)",
)
async def assign_staff_department_route(
    user_id: UUID,
    body: AssignStaffDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    department_id: null unassigns the staff member from whatever
    department they're currently in.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        UserNotStaffError: 409, if the user isn't a staff account.
        DepartmentNotFoundError: 404, if department_id is given but
            doesn't match a real department.
    """
    user = await assign_staff_department(user_id, body.department_id, db)
    await db.commit()

    return SuccessResponse[UserOut](
        message="Staff department updated.",
        data=UserOut.model_validate(user),
    )
