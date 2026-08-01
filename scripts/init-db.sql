-- 数据库初始化：仅在 Postgres 数据卷为空时由官方镜像自动执行一次。
-- pgvector 扩展必须在建表之前存在，否则 vector 类型不可用。
CREATE EXTENSION IF NOT EXISTS vector;

-- 用于文档名、片段内容的模糊匹配，M3 混合检索会用到
CREATE EXTENSION IF NOT EXISTS pg_trgm;
