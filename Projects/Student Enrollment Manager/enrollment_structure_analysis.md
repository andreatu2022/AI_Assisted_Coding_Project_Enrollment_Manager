# Enrollment Manager Structure Analysis

## Structural Issues

| Structural Issue | Where It Appears | Why It Hurts Scalability / Maintainability | Layer Problem | Better Future Design |
|------------------|------------------|-------------------------------------------|----------------|----------------------|
| Global config mixed with logic | DB_PATH, SNAPSHOT_PATH, CURRENT_STUDENT, statuses | Hard to reuse and test because environment details and fake data are tied to logic | Mixed responsibility | Move to constants/config layer |
| Sample data mixed with real logic | AVAILABLE_COURSE_KEYS, SAMPLE_ENROLLMENTS, seed_sample_data | Confuses test vs production data and makes scaling harder | Config + DB mixed | Separate seed data from DB logic |
| DB functions know business rules | get_student_enrollments, soft_unenroll_student, enroll_with_key | Changing business rules requires editing SQL functions | DB doing service work | Service defines rules, DB only handles data |
| Too many responsibilities in one function | enroll_with_key | Hard to debug and extend because validation, lookup, update, and return are combined | Cross-layer mixing | Split into service + database functions |
| Business decision inside DB update | soft_unenroll_student | “Soft delete” is a business rule, not a DB concern | Cross-layer mixing | Service decides behavior, DB executes update |
| SQL tied to dashboard meaning | get_student_enrollments, get_student_summary | Adding new statuses or meanings requires changes in multiple places | DB + service overlap | DB returns raw data, service interprets |
| Indirect DB dependency in service | get_student_summary | Harder to scale summaries or optimize queries later | Service depends on DB logic | Service should clearly control aggregation |
| Export mixes multiple concerns | export_database_snapshot | Combines DB reads, formatting, and file writing in one place | Cross-layer mixing | Separate export logic from data retrieval |
| Main function does everything | main | Not scalable—handles setup, actions, and output | Mixed responsibilities | Keep as simple app entry point |
| Repeated DB connections | connect() used everywhere | Harder to manage transactions and optimize performance later | DB design issue | Centralize connection handling in DB class |
| Helper functions floating globally | rows_to_dicts | Reduces organization and clarity of DB layer | Poor separation | Move into DB layer |
| No structured data models | Functions return dicts | Risky if schema changes—breaks downstream logic | Data design issue | Define consistent data structures |
| Constants not organized | Paths, statuses, sample data | Different types of constants are grouped together | Config issue | Separate by purpose (config vs business vs sample) |

---

## Key Takeaway

The core issue is **layer mixing**:

- Database layer is making **business decisions**
- Service logic is embedded inside SQL-based functions
- Config, data, and execution flow are all in one file

### Ideal Structure

- **Database Layer** → SQL + connections only  
- **Service Layer** → Business rules + logic  
- **Config Layer** → Constants and settings  
- **App Layer** → Controls flow (main)

This separation improves:
- Scalability  
- Maintainability  
- Readability  
