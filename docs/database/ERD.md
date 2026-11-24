# ER Diagram

Schema version 1. SQLite implementation: `backend/app/db/database.py`.

```mermaid
erDiagram
    USERS o|--o{ PROJECTS : owns
    PROJECTS ||--o{ ASSETS : contains
    PROJECTS ||--o{ GENERATION_TASKS : tracks
    PACKAGING_TEMPLATES o|--o{ PROJECTS : selected_for
    ASSETS o|--o{ GENERATION_TASKS : input_for
    ASSETS o|--o{ GENERATION_TASKS : output_of

    USERS {
        text id PK
        text email UK "nullable until account feature"
        text created_at
    }
    PROJECTS {
        text id PK "random UUID"
        text user_id FK "nullable"
        text guest_token_hash
        text template_id FK "nullable"
        text name
        text style
        text settings_json
        text status
        text created_at
        text updated_at
    }
    ASSETS {
        text id PK "random UUID"
        text project_id FK
        text asset_type
        text storage_key UK
        text mime_type
        integer size_bytes
        text metadata_json
        text created_at
    }
    GENERATION_TASKS {
        text id PK "random UUID"
        text project_id FK
        text task_type
        text status
        text input_asset_id FK "nullable"
        text output_asset_id FK "nullable"
        text provider
        text parameters_json
        integer attempts
        text error_message "nullable"
        text created_at
        text started_at "nullable"
        text finished_at "nullable"
    }
    PACKAGING_TEMPLATES {
        text id PK
        text name
        text style
        text template_path
        text placement_json
        text version
        integer available
        text created_at
    }
```

`USERS` exists only as a future owner table; no registration, login, password, or account API is implemented. Guest projects use a random project UUID plus a 256-bit capability token. Only the SHA-256 token hash is stored in SQLite. The plaintext token is returned once at creation and retained by the frontend for that browser origin. Migration v2 adds `projects.template_id`; new projects select the available template for their style.

`settings_json`, `metadata_json`, and `parameters_json` keep MVP settings flexible while their owning project/asset/task remain relational. Files themselves are never stored as SQLite BLOBs.