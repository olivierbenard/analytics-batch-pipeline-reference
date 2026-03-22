-- local Dockerize Postgres runs with one default application user
-- complex role management is probably out of scope
-- this script serves as placeholder if it becomes handy for future needs.

GRANT USAGE ON SCHEMA raw TO admin;
GRANT USAGE ON SCHEMA staging TO admin;
GRANT USAGE ON SCHEMA marts TO admin;