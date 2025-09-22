# Database Migrations

This directory contains database migration files for the AI Receptionist project.

## Directory Structure

```
migrations/
├── *.sql          # Migration files (same SQL runs on both dev and prod)
├── migration_runner.py  # Script to run migrations
├── create_migration.py # Script to create new migrations
└── README.md      # This file
```

## Migration Naming Convention

Migrations should be named with the following format:
```
YYYY_MM_DD_HHMMSS_description.sql
```

Examples:
- `2025_01_15_143022_create_phone_numbers_table.sql`
- `2025_01_15_143045_add_organization_id_to_leads.sql`

## Environment-Specific Execution

- **Same SQL, Different Databases**: All migrations run the same SQL code
- **Development**: Migrations run against development Supabase database
- **Production**: Migrations run against production Supabase database
- **No Duplication**: Create migration once, runs on both environments

## Running Migrations

### Manual Execution
```bash
# Run development migrations (against dev Supabase database)
python app/migrations/migration_runner.py --env dev

# Run production migrations (against prod Supabase database)
python app/migrations/migration_runner.py --env prod
```

### Automatic Execution
Migrations run automatically during GitHub Actions deployment:
- `development` branch → runs migrations against dev Supabase database
- `main` branch → runs migrations against prod Supabase database

## Creating New Migrations

1. Create a new SQL file in the migrations folder
2. Follow the naming convention
3. Include both CREATE/ALTER statements and any necessary data migrations
4. Test locally before pushing to repository

### Using the Helper Script
```bash
# Create a new migration file
python app/migrations/create_migration.py "add user preferences table"
```

## Migration Best Practices

- Always include rollback instructions in comments
- Test migrations on development environment first
- Use transactions where possible
- Include data validation checks
- Document any breaking changes
