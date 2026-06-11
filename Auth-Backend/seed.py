"""Seed script for roles and permissions."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from src.config.database import SessionLocal
from src.data.models.postgres.role import Role
from src.data.models.postgres.permission import Permission
from src.data.models.postgres.role_permission import RolePermission


# Define roles
ROLES = [
    {"name": "ADMIN", "description": "System administrator"},
    {"name": "DOCTOR", "description": "Doctor"},
    {"name": "FRONT_DESK", "description": "Front desk staff"},
    {"name": "PATIENT", "description": "Patient"},
]

# Define permissions
PERMISSIONS = [
    {"name": "appointment.create", "description": "Create appointments"},
    {"name": "appointment.read", "description": "Read appointments"},
    {"name": "appointment.read_own", "description": "Read own appointments"},
    {"name": "appointment.update", "description": "Update appointments"},
    {"name": "appointment.delete", "description": "Delete appointments"},
    {"name": "schedule.manage", "description": "Manage doctor schedules"},
    {"name": "doctor.manage", "description": "Manage doctors"},
    {"name": "patient.manage", "description": "Manage patients"},
    {"name": "user.manage", "description": "Manage users"},
]

# Define role-permission mappings
ROLE_PERMISSIONS = {
    "ADMIN": [
        "appointment.create",
        "appointment.read",
        "appointment.update",
        "appointment.delete",
        "user.manage",
        "doctor.manage",
    ],
    "DOCTOR": [
        "appointment.read",
        "appointment.update",
        "schedule.manage",
    ],
    "FRONT_DESK": [
        "appointment.create",
        "appointment.read",
        "patient.manage",
    ],
    "PATIENT": [
        "appointment.read_own",
    ],
}


def seed():
    db = SessionLocal()

    try:
        # Seed roles
        role_map = {}
        for role_data in ROLES:
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(**role_data)
                db.add(role)
                db.flush()
                role_map[role.name] = role.id
                print(f"  Created role: {role.name}")
            else:
                role_map[existing.name] = existing.id
                print(f"  Role exists: {existing.name}")

        # Seed permissions
        perm_map = {}
        for perm_data in PERMISSIONS:
            existing = db.query(Permission).filter(
                Permission.name == perm_data["name"]
            ).first()
            if not existing:
                perm = Permission(**perm_data)
                db.add(perm)
                db.flush()
                perm_map[perm.name] = perm.id
                print(f"  Created permission: {perm.name}")
            else:
                perm_map[existing.name] = existing.id
                print(f"  Permission exists: {existing.name}")

        # Seed role-permissions
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role_id = role_map[role_name]
            for perm_name in permissions:
                perm_id = perm_map[perm_name]
                existing = db.query(RolePermission).filter(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == perm_id,
                ).first()
                if not existing:
                    rp = RolePermission(role_id=role_id, permission_id=perm_id)
                    db.add(rp)
                    print(f"  Assigned: {role_name} -> {perm_name}")
                else:
                    print(f"  Mapping exists: {role_name} -> {perm_name}")

        db.commit()
        print("\nSeed completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
