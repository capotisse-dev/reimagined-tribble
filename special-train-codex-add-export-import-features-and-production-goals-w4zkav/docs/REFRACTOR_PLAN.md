# Refactor Plan Notes

## Phase 0 Findings

### UI modules (ui_*.py) and direct db.py usage
- **Direct db.py imports**:
  - `ui_admin.py`
  - `ui_audit.py`
  - `ui_login.py`
  - `ui_machine_history.py`
  - `ui_master_data.py`
  - `ui_operator.py`
  - `ui_shift_handoff.py`
  - `ui_toolchanger.py`
  - `ui_top.py`
- **No direct db.py imports**:
  - `ui_action_center.py`, `ui_common.py`, `ui_dashboard.py`, `ui_gage_questions_editor.py`, `ui_gage_verification.py`,
    `ui_gages.py`, `ui_health_check.py`, `ui_leader.py`, `ui_notifications.py`, `ui_quality.py`, `ui_repeat_offenders.py`,
    `ui_risk_settings.py`, `ui_super.py`

### Audit logging usage
- `app/audit.py` wraps `db.log_audit` (SQLite audit table) and is called from multiple UI screens and stores (`ui_login.py`,
  `ui_toolchanger.py`, `ui_operator.py`, `ui_quality.py`, `ui_leader.py`, `ui_admin.py`, `ui_master_data.py`,
  `action_store.py`).
- `app/config.py` includes `AUDIT_LOG_FILE`, but primary usage is SQLite audit logs.

### Permissions enforcement
- Role and screen-based permissions live in `app/permissions.py` (`PERMISSIONS`, `ROLE_SCREEN_DEFAULTS`, `screen_access`,
  `can_edit_screen`).
- Current enforcement is mostly UI-based (screen access & button hiding), with no service-level enforcement.

### JSON files used as live data sources
- `data/users.json` (bootstrap + login validation hints)
- `data/reasons.json`
- `data/parts.json`
- `data/tool_config.json`
- `data/cost_config.json`
- `data/risk_config.json`
- `data/repeat_rules.json`
- `data/lpa_checklist.json`
- `data/gages.json`
- `data/gage_verification_questions.json`
- `data/andon_reasons.json`
- `data/defect_codes.json`
- `data/actions.json`
- `data/ncrs.json`
- `data/alerts_YYYY_MM.json`

### Excel import/export code paths
- **Exports**: `ui_shift_handoff.py` (shift handoff export), `ui_repeat_offenders.py` (repeat offenders export).
- **Imports/reads**:
  - `bootstrap.py` reads/writes monthly tool life Excel.
  - `ui_gage_verification.py` reads/writes gage verification Excel log.
  - `migrate_to_sqlite.py` reads legacy tool life Excel files.

## Approach Summary
- Introduce a `services/` layer with consistent CRUD entry points and explicit actor context.
- Enforce permissions in services with centralized checks + audit on denial.
- Add exceptions + centralized logging wrapper for UI callbacks.
- Add bootstrap defaults loader that uses JSON only when tables are empty.
- Implement consistent program/print revision services and migrations.
- Add import preview gate for Excel/CSV and wire into the first import path(s).
- Harden DB with indexes and soft delete columns via migrations, document data cleanup if needed.
- Add backup/restore utilities and minimal admin UI wiring.
- Keep UI behavior intact; refactor three representative screens end-to-end first.

## Constraint/Index Notes
- Users already enforce `username` uniqueness in schema. If existing data ever conflicts, plan is to rename duplicates with a suffix
  (`username_1`, `username_2`) before applying the unique constraint.
- New indexes target audit and revision tables; no destructive migrations are applied.
