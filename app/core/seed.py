# app/core/seed.py
import asyncio
from typing import Dict, List
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import Permission, Role, RolePermission, User

# 1. Seven Approved Core Roles from Specification (04.5.8)
CORE_ROLES = [
    {"role_code": "SCHOOL_ADMIN", "role_name": "School Administrator", "is_system_role": True},
    {"role_code": "DIRECTOR", "role_name": "School Director", "is_system_role": True},
    {"role_code": "FLOOR_SUPERVISOR", "role_name": "Floor Supervisor", "is_system_role": True},
    {"role_code": "TEACHER", "role_name": "Teacher", "is_system_role": True},
    {"role_code": "ASSISTANT_TEACHER", "role_name": "Assistant Teacher", "is_system_role": True},
    {"role_code": "STUDENT", "role_name": "Student", "is_system_role": True},
    {"role_code": "PARENT", "role_name": "Parent / Guardian", "is_system_role": True},
]

# 2. Permissions Grouped by Module
PERMISSIONS_DATA = [
    # Administration Permissions
    {"permission_code": "VIEW_USERS", "permission_name": "View User Accounts", "module_category": "ADMIN"},
    {"permission_code": "CREATE_USERS", "permission_name": "Create User Accounts", "module_category": "ADMIN"},
    {"permission_code": "EDIT_USERS", "permission_name": "Edit User Accounts", "module_category": "ADMIN"},
    {"permission_code": "ACTIVATE_USERS", "permission_name": "Activate User Accounts", "module_category": "ADMIN"},
    {"permission_code": "DEACTIVATE_USERS", "permission_name": "Deactivate User Accounts", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_STUDENTS", "permission_name": "Manage Student Records", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_TEACHERS", "permission_name": "Manage Teacher Accounts", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_PARENTS", "permission_name": "Manage Parent Accounts", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_ASSISTANT_TEACHERS", "permission_name": "Manage Assistant Teachers", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_FLOOR_SUPERVISORS", "permission_name": "Manage Floor Supervisors", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_PARENT_STUDENT_RELATIONSHIPS", "permission_name": "Manage Parent-Student Links", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_ACADEMIC_STRUCTURE", "permission_name": "Manage Academic Structure", "module_category": "ADMIN"},
    {"permission_code": "MANAGE_SCHOOL_SETTINGS", "permission_name": "Manage School Settings", "module_category": "ADMIN"},
    {"permission_code": "VIEW_AUDIT_LOGS", "permission_name": "View Audit Records", "module_category": "ADMIN"},
    {"permission_code": "EXPORT_AUDIT_LOGS", "permission_name": "Export Audit Logs", "module_category": "ADMIN"},

    # Attendance Permissions
    {"permission_code": "VIEW_ATTENDANCE", "permission_name": "View Attendance Records", "module_category": "ATTENDANCE"},
    {"permission_code": "RECORD_ATTENDANCE", "permission_name": "Record Daily Attendance", "module_category": "ATTENDANCE"},
    {"permission_code": "MODIFY_ATTENDANCE", "permission_name": "Modify Attendance Records", "module_category": "ATTENDANCE"},
    {"permission_code": "APPROVE_LATE", "permission_name": "Approve Late Arrival", "module_category": "ATTENDANCE"},
    {"permission_code": "APPROVE_EXCUSED", "permission_name": "Approve Excused Absence", "module_category": "ATTENDANCE"},
    {"permission_code": "VIEW_ATTENDANCE_REPORTS", "permission_name": "View Attendance Reports", "module_category": "ATTENDANCE"},

    # Homework Permissions
    {"permission_code": "VIEW_HOMEWORK", "permission_name": "View Homework Assignments", "module_category": "HOMEWORK"},
    {"permission_code": "CREATE_HOMEWORK", "permission_name": "Create Homework Assignments", "module_category": "HOMEWORK"},
    {"permission_code": "PUBLISH_HOMEWORK", "permission_name": "Publish Homework", "module_category": "HOMEWORK"},
    {"permission_code": "EDIT_HOMEWORK", "permission_name": "Edit Homework", "module_category": "HOMEWORK"},
    {"permission_code": "SUBMIT_HOMEWORK", "permission_name": "Submit Homework Solutions", "module_category": "HOMEWORK"},
    {"permission_code": "REVIEW_HOMEWORK_SUBMISSIONS", "permission_name": "Review Homework Submissions", "module_category": "HOMEWORK"},
    {"permission_code": "GRADE_HOMEWORK", "permission_name": "Grade Homework and Give Feedback", "module_category": "HOMEWORK"},
    {"permission_code": "VIEW_SUBMISSION_HISTORY", "permission_name": "View Submission History", "module_category": "HOMEWORK"},

    # Exams Permissions
    {"permission_code": "VIEW_EXAMS", "permission_name": "View Examination Details", "module_category": "EXAM"},
    {"permission_code": "CREATE_EXAMS", "permission_name": "Create Examinations", "module_category": "EXAM"},
    {"permission_code": "EDIT_EXAMS", "permission_name": "Edit Examinations", "module_category": "EXAM"},
    {"permission_code": "MANAGE_EXAM_QUESTIONS", "permission_name": "Manage Examination Questions", "module_category": "EXAM"},
    {"permission_code": "PUBLISH_EXAMS", "permission_name": "Publish Examinations", "module_category": "EXAM"},
    {"permission_code": "TAKE_EXAM", "permission_name": "Take Online Examination", "module_category": "EXAM"},
    {"permission_code": "VIEW_EXAM_RESULTS", "permission_name": "View Exam Results", "module_category": "EXAM"},
    {"permission_code": "REOPEN_EXAM", "permission_name": "Reopen Exam for Exceptional Cases", "module_category": "EXAM"},
    {"permission_code": "EXTEND_EXAM_TIME", "permission_name": "Extend Examination Time", "module_category": "EXAM"},

    # Grades Permissions
    {"permission_code": "VIEW_GRADES", "permission_name": "View Official Academic Results", "module_category": "GRADES"},
    {"permission_code": "PREPARE_ACADEMIC_RESULT", "permission_name": "Prepare Term Marks", "module_category": "GRADES"},
    {"permission_code": "UPLOAD_OFFICIAL_RESULT", "permission_name": "Upload/Publish Authoritative Results", "module_category": "GRADES"},

    # Communication Permissions
    {"permission_code": "SEND_PRIVATE_MESSAGE", "permission_name": "Send Private Message", "module_category": "COMMUNICATION"},
    {"permission_code": "RECEIVE_PRIVATE_MESSAGE", "permission_name": "Receive Private Message", "module_category": "COMMUNICATION"},
    {"permission_code": "COMMUNICATE_WITH_STUDENTS", "permission_name": "Communicate With Students", "module_category": "COMMUNICATION"},
    {"permission_code": "COMMUNICATE_WITH_PARENTS", "permission_name": "Communicate With Parents", "module_category": "COMMUNICATION"},
    {"permission_code": "COMMUNICATE_WITH_TEACHERS", "permission_name": "Communicate With Teachers", "module_category": "COMMUNICATION"},

    # Dashboard & Reports
    {"permission_code": "VIEW_DASHBOARD", "permission_name": "View Dashboard Overview", "module_category": "DASHBOARD"},
    {"permission_code": "VIEW_REPORTS", "permission_name": "View Reports", "module_category": "DASHBOARD"},
    {"permission_code": "EXPORT_REPORTS", "permission_name": "Export Authorized Reports", "module_category": "DASHBOARD"},
]

# 3. Role-to-Permission Mapping Matrix according to the document
ROLE_PERMISSIONS_MAP: Dict[str, List[str]] = {
    "SCHOOL_ADMIN": [
        "VIEW_USERS", "CREATE_USERS", "EDIT_USERS", "ACTIVATE_USERS", "DEACTIVATE_USERS",
        "MANAGE_STUDENTS", "MANAGE_TEACHERS", "MANAGE_PARENTS", "MANAGE_ASSISTANT_TEACHERS",
        "MANAGE_FLOOR_SUPERVISORS", "MANAGE_PARENT_STUDENT_RELATIONSHIPS", "MANAGE_ACADEMIC_STRUCTURE",
        "MANAGE_SCHOOL_SETTINGS", "VIEW_AUDIT_LOGS", "EXPORT_AUDIT_LOGS", "VIEW_ATTENDANCE",
        "VIEW_ATTENDANCE_REPORTS", "UPLOAD_OFFICIAL_RESULT", "VIEW_GRADES", "VIEW_DASHBOARD",
        "VIEW_REPORTS", "EXPORT_REPORTS", "COMMUNICATE_WITH_PARENTS", "COMMUNICATE_WITH_TEACHERS",
    ],
    "DIRECTOR": [
        "VIEW_USERS", "VIEW_ATTENDANCE", "MODIFY_ATTENDANCE", "APPROVE_LATE", "APPROVE_EXCUSED",
        "VIEW_ATTENDANCE_REPORTS", "VIEW_HOMEWORK", "VIEW_EXAMS", "VIEW_EXAM_RESULTS",
        "REOPEN_EXAM", "EXTEND_EXAM_TIME", "VIEW_GRADES", "VIEW_AUDIT_LOGS", "VIEW_DASHBOARD",
        "VIEW_REPORTS", "COMMUNICATE_WITH_PARENTS", "COMMUNICATE_WITH_TEACHERS",
    ],
    "FLOOR_SUPERVISOR": [
        "VIEW_ATTENDANCE", "RECORD_ATTENDANCE", "VIEW_ATTENDANCE_REPORTS", "VIEW_DASHBOARD",
    ],
    "TEACHER": [
        "VIEW_HOMEWORK", "CREATE_HOMEWORK", "PUBLISH_HOMEWORK", "EDIT_HOMEWORK",
        "REVIEW_HOMEWORK_SUBMISSIONS", "GRADE_HOMEWORK", "VIEW_SUBMISSION_HISTORY",
        "VIEW_EXAMS", "CREATE_EXAMS", "EDIT_EXAMS", "MANAGE_EXAM_QUESTIONS", "PUBLISH_EXAMS",
        "VIEW_EXAM_RESULTS", "REOPEN_EXAM", "EXTEND_EXAM_TIME", "PREPARE_ACADEMIC_RESULT",
        "VIEW_GRADES", "SEND_PRIVATE_MESSAGE", "RECEIVE_PRIVATE_MESSAGE",
        "COMMUNICATE_WITH_STUDENTS", "COMMUNICATE_WITH_PARENTS", "VIEW_DASHBOARD",
    ],
    "ASSISTANT_TEACHER": [
        "VIEW_HOMEWORK", "REVIEW_HOMEWORK_SUBMISSIONS", "VIEW_SUBMISSION_HISTORY",
        "VIEW_EXAMS", "VIEW_EXAM_RESULTS", "SEND_PRIVATE_MESSAGE", "RECEIVE_PRIVATE_MESSAGE",
        "COMMUNICATE_WITH_STUDENTS", "COMMUNICATE_WITH_TEACHERS", "VIEW_DASHBOARD",
    ],
    "STUDENT": [
        "VIEW_HOMEWORK", "SUBMIT_HOMEWORK", "VIEW_SUBMISSION_HISTORY", "VIEW_EXAMS",
        "TAKE_EXAM", "VIEW_EXAM_RESULTS", "VIEW_GRADES", "SEND_PRIVATE_MESSAGE",
        "RECEIVE_PRIVATE_MESSAGE", "COMMUNICATE_WITH_TEACHERS", "VIEW_DASHBOARD",
    ],
    "PARENT": [
        "VIEW_ATTENDANCE", "VIEW_HOMEWORK", "VIEW_EXAMS", "VIEW_EXAM_RESULTS",
        "VIEW_GRADES", "SEND_PRIVATE_MESSAGE", "RECEIVE_PRIVATE_MESSAGE",
        "COMMUNICATE_WITH_TEACHERS", "VIEW_DASHBOARD",
    ],
}


async def seed_data():
    async with AsyncSessionLocal() as session:
        # 1. Seed or fetch Permissions
        permissions_map: Dict[str, Permission] = {}
        for p_data in PERMISSIONS_DATA:
            stmt = select(Permission).where(Permission.permission_code == p_data["permission_code"])
            perm = (await session.execute(stmt)).scalar_one_or_none()
            if not perm:
                perm = Permission(**p_data)
                session.add(perm)
                await session.flush()
            permissions_map[perm.permission_code] = perm

        # 2. Seed or fetch Roles
        roles_map: Dict[str, Role] = {}
        for r_data in CORE_ROLES:
            stmt = select(Role).where(Role.role_code == r_data["role_code"])
            role = (await session.execute(stmt)).scalar_one_or_none()
            if not role:
                role = Role(**r_data)
                session.add(role)
                await session.flush()
            roles_map[role.role_code] = role

        # 3. Explicitly seed RolePermission records directly (avoids async lazy-load trigger)
        for role_code, perm_codes in ROLE_PERMISSIONS_MAP.items():
            role = roles_map[role_code]
            for code in perm_codes:
                perm = permissions_map.get(code)
                if not perm:
                    continue
                # Check if mapping already exists in junction table
                rp_stmt = select(RolePermission).where(
                    RolePermission.role_id == role.role_id,
                    RolePermission.permission_id == perm.permission_id,
                )
                existing_rp = (await session.execute(rp_stmt)).scalar_one_or_none()
                if not existing_rp:
                    session.add(RolePermission(role_id=role.role_id, permission_id=perm.permission_id))

        await session.flush()

        # 4. Seed Default Administrator Account
        admin_email = "admin@school.com"
        stmt = select(User).where(User.email == admin_email)
        admin_user = (await session.execute(stmt)).scalar_one_or_none()

        if not admin_user:
            admin_role = roles_map["SCHOOL_ADMIN"]
            new_admin = User(
                username="school_admin",
                email=admin_email,
                password_hash=hash_password("Admin@123456"),
                display_name="System Administrator",
                phone="01000000000",
                is_active=True,
            )
            session.add(new_admin)
            await session.flush()

            # Insert into user_roles association directly
            from app.models.user import UserRole
            session.add(UserRole(user_id=new_admin.user_id, role_id=admin_role.role_id))

        await session.commit()
        print("Data seeded successfully: 7 Core Roles, Permissions Matrix, and Default Admin account.")


if __name__ == "__main__":
    asyncio.run(seed_data())