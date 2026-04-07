from typing import Dict, Set

# Mapping hiérarchique des niveaux de permissions
PERMISSION_SETS: Dict[str, Set[str]] = {
    # "read": {"access_project", "view_form", "view_submission"},
    # "submit": {"access_project", "view_form", "view_submission", "add_submission"},
    "contribute": {
        "access_project",
        "view_form",
        "view_submission",
        "add_submission",
        "edit_submission",
        "create_form",
        "edit_form",
    },
    "manage": {
        "access_project",
        "view_form",
        "view_submission",
        "add_submission",
        "edit_submission",
        "create_form",
        "edit_form",
        "manage_project",
        "archive_project",
        "restore_project",
        "delete_form",
        "delete_submission",
    },
}

# Rôles avec accès global (bypass des permissions granulaires)
ADMIN_ROLES = ["administrator"]

# Mapping des rôles ODK vers les niveaux de permissions autorisés
ROLE_ALLOWED_LEVELS = {
    "administrator": ["manage"],
    "manager": ["contribute", "manage"],
    "insuco_user": ["contribute"],
}
