"""Auth API — Login, profile, change password"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import verify_password, hash_password, create_access_token, get_current_admin, decode_token
from models.admin import Admin, Role, RolePermission, Permission

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    admin = (await db.execute(
        select(Admin).where(Admin.username == data.username)
    )).scalar_one_or_none()

    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Gather permissions
    permissions = []
    is_super = False
    if admin.role_id:
        role = (await db.execute(select(Role).where(Role.id == admin.role_id))).scalar_one_or_none()
        if role:
            is_super = role.is_super
            if not is_super:
                rp_result = await db.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role.id)
                )
                permissions = [r[0] for r in rp_result.all()]

    token = create_access_token({
        "sub": str(admin.id),
        "username": admin.username,
        "is_super": is_super,
        "permissions": permissions,
    })

    return TokenResponse(
        access_token=token,
        admin={
            "id": str(admin.id),
            "username": admin.username,
            "display_name": admin.display_name or admin.username,
            "is_super": is_super,
            "telegram_id": admin.telegram_id,
        },
    )


@router.get("/me")
async def get_me(admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """Get current admin full profile"""
    import uuid
    admin_record = (await db.execute(
        select(Admin).where(Admin.id == uuid.UUID(admin["sub"]))
    )).scalar_one_or_none()

    if not admin_record:
        raise HTTPException(404, "Admin not found")

    role_name = None
    if admin_record.role_id:
        role = (await db.execute(select(Role).where(Role.id == admin_record.role_id))).scalar_one_or_none()
        role_name = role.name if role else None

    return {
        "id": str(admin_record.id),
        "username": admin_record.username,
        "display_name": admin_record.display_name,
        "telegram_id": admin_record.telegram_id,
        "is_active": admin_record.is_active,
        "role": role_name,
        "is_super": admin.get("is_super", False),
        "created_at": admin_record.created_at.isoformat() if admin_record.created_at else None,
    }


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change current admin password"""
    import uuid
    admin_record = (await db.execute(
        select(Admin).where(Admin.id == uuid.UUID(admin["sub"]))
    )).scalar_one_or_none()

    if not admin_record:
        raise HTTPException(404, "Admin not found")

    # Verify current password
    if not verify_password(data.current_password, admin_record.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")

    # Update password
    admin_record.password_hash = hash_password(data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.put("/update-profile")
async def update_profile(
    data: UpdateProfileRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update current admin profile (display name, username, telegram_id)"""
    import uuid
    admin_record = (await db.execute(
        select(Admin).where(Admin.id == uuid.UUID(admin["sub"]))
    )).scalar_one_or_none()

    if not admin_record:
        raise HTTPException(404, "Admin not found")

    # Check if new username is taken
    if data.username and data.username != admin_record.username:
        existing = (await db.execute(
            select(Admin).where(Admin.username == data.username)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(400, "Username already taken")
        admin_record.username = data.username

    if data.display_name is not None:
        admin_record.display_name = data.display_name

    if data.telegram_id is not None:
        admin_record.telegram_id = data.telegram_id

    await db.commit()

    # Generate new token with updated username
    is_super = admin.get("is_super", False)
    permissions = admin.get("permissions", [])
    new_token = create_access_token({
        "sub": str(admin_record.id),
        "username": admin_record.username,
        "is_super": is_super,
        "permissions": permissions,
    })

    return {
        "message": "Profile updated successfully",
        "access_token": new_token,
        "admin": {
            "id": str(admin_record.id),
            "username": admin_record.username,
            "display_name": admin_record.display_name or admin_record.username,
            "is_super": is_super,
            "telegram_id": admin_record.telegram_id,
        },
    }
