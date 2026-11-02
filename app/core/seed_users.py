# app/core/seed_users.py
import asyncio
from datetime import date  # تم إضافة مكتبة التاريخ لتحويل النص إلى Date صحيح
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, Role, UserRole
from app.models.stakeholder import StaffMember, Student, ParentGuardian, ParentStudentRelationship


async def create_default_users():
    async with AsyncSessionLocal() as db:
        print("--- بدء إنشاء الحسابات الافتراضية وصلاحياتها ---")

        # 1. القائمة الكاملة للحسابات السبعة حسب متطلبات المشروع
        users_data = [
            {
                "email": "admin@school.com",
                "password": "Admin123456!",
                "display_name": "نظام المسؤول الرئيسي",
                "role_code": "SCHOOL_ADMIN",
            },
            {
                "email": "director@school.com",
                "password": "Director123456!",
                "display_name": "المدير التنفيذي",
                "role_code": "DIRECTOR",
            },
            {
                "email": "supervisor@school.com",
                "password": "Supervisor123456!",
                "display_name": "مشرف الطابق",
                "role_code": "FLOOR_SUPERVISOR",
            },
            {
                "email": "teacher@school.com",
                "password": "Teacher123456!",
                "display_name": "الأستاذ أحمد",
                "role_code": "TEACHER",
            },
            {
                "email": "assistant@school.com",
                "password": "Assistant123456!",
                "display_name": "المساعد المدرسي",
                "role_code": "ASSISTANT_TEACHER",
            },
            {
                "email": "student@school.com",
                "password": "Student123456!",
                "display_name": "الطالب يوسف",
                "role_code": "STUDENT",
            },
            {
                "email": "parent@school.com",
                "password": "Parent123456!",
                "display_name": "ولي الأمر (الأب)",
                "role_code": "PARENT",
            },
        ]

        created_users = {}

        for data in users_data:
            # التحقق مما إذا كان المستخدم موجوداً مسبقاً
            existing_user = (
                await db.execute(select(User).where(User.email == data["email"]))
            ).scalar_one_or_none()

            if existing_user:
                print(f"المستخدم {data['email']} موجود بالفعل.")
                created_users[data["role_code"]] = existing_user
                continue

            # جلب الدور من قاعدة البيانات
            role = (
                await db.execute(select(Role).where(Role.role_code == data["role_code"]))
            ).scalar_one_or_none()

            if not role:
                print(f"تحذير: الدور {data['role_code']} غير موجود في جدول الأدوار (Roles)! تأكد من تهيئته أولاً.")
                continue

            # استخراج الـ username من البريد الإلكتروني لتجنب خطأ الـ NotNullViolation
            username_from_email = data["email"].split("@")[0]

            # إنشاء المستخدم وتشفير كلمة المرور
            new_user = User(
                email=data["email"],
                username=username_from_email,
                password_hash=hash_password(data["password"]),
                display_name=data["display_name"],
                is_active=True,
            )
            db.add(new_user)
            await db.flush()

            # ربط الدور بالمستخدم
            user_role = UserRole(user_id=new_user.user_id, role_id=role.role_id)
            db.add(user_role)

            created_users[data["role_code"]] = new_user
            print(f"تم إنشاء المستخدم: {data['email']} بدور [{data['role_code']}] بنجاح.")

        # 2. إنشاء البروفايلات التابعة (Stakeholders) وربط ولي الأمر بالطالب رسمياً
        student_user = created_users.get("STUDENT")
        parent_user = created_users.get("PARENT")
        teacher_user = created_users.get("TEACHER")
        supervisor_user = created_users.get("FLOOR_SUPERVISOR")
        assistant_user = created_users.get("ASSISTANT_TEACHER")

        # بروفايل الطالب (تم تحويل تاريخ الميلاد إلى كائن date لتوافق asyncpg)
        if student_user:
            student_profile = (
                await db.execute(select(Student).where(Student.user_id == student_user.user_id))
            ).scalar_one_or_none()
            if not student_profile:
                student_profile = Student(
                    user_id=student_user.user_id,
                    student_code="STD-2026-001",
                    first_name="يوسف",
                    last_name="أحمد",
                    date_of_birth=date(2015, 5, 10),  # استخدام date object بدلاً من string
                    gender="MALE",
                    status="ACTIVE",
                )
                db.add(student_profile)
                await db.flush()
                print("تم إنشاء بروفايل الطالب بنجاح.")

        # بروفايل ولي الأمر والربط الرسمي مع الطالب
        if parent_user and student_user:
            parent_profile = (
                await db.execute(select(ParentGuardian).where(ParentGuardian.user_id == parent_user.user_id))
            ).scalar_one_or_none()
            if not parent_profile:
                parent_profile = ParentGuardian(user_id=parent_user.user_id, parent_code="PAR-2026-001")
                db.add(parent_profile)
                await db.flush()
                print("تم إنشاء بروفايل ولي الأمر بنجاح.")

            student_record = (
                await db.execute(select(Student).where(Student.user_id == student_user.user_id))
            ).scalar_one_or_none()
            
            if student_record and parent_profile:
                existing_rel = (
                    await db.execute(
                        select(ParentStudentRelationship).where(
                            ParentStudentRelationship.parent_guardian_id == parent_profile.parent_guardian_id,
                            ParentStudentRelationship.student_id == student_record.student_id,
                        )
                    )
                ).scalar_one_or_none()

                if not existing_rel:
                    rel = ParentStudentRelationship(
                        parent_guardian_id=parent_profile.parent_guardian_id,
                        student_id=student_record.student_id,
                        relationship_type="FATHER",
                        is_primary=True,
                        is_active=True,
                    )
                    db.add(rel)
                    print("تم إنشاء الربط الرسمي بين ولي الأمر والطالب بنجاح.")

        # بروفايل المعلم
        if teacher_user:
            t_profile = (
                await db.execute(select(StaffMember).where(StaffMember.user_id == teacher_user.user_id))
            ).scalar_one_or_none()
            if not t_profile:
                db.add(StaffMember(user_id=teacher_user.user_id, employee_code="TCH-001", staff_type="TEACHER"))
                print("تم إنشاء بروفايل المعلم بنجاح.")

        # بروفايل مشرف الطابق
        if supervisor_user:
            s_profile = (
                await db.execute(select(StaffMember).where(StaffMember.user_id == supervisor_user.user_id))
            ).scalar_one_or_none()
            if not s_profile:
                db.add(StaffMember(user_id=supervisor_user.user_id, employee_code="SUP-001", staff_type="FLOOR_SUPERVISOR"))
                print("تم إنشاء بروفايل مشرف الطابق بنجاح.")

        # بروفايل المساعد المدرسي
        if assistant_user:
            a_profile = (
                await db.execute(select(StaffMember).where(StaffMember.user_id == assistant_user.user_id))
            ).scalar_one_or_none()
            if not a_profile:
                db.add(StaffMember(user_id=assistant_user.user_id, employee_code="AST-001", staff_type="ASSISTANT_TEACHER"))
                print("تم إنشاء بروفايل المساعد المدرسي بنجاح.")

        await db.commit()
        print("--- تمت عملية إدخال الحسابات والبيانات الافتراضية بنجاح تام! ---")


if __name__ == "__main__":
    asyncio.run(create_default_users())


    # School Administrator: admin@school.com | Password: Admin123456!   
    # Director: director@school.com | Password: Director123456!  
    # Floor Supervisor: supervisor@school.com | Password: Supervisor123456!  
    # Teacher: teacher@school.com | Password: Teacher123456!  
    # Assistant Teacher: assistant@school.com | Password: Assistant123456!  
    # Student: student@school.com | Password: Student123456! 
    # Parent / Guardian: parent@school.com | Password: Parent123456! 