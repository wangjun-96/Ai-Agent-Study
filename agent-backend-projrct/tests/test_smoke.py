"""基础冒烟测试：使用 pytest + httpx 验证用户接口核心链路。

覆盖范围：
1. 健康检查接口：服务存活、数据库连通性、接口文档可访问性（/docs、/redoc、/openapi.json）。
2. 用户增删改查全链路：登录获取 JWT → 创建 → 查询列表 → 查询详情 → 更新 → 删除。
3. 鉴权分支：用户接口未登录统一 401(40104)；业务异常分支：用户不存在(404)、
   用户名重复(400)、参数校验失败(422)。
4. 注册接口：注册成功且密码 bcrypt 哈希入库、弱密码校验(400)、限流(429)；
   multipart 表单可选头像：带头像注册成功上传 MinIO 并回写 avatar，头像非法拒绝且不建号。

运行命令：pytest tests/test_smoke.py -v
"""
import base64
import hashlib

import pytest
from sqlalchemy import select

from app.db.models import User
from app.security import verify_password

# 1x1 像素合法 PNG，用于注册头像上传用例（内容固定，MD5 可直接推导）
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLv"
    "AAAAAElFTkSuQmCC"
)


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
    """用户增删改查接口冒烟测试（业务接口需登录，全部携带 JWT 访问令牌）。"""

    def test_create_user(self, client, login_user):
        """创建用户：返回 201，响应体包含用户信息，不含密码。"""
        headers, _ = login_user()
        resp = client.post(
            "/api/v1/users/",
            json={"username": "alice", "password": "secret123"},
            headers=headers,
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
        assert "detail" not in body  # response_model 序列化：成功响应不含 detail

    def test_list_users(self, client, login_user):
        """查询用户列表：返回 200，列表包含已创建用户。"""
        # 先登录（注册即创建 alice），再用其令牌创建 bob，列表恰好 2 个用户
        headers, _ = login_user("alice", "secret123")
        client.post(
            "/api/v1/users/",
            json={"username": "bob", "password": "bobpass456"},
            headers=headers,
        )
        resp = client.get("/api/v1/users/", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        users = body["data"]
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert usernames == {"alice", "bob"}

    def test_get_user(self, client, login_user):
        """查询单个用户：返回 200，数据正确。"""
        headers, user_id = login_user("alice", "secret123")
        resp = client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["username"] == "alice"

    def test_update_user(self, client, login_user):
        """更新用户：返回 200，用户名与密码更新生效。"""
        headers, user_id = login_user("alice", "secret123")
        resp = client.put(
            f"/api/v1/users/{user_id}",
            json={"username": "alice_updated", "password": "newpass789"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "用户更新成功"
        assert body["data"]["username"] == "alice_updated"

    def test_delete_user(self, client, login_user):
        """删除用户：返回 200，再次查询应 404。"""
        headers, user_id = login_user("alice", "secret123")
        # 另备一个有效账号：删除后 alice 自己的令牌会在鉴权层失效(40104)，
        # 用 bob 的有效令牌才能通过鉴权并命中"用户不存在"的 404 业务分支
        other_headers, _ = login_user("bob", "otherpass7")
        # 删除
        resp = client.delete(f"/api/v1/users/{user_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "用户删除成功"
        assert body["data"] is None  # 无数据操作保留 data: null 契约
        assert "detail" not in body
        # 删除后用其他有效账号查询：鉴权通过，资源不存在 → 404
        get_resp = client.get(f"/api/v1/users/{user_id}", headers=other_headers)
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# 三、异常分支
# ---------------------------------------------------------------------------


class TestUserAuth:
    """用户管理接口统一登录鉴权冒烟测试：未登录一律拒绝。"""

    @pytest.mark.parametrize(
        "method,path,payload",
        [
            ("GET", "/api/v1/users/", None),
            ("POST", "/api/v1/users/", {"username": "alice", "password": "secret123"}),
            ("GET", "/api/v1/users/1", None),
            ("PUT", "/api/v1/users/1", {"username": "ghost"}),
            ("DELETE", "/api/v1/users/1", None),
        ],
    )
    def test_users_api_requires_login(self, client, method, path, payload):
        """未携带访问令牌访问任一用户接口：统一返回 401(40104)，并提示 Bearer 认证。"""
        resp = client.request(method, path, json=payload)
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == 40104
        assert body["message"] == "访问令牌无效或已过期"
        assert resp.headers["WWW-Authenticate"] == "Bearer"


class TestUserErrors:
    """用户接口异常分支冒烟测试（均已登录，携带有效 JWT 访问令牌）。"""

    def test_get_user_not_found(self, client, login_user):
        """查询不存在的用户：返回 404。"""
        headers, _ = login_user()
        resp = client.get("/api/v1/users/99999", headers=headers)
        assert resp.status_code == 404
        body = resp.json()
        assert body["code"] == 40401
        assert body["message"] == "用户不存在"

    def test_create_duplicate_username(self, client, login_user):
        """创建重复用户名：返回 400，业务码为 40001。"""
        headers, _ = login_user("alice", "secret123")
        resp = client.post(
            "/api/v1/users/",
            json={"username": "alice", "password": "otherpass"},
            headers=headers,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40001
        assert body["message"] == "用户名已存在"

    def test_create_user_validation_short_password(self, client, login_user):
        """参数校验：密码过短返回 422。"""
        headers, _ = login_user()
        resp = client.post(
            "/api/v1/users/",
            json={"username": "alice", "password": "123"},  # 密码 < 6 位
            headers=headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == 42200

    def test_create_user_validation_short_username(self, client, login_user):
        """参数校验：用户名过短返回 422。"""
        headers, _ = login_user()
        resp = client.post(
            "/api/v1/users/",
            json={"username": "a", "password": "secret123"},  # 用户名 < 2 位
            headers=headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == 42200

    def test_create_user_missing_fields(self, client, login_user):
        """参数校验：缺少必填字段返回 422。"""
        headers, _ = login_user()
        resp = client.post(
            "/api/v1/users/", json={"username": "alice"}, headers=headers
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200

    def test_update_user_not_found(self, client, login_user):
        """更新不存在的用户：返回 404。"""
        headers, _ = login_user()
        resp = client.put(
            "/api/v1/users/99999",
            json={"username": "ghost"},
            headers=headers,
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401

    def test_delete_user_not_found(self, client, login_user):
        """删除不存在的用户：返回 404。"""
        headers, _ = login_user()
        resp = client.delete("/api/v1/users/99999", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401


# ---------------------------------------------------------------------------
# 四、注册接口（/api/v1/auth/register）
# ---------------------------------------------------------------------------


class TestAuthRegister:
    """注册接口冒烟测试：成功入库、bcrypt 哈希、弱密码校验、用户名重复、限流。"""

    def test_register_success(self, client, db_session):
        """注册成功：返回 201，响应不含密码，库里存的是 bcrypt 哈希而非明文。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "newuser", "password": "Goodpass1"},
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
            "/api/v1/auth/register",
            data={"username": "tester", "password": weak_password},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "弱密码" in body["message"]

    @pytest.mark.parametrize("weak_password", ["secretpw", "1234567"])
    def test_register_password_must_mix_letters_and_digits(self, client, weak_password):
        """组合复杂度：纯字母或纯数字密码返回 400，提示必须同时包含字母和数字。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "tester", "password": weak_password},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "字母和数字" in body["message"]

    def test_register_password_contains_username(self, client):
        """关联性：密码包含用户名返回 400。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "alice", "password": "alice123"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40002
        assert "用户名" in body["message"]

    def test_register_duplicate_username(self, client):
        """注册重复用户名：复用 create_user 的唯一性校验，返回 400，业务码 40001。"""
        client.post(
            "/api/v1/auth/register", data={"username": "alice", "password": "Goodpass1"}
        )
        resp = client.post(
            "/api/v1/auth/register", data={"username": "alice", "password": "Anotherpass2"}
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001

    def test_register_validation_short_password(self, client):
        """参数校验：密码短于 6 位属于格式错误，返回 422。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "alice", "password": "a1"},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200

    def test_register_rate_limited(self, client):
        """接口限流：同一 IP 一分钟内超过 5 次注册，第 6 次返回 429，业务码 42901。"""
        # 前 5 次放行（用户名均不同、密码均合规）
        for index in range(1, 6):
            resp = client.post(
                "/api/v1/auth/register",
                data={"username": f"user{index}", "password": f"Pass{index}word"},
            )
            assert resp.status_code == 201
        # 第 6 次触发固定窗口限流
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "user6", "password": "Pass6word"},
        )
        assert resp.status_code == 429
        body = resp.json()
        assert body["code"] == 42901
        assert body["message"] == "请求过于频繁，请稍后再试"
        # 标准 Retry-After 头：正整数秒，且与响应体 detail 一致
        retry_after = int(resp.headers["Retry-After"])
        assert 1 <= retry_after <= 60
        assert body["detail"]["retry_after_seconds"] == retry_after

    def test_register_without_avatar_returns_null_avatar(self, client):
        """不传头像注册：正常建号，响应 avatar 为 null。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "noavatar", "password": "Goodpass1"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["avatar"] is None

    def test_register_with_avatar_saves_file_and_updates_avatar(
        self, client, db_session, fake_minio
    ):
        """带头像注册：201 建号 + 头像上传 MinIO（{user_id}/{md5}.png）+ avatar 回写。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "avataruser", "password": "Goodpass1"},
            files={"avatar": ("my-avatar.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 201, resp.text
        user = resp.json()["data"]
        user_id = user["id"]

        # 头像路径符合 minio://{bucket}/user_{user_id}/images/{md5}.png 规则
        stored_name = f"{hashlib.md5(_PNG_BYTES).hexdigest()}.png"
        object_key = f"user_{user_id}/images/{stored_name}"
        expected_path = f"minio://ai-resource/{object_key}"
        assert user["avatar"] == expected_path

        # MinIO 对象确实写入，内容与上传字节一致
        assert object_key in fake_minio.objects
        assert fake_minio.objects[object_key][0] == _PNG_BYTES

        # 数据库 users.avatar 已回写
        db_user = db_session.scalars(
            select(User).where(User.username == "avataruser")
        ).first()
        assert db_user is not None
        assert db_user.avatar == expected_path

        # 自动登录后 /api/v1/auth/me 返回的头像与注册响应一致
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "avataruser", "password": "Goodpass1"},
        )
        token = login_resp.json()["data"]["access_token"]
        me_resp = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["avatar"] == expected_path

    def test_register_with_non_image_avatar_rejected(self, client, db_session):
        """头像为文档类型：返回 400(40003)，且不创建用户（无孤儿账号）。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "badavatar", "password": "Goodpass1"},
            files={"avatar": ("note.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40003

        # 用户未创建：同一用户名随后不带头像可正常注册成功
        assert db_session.scalars(
            select(User).where(User.username == "badavatar")
        ).first() is None
        retry_resp = client.post(
            "/api/v1/auth/register",
            data={"username": "badavatar", "password": "Goodpass1"},
        )
        assert retry_resp.status_code == 201

    def test_register_with_empty_avatar_rejected(self, client, db_session):
        """头像为空文件：返回 400(40005)，且不创建用户。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "emptyavatar", "password": "Goodpass1"},
            files={"avatar": ("empty.png", b"", "image/png")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40005
        assert db_session.scalars(
            select(User).where(User.username == "emptyavatar")
        ).first() is None
