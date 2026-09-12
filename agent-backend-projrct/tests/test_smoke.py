"""基础冒烟测试：使用 pytest + httpx 验证用户接口核心链路。

覆盖范围：
1. 健康检查接口：服务存活、数据库连通性、接口文档可访问性（/docs、/redoc、/openapi.json）。
2. 用户增删改查全链路：创建 → 查询列表 → 查询详情 → 更新 → 删除。
3. 异常分支：用户不存在(404)、用户名重复(400)、参数校验失败(422)。
4. 注册接口：注册成功且密码 bcrypt 哈希入库、弱密码校验(400)、限流(429)。

运行命令：pytest tests/test_smoke.py -v
"""
import pytest
from sqlalchemy import select

from app.db.models import User
from app.security import verify_password


# ---------------------------------------------------------------------------
# 一、健康检查
# ---------------------------------------------------------------------------


class TestHealth:
    """健康检查接口冒烟测试。"""

    def test_health_ok(self, client):
        """健康检查：服务与数据库均正常时返回 200。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "healthy"
        assert body["data"]["checks"]["service"] == "ok"
        assert body["data"]["checks"]["database"] == "ok"

    def test_docs_accessible(self, client):
        """接口文档可访问性：Swagger UI (/docs) 与 ReDoc (/redoc) 均返回 200。"""
        # Swagger UI（FastAPI 默认提供）
        docs_resp = client.get("/docs")
        assert docs_resp.status_code == 200
        # ReDoc（FastAPI 默认提供）
        redoc_resp = client.get("/redoc")
        assert redoc_resp.status_code == 200
        # openapi.json 元数据接口应可访问且包含 paths 字段
        schema_resp = client.get("/openapi.json")
        assert schema_resp.status_code == 200
        assert "paths" in schema_resp.json()


# ---------------------------------------------------------------------------
# 二、用户增删改查全链路
# ---------------------------------------------------------------------------


class TestUserCRUD:
    """用户增删改查接口冒烟测试。"""

    def test_create_user(self, client):
        """创建用户：返回 201，响应体包含用户信息，不含密码。"""
        resp = client.post(
            "/api/v1/users/",
            json={"username": "alice", "password": "secret123"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "用户创建成功"
        user = body["data"]
        assert user["username"] == "alice"
        assert "id" in user
        assert "password" not in user  # 响应体不暴露密码
        assert "create_time" in user

    def test_list_users(self, client):
        """查询用户列表：返回 200，列表包含已创建用户。"""
        # 先创建两个用户
        client.post(
            "/api/v1/users/", json={"username": "alice", "password": "secret123"}
        )
        client.post(
            "/api/v1/users/", json={"username": "bob", "password": "bobpass456"}
        )
        resp = client.get("/api/v1/users/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        users = body["data"]
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert usernames == {"alice", "bob"}

    def test_get_user(self, client):
        """查询单个用户：返回 200，数据正确。"""
        create_resp = client.post(
            "/api/v1/users/", json={"username": "alice", "password": "secret123"}
        )
        user_id = create_resp.json()["data"]["id"]
        resp = client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["username"] == "alice"

    def test_update_user(self, client):
        """更新用户：返回 200，用户名与密码更新生效。"""
        create_resp = client.post(
            "/api/v1/users/", json={"username": "alice", "password": "secret123"}
        )
        user_id = create_resp.json()["data"]["id"]
        resp = client.put(
            f"/api/v1/users/{user_id}",
            json={"username": "alice_updated", "password": "newpass789"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "用户更新成功"
        assert body["data"]["username"] == "alice_updated"

    def test_delete_user(self, client):
        """删除用户：返回 200，再次查询应 404。"""
        create_resp = client.post(
            "/api/v1/users/", json={"username": "alice", "password": "secret123"}
        )
        user_id = create_resp.json()["data"]["id"]
        # 删除
        resp = client.delete(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert resp.json()["message"] == "用户删除成功"
        # 删除后查询应返回 404
        get_resp = client.get(f"/api/v1/users/{user_id}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# 三、异常分支
# ---------------------------------------------------------------------------


class TestUserErrors:
    """用户接口异常分支冒烟测试。"""

    def test_get_user_not_found(self, client):
        """查询不存在的用户：返回 404。"""
        resp = client.get("/api/v1/users/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["code"] == 40401
        assert body["message"] == "用户不存在"

    def test_create_duplicate_username(self, client):
        """创建重复用户名：返回 400，业务码为 40001。"""
        client.post(
            "/api/v1/users/", json={"username": "alice", "password": "secret123"}
        )
        resp = client.post(
            "/api/v1/users/", json={"username": "alice", "password": "otherpass"}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40001
        assert body["message"] == "用户名已存在"

    def test_create_user_validation_short_password(self, client):
        """参数校验：密码过短返回 422。"""
        resp = client.post(
            "/api/v1/users/",
            json={"username": "alice", "password": "123"},  # 密码 < 6 位
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == 42200

    def test_create_user_validation_short_username(self, client):
        """参数校验：用户名过短返回 422。"""
        resp = client.post(
            "/api/v1/users/",
            json={"username": "a", "password": "secret123"},  # 用户名 < 2 位
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == 42200

    def test_create_user_missing_fields(self, client):
        """参数校验：缺少必填字段返回 422。"""
        resp = client.post("/api/v1/users/", json={"username": "alice"})
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200

    def test_update_user_not_found(self, client):
        """更新不存在的用户：返回 404。"""
        resp = client.put(
            "/api/v1/users/99999",
            json={"username": "ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401

    def test_delete_user_not_found(self, client):
        """删除不存在的用户：返回 404。"""
        resp = client.delete("/api/v1/users/99999")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401


# ---------------------------------------------------------------------------
# 四、注册接口（/auth/register）
# ---------------------------------------------------------------------------


class TestAuthRegister:
    """注册接口冒烟测试：成功入库、bcrypt 哈希、弱密码校验、用户名重复、限流。"""

    def test_register_success(self, client, db_session):
        """注册成功：返回 201，响应不含密码，库里存的是 bcrypt 哈希而非明文。"""
        resp = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "Goodpass1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "注册成功"
        user = body["data"]
        assert user["username"] == "newuser"
        assert "password" not in user  # 响应体不暴露密码
        assert "detail" not in body  # response_model_exclude_none：成功响应不输出 detail

        # 直查测试库：落库密码必须是 bcrypt 哈希且可校验通过，明文不落库
        db_user = db_session.scalars(
            select(User).where(User.username == "newuser")
        ).first()
        assert db_user is not None
        assert db_user.password != "Goodpass1"
        assert db_user.password.startswith("$2")  # bcrypt 哈希前缀
        assert verify_password("Goodpass1", db_user.password)

    @pytest.mark.parametrize("weak_password", ["123456", "password123", "admin123"])
    def test_register_blacklist_password(self, client, weak_password):
        """弱密码黑名单：命中常见弱密码返回 400，业务码 40002。"""
        resp = client.post(
            "/auth/register",
            json={"username": "tester", "password": weak_password},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "弱密码" in body["message"]

    @pytest.mark.parametrize("weak_password", ["secretpw", "1234567"])
    def test_register_password_must_mix_letters_and_digits(self, client, weak_password):
        """组合复杂度：纯字母或纯数字密码返回 400，提示必须同时包含字母和数字。"""
        resp = client.post(
            "/auth/register",
            json={"username": "tester", "password": weak_password},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "字母和数字" in body["message"]

    def test_register_password_contains_username(self, client):
        """关联性：密码包含用户名返回 400。"""
        resp = client.post(
            "/auth/register",
            json={"username": "alice", "password": "alice123"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "用户名" in body["message"]

    def test_register_duplicate_username(self, client):
        """注册重复用户名：复用 create_user 的唯一性校验，返回 400，业务码 40001。"""
        client.post(
            "/auth/register", json={"username": "alice", "password": "Goodpass1"}
        )
        resp = client.post(
            "/auth/register", json={"username": "alice", "password": "Anotherpass2"}
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001

    def test_register_validation_short_password(self, client):
        """参数校验：密码短于 6 位属于格式错误，返回 422。"""
        resp = client.post(
            "/auth/register",
            json={"username": "alice", "password": "a1"},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200

    def test_register_rate_limited(self, client):
        """接口限流：同一 IP 一分钟内超过 5 次注册，第 6 次返回 429，业务码 42901。"""
        # 前 5 次放行（用户名均不同、密码均合规）
        for index in range(1, 6):
            resp = client.post(
                "/auth/register",
                json={"username": f"user{index}", "password": f"Pass{index}word"},
            )
            assert resp.status_code == 201
        # 第 6 次触发固定窗口限流
        resp = client.post(
            "/auth/register",
            json={"username": "user6", "password": "Pass6word"},
        )
        assert resp.status_code == 429
        body = resp.json()
        assert body["code"] == 42901
        assert body["message"] == "请求过于频繁，请稍后再试"
        # 标准 Retry-After 头：正整数秒，且与响应体 detail 一致
        retry_after = int(resp.headers["Retry-After"])
        assert 1 <= retry_after <= 60
        assert body["detail"]["retry_after_seconds"] == retry_after
