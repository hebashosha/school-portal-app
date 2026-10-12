from app.models.base import Base, TimestampMixin

# 1-5: Identity & RBAC
from app.models.user import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
)

# 6-9: Stakeholders
from app.models.stakeholder import (
    Student,
    StaffMember,
    ParentGuardian,
    ParentStudentRelationship,
)

# 10-15: Academic (No Sections - Direct Class)
from app.models.academic import (
    AcademicYear,
    Grade,
    ClassModel,
    Subject,
    StudentEnrollment,
    StaffAllocation,
)

# 16-18: Attendance
from app.models.attendance import (
    AttendanceOccurrence,
    AttendanceRecord,
    AttendanceChangeRequest,
)

# 19-22: Coursework / Assignments
from app.models.coursework import (
    Assignment,
    AssignmentAttachment,
    AssignmentSubmission,
    SubmissionAttachment,
)

# 23-29: Exams
from app.models.exam import (
    Exam,
    ExamQuestion,
    ExamQuestionOption,
    ExamAttempt,
    ExamAttemptException,
    ExamAnswer,
    ExamResult,
)

# 30-32: Official Grades
from app.models.grade import (
    OfficialResultPeriod,
    SubjectTermResult,
    OfficialReportCard,
)

# 33-36: Announcements
from app.models.announcement import (
    Announcement,
    AnnouncementRoleTarget,
    AnnouncementAttachment,
    AnnouncementRead,
)

# 37-41: Communications & Meetings
from app.models.communication import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    Meeting,
)

# 42-43: System Settings & Auditing
from app.models.system import (
    SchoolSetting,
    AuditLog,
)

__all__ = [
    "Base",
    "TimestampMixin",
    # 1-5
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # 6-9
    "Student",
    "StaffMember",
    "ParentGuardian",
    "ParentStudentRelationship",
    # 10-15
    "AcademicYear",
    "Grade",
    "ClassModel",
    "Subject",
    "StudentEnrollment",
    "StaffAllocation",
    # 16-18
    "AttendanceOccurrence",
    "AttendanceRecord",
    "AttendanceChangeRequest",
    # 19-22
    "Assignment",
    "AssignmentAttachment",
    "AssignmentSubmission",
    "SubmissionAttachment",
    # 23-29
    "Exam",
    "ExamQuestion",
    "ExamQuestionOption",
    "ExamAttempt",
    "ExamAttemptException",
    "ExamAnswer",
    "ExamResult",
    # 30-32
    "OfficialResultPeriod",
    "SubjectTermResult",
    "OfficialReportCard",
    # 33-36
    "Announcement",
    "AnnouncementRoleTarget",
    "AnnouncementAttachment",
    "AnnouncementRead",
    # 37-41
    "Conversation",
    "ConversationParticipant",
    "Message",
    "MessageAttachment",
    "Meeting",
    # 42-43
    "SchoolSetting",
    "AuditLog",
]