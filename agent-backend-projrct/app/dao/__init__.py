"""DAO 层：数据库操作层，封装所有 SQLAlchemy Session 操作。

层级单向依赖：router → service → dao → model，禁止跨层反向调用。
Service 只处理业务逻辑，不直接操作 Session、写 SQL 语句；事务由 DAO 统一封装。
"""
