# Backend Refactor Plan

## Goal

Refactor the current procedural student enrollment backend into an object-oriented, layered design.

The main goal is to separate responsibilities so that:

- The **database layer** focuses only on SQLite connections, row queries, inserts, and updates.
- The **service layer** owns business meaning, including enrollment-key validation, dashboard meaning, student actions, and summary counting.
- The **config/constants layer** stores paths, statuses, and sample values.
- The **runner/app layer** only controls the flow of the program.

---

## Most Important Findings

The core issue is **layer mixing**:

| Finding | Why It Matters |
|---|---|
| Database layer is making business decisions | SQL functions are deciding what counts as active enrollment or unenrollment, which should be service logic. |
| Service logic is embedded inside SQL-based functions | Functions like `enroll_with_key` combine validation, lookup, insert/update, and return meaning. |
| Config, data, and execution flow are all in one file | This makes the file harder to scale, test, reuse, and maintain. |

---

## Target Layered Design

| Layer | Responsibility | Should Know | Should Not Know |
|---|---|---|---|
| Config / Constants | Store paths, statuses, and sample values | Database path, snapshot path, status names, sample student/course data | SQL logic, enrollment rules, dashboard logic |
| Database Class | Handle SQLite row-level work | SQL queries, inserts, updates, table creation, row conversion | Business meaning, dashboard interpretation, enrollment-key validation |
| Service Class | Handle enrollment business logic | Enrollment rules, validation, summaries, dashboard meaning, student actions | SQL details, database file path, raw connection handling |
| Runner / App Layer | Run the program flow | Which service method to call and when | SQL queries, business rule details, database internals |

---

## Refactor Steps

| Step | Change | Purpose |
|---|---|---|
| 1 | Create a constants/config section or file | Separate paths, statuses, and sample data from logic |
| 2 | Create an `EnrollmentDatabase` class | Move SQLite connection, table creation, seed data, and row queries into one database-focused class |
| 3 | Move SQL-only functions into the database class | Keep database work focused on rows, not business meaning |
| 4 | Create an `EnrollmentService` class | Move enrollment rules, student actions, dashboard meaning, and summaries into the service layer |
| 5 | Split `enroll_with_key` | Service validates the key and decides what should happen; database only looks up course and saves enrollment row |
| 6 | Split `soft_unenroll_student` | Service decides that unenrollment should be a status update; database performs the update |
| 7 | Move `get_student_summary` into service | Summary counting is business interpretation, not raw database access |
| 8 | Refactor dashboard-related meaning into service | Service should prepare student-facing enrolled classes, history, and summary output |
| 9 | Separate snapshot/export logic | Keep JSON writing separate from database querying and service rules |
| 10 | Simplify `main` | Main should only create objects, call setup methods, run a short test flow, and print results |

---

## Function Movement Plan

| Current Function / Responsibility | Current Problem | Future Location |
|---|---|---|
| `DB_PATH`, `SNAPSHOT_PATH` | Global config mixed with logic | Config / constants |
| `CURRENT_STUDENT` | Sample user state mixed into backend logic | Config / sample data |
| `STATUS_ENROLLED`, `STATUS_UNENROLLED` | Business constants mixed globally | Config / constants |
| `AVAILABLE_COURSE_KEYS` | Sample course data mixed with backend logic | Config / sample data |
| `SAMPLE_ENROLLMENTS` | Seed data mixed with backend logic | Config / sample data |
| `connect` | Procedural connection function | Database class |
| `create_tables` | Database schema setup | Database class |
| `seed_sample_data` | Database insert setup | Database class, using seed data |
| `rows_to_dicts` | Database helper floating globally | Database class/helper |
| `get_available_course_keys` | SQL row retrieval | Database class |
| `get_course_by_key` | SQL row lookup | Database class |
| `get_student_enrollments` | Mixes row retrieval with active-enrollment meaning | Split: database gets records, service decides dashboard meaning |
| `get_student_enrollment_history` | SQL row retrieval | Database class |
| `get_student_course_record` | SQL row lookup | Database class |
| `enroll_with_key` | Combines validation, business rule, SQL update, and return meaning | Split between service class and database class |
| `soft_unenroll_student` | Business decision mixed with DB update | Split between service class and database class |
| `get_student_summary` | Summary counting is service meaning | Service class |
| `get_all_enrollment_records` | SQL row retrieval | Database class |
| `export_database_snapshot` | Mixes DB reads, global state, formatting, and file writing | Separate snapshot/export helper |
| `main` | Runs setup, demo actions, printing, and export | Runner/app layer |

---

## Database Layer Plan

