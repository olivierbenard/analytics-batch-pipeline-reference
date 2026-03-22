CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging; -- dbt can also creates the schemas if not existing (see: `dbt_project.yml`)
CREATE SCHEMA IF NOT EXISTS marts;