The database class should be responsible for SQLite work only.

### Database class should handle:

| Responsibility | Example |
|---|---|
| Opening database connections | Connecting to the SQLite database path |
| Creating tables | Creating `courses` and `enrollments` |
| Seeding data | Inserting sample courses and enrollments |
| Looking up rows | Finding a course by enrollment key |
| Returning rows | Returning enrollment records from SQLite |
| Updating rows | Inserting/reactivating enrollment rows or updating status |

### Database class should not handle:

| Should Not Do | Reason |
|---|---|
| Decide whether an enrollment key is valid from a business perspective | That is service validation |
| Decide what counts as a dashboard enrollment | That is student-facing meaning |
| Count summaries for the user | That is service interpretation |
| Know about the current student globally | Student data should be passed in |
| Write final dashboard meaning | Database should return rows, not presentation-ready conclusions |

---

## Service Layer Plan

The service class should own the business meaning of the enrollment system.

### Service class should handle:

| Responsibility | Example |
|---|---|
| Enrollment-key validation | Check if a key was entered and whether it matches a course |
| Student action logic | Enroll, reactivate, or unenroll a student |
| Dashboard meaning | Decide what enrolled classes, history, and summary mean for the student |
| Summary counting | Count total records, enrolled records, and unenrolled records |
| Status interpretation | Decide how `enrolled` and `unenrolled` should be interpreted |

### Service class should not handle:

| Should Not Do | Reason |
|---|---|
| Write SQL queries | SQL belongs in database layer |
| Open SQLite connections | Connection handling belongs in database layer |
| Know the database file path | Path belongs in config/database setup |
| Write JSON files directly | Exporting should be separate |
| Control the entire program flow | Main/app layer controls flow |

---

## Snapshot / Export Plan

The current snapshot function mixes several responsibilities.

| Current Issue | Refactor Direction |
|---|---|
| Uses global `CURRENT_STUDENT` | Pass student data into the snapshot builder |
| Calls database-backed functions directly | Use service/database objects intentionally |
| Builds JSON structure and writes file | Split building the snapshot from writing the file |
| Combines testing and exporting | Keep export as an optional helper |

Future design:

| Piece | Responsibility |
|---|---|
| Snapshot builder | Creates the dictionary structure |
| Snapshot writer | Writes the dictionary to JSON |
| Service/database | Provide the data used in the snapshot |

---

## Main Runner Plan

The main runner should become much smaller.

### Main should only:

| Responsibility |
|---|
| Create the database object |
| Create the service object |
| Create tables |
| Seed sample data |
| Run a short practice flow |
| Print results |
| Optionally call snapshot export |

### Main should not:

| Should Not Do |
|---|
| Contain SQL |
| Contain enrollment rules |
| Count summaries itself |
| Decide dashboard meaning |
| Manage database internals |

---

## Refactor Order

| Order | Task |
|---|---|
| 1 | Move constants and sample data into a clearly separated config area |
| 2 | Create the database class and move connection/table/seed/query functions |
| 3 | Create the service class and move business rules |
| 4 | Split mixed functions like `enroll_with_key` and `soft_unenroll_student` |
| 5 | Move summary/dashboard meaning into service |
| 6 | Separate snapshot/export logic |
| 7 | Reduce `main` into a simple runner |
| 8 | Test the same behavior as the original procedural file |

---

## Success Criteria

| Success Criteria | How to Check |
|---|---|
| Database class only handles SQL and rows | No business interpretation in database methods |
| Service class owns enrollment meaning | Enrollment validation, summary counting, and dashboard meaning are in service |
| Config is separated | Paths, statuses, and sample data are not buried in procedural logic |
| Main is simple | Main only creates objects and calls methods |
| Original behavior still works | Running the backend still creates the database, seeds data, enrolls/reactivates a student, prints summary, and exports a snapshot |
| Code is easier to extend | New statuses or dashboard rules can be added mostly in service layer |

---

## Implementation Prompt to Use After Plan Approval

Use this prompt after approving the plan:

> Refactor the procedural student enrollment backend into an object-oriented layered design. Keep the behavior the same, but reorganize the code into clear responsibilities. Create a database class that owns SQLite connection handling, table creation, seed inserts, row queries, and updates. Create a service class that owns business meaning, including enrollment-key validation, student enrollment actions, soft unenrollment decisions, dashboard meaning, and summary counting. Keep constants/config separate from logic. Keep the main runner small so it only creates objects, runs setup, demonstrates the flow, and optionally exports the snapshot. Do not add Streamlit or UI code. Keep the coding style simple and close to the starter file.
