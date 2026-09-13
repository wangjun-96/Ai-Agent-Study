"""登录接口与 JWT 鉴权冒烟测试：pytest + httpx。

覆盖范围：
1. 登录成功：返回 Access/Refresh 双令牌，令牌载荷（sub/username/type/exp）正确；
2. 登录失败：密码错误、用户不存在统一 401(40103)，参数缺失 422；
3. 受保护接口 /auth/me：无令牌/伪造令牌/刷新令牌混用/用户已删除均返回 401(40104)，
   有效访问令牌返回 200；
4. 刷新接口 /auth/refresh：合法刷新令牌换新成功，类型不符/伪造/过期返回 401(40105)；
5. 静默续期闭环：访问令牌过期 → 401(40104) → 用刷新令牌换新 → 自动重试原请求成功，
   全程无需用户重新登录（模拟前端 axios 响应拦截器的处理逻辑）。

运行命令：pytest tests/test_auth_login.py -v
"""
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.jwt import create_token
from app.enums.token_type import TokenType

# 测试固定账号（密码满足注册强度规则：字母+数字、不含用户名、非黑名单）
_USERNAME = "loginuser"
_PASSWORD = "Goodpass1"


def _register(client, username: str = _USERNAME, password: str = _PASSWORD) -> str:
    """注册测试用户并返回用户ID。"""
    resp = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def _login(client, username: str = _USERNAME, password: str = _PASSWORD) -> dict:
    """登录并返回令牌对 data（access_token/refresh_token/token_type/expires_in）。"""
    resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _auth_header(token: str) -> dict:
    """构造 Bearer 认证请求头。"""
    return {"Authorization": f"Bearer {token}"}


def _decode(token: str) -> dict:
    """用配置中的密钥解码令牌，供用例校验载荷。"""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ---------------------------------------------------------------------------
# 一、登录接口
# ---------------------------------------------------------------------------


class TestLogin:
    """登录接口冒烟测试。"""

    def test_login_success_returns_token_pair(self, client):
        """登录成功：返回 200 与双令牌，expires_in 与配置一致。"""
        _register(client)
        data = _login(client)

        assert data["token_type"] == "bearer"
        # 访问令牌有效期（秒）与配置层一致
        assert data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert data["access_token"]
        assert data["refresh_token"]
        # 两类令牌必须不同
        assert data["access_token"] != data["refresh_token"]

    def test_access_token_claims(self, client):
        """访问令牌载荷：sub/username/type/exp 声明正确。"""
        user_id = _register(client)
        data = _login(client)

        payload = _decode(data["access_token"])
        assert payload["sub"] == str(user_id)
        assert payload["username"] == _USERNAME
        assert payload["type"] == TokenType.ACCESS.value
        assert "exp" in payload and "jti" in payload

    def test_refresh_token_claims(self, client):
        """刷新令牌载荷：类型为 refresh，有效期按天配置。"""
        _register(client)
        data = _login(client)

        payload = _decode(data["refresh_token"])
        assert payload["type"] == TokenType.REFRESH.value
        assert payload["username"] == _USERNAME

    def test_login_wrong_password(self, client):
        """密码错误：返回 401，业务码 40103，提示用户名或密码错误。"""
        _register(client)
        resp = client.post(
            "/auth/login",
            json={"username": _USERNAME, "password": "WrongPass9"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == 40103
        assert body["message"] == "用户名或密码错误"
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_login_unknown_username(self, client):
        """用户不存在：与密码错误返回完全一致的 401(40103)，避免用户名被枚举。"""
        resp = client.post(
            "/auth/login",
            json={"username": "ghost", "password": "AnyPass123"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == 40103
        assert body["message"] == "用户名或密码错误"

    def test_login_missing_fields(self, client):
        """参数校验：缺少密码字段返回 422。"""
        resp = client.post("/auth/login", json={"username": _USERNAME})
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200


# ---------------------------------------------------------------------------
# 二、JWT 保护接口 /auth/me
# ---------------------------------------------------------------------------


class TestProtectedMe:
    """受 JWT 保护的 /auth/me 接口冒烟测试。"""

    def test_me_without_token_unauthorized(self, client):
        """无令牌访问：返回 401，业务码 40104，并携带 WWW-Authenticate 头。"""
        resp = client.get("/auth/me")
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == 40104
        assert body["message"] == "访问令牌无效或已过期"
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_me_with_valid_access_token(self, client):
        """有效访问令牌：返回 200 与当前登录用户信息，响应不含密码。"""
        _register(client)
        tokens = _login(client)

        resp = client.get("/auth/me", headers=_auth_header(tokens["access_token"]))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == _USERNAME
        assert "id" in data
        assert "password" not in data

    def test_me_with_forged_token_rejected(self, client):
        """伪造令牌：返回 401(40104)。"""
        resp = client.get("/auth/me", headers=_auth_header("not-a-valid-jwt"))
        assert resp.status_code == 401
        assert resp.json()["code"] == 40104

    def test_me_with_non_bearer_scheme_rejected(self, client):
        """非 Bearer 认证方案（如 Basic）：返回 401(40104)，不暴露框架级 403。"""
        resp = client.get("/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 401
        assert resp.json()["code"] == 40104

    def test_me_with_refresh_token_rejected(self, client):
        """令牌类型隔离：拿刷新令牌访问业务接口返回 401(40104)。"""
        _register(client)
        tokens = _login(client)

        resp = client.get("/auth/me", headers=_auth_header(tokens["refresh_token"]))
        assert resp.status_code == 401
        assert resp.json()["code"] == 40104

    def test_me_after_user_deleted(self, client):
        """令牌合法但用户已删除：返回 401(40104)，不暴露 404 语义。"""
        user_id = _register(client)
        tokens = _login(client)
        # 用户管理接口已要求登录：携带本人访问令牌删除自己
        del_resp = client.delete(
            f"/api/v1/users/{user_id}",
            headers=_auth_header(tokens["access_token"]),
        )
        assert del_resp.status_code == 200

        resp = client.get("/auth/me", headers=_auth_header(tokens["access_token"]))
        assert resp.status_code == 401
        assert resp.json()["code"] == 40104


# ---------------------------------------------------------------------------
# 三、刷新接口 /auth/refresh
# ---------------------------------------------------------------------------


class TestRefreshToken:
    """刷新令牌接口冒烟测试。"""

    def test_refresh_success(self, client):
        """合法刷新令牌：返回 200 与新的访问令牌，新令牌可正常访问 /auth/me。"""
        _register(client)
        tokens = _login(client)

        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert resp.json()["message"] == "令牌刷新成功"
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        # 新访问令牌与登录时下发的不同
        assert data["access_token"] != tokens["access_token"]
        # 新令牌载荷正确且可直接访问受保护接口
        assert _decode(data["access_token"])["type"] == TokenType.ACCESS.value
        me_resp = client.get("/auth/me", headers=_auth_header(data["access_token"]))
        assert me_resp.status_code == 200

    def test_refresh_with_access_token_rejected(self, client):
        """令牌类型隔离：拿访问令牌调用刷新接口返回 401(40105)。"""
        _register(client)
        tokens = _login(client)

        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 40105
        assert resp.json()["message"] == "刷新令牌无效或已过期"

    def test_refresh_with_forged_token_rejected(self, client):
        """伪造刷新令牌：返回 401(40105)。"""
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": "not-a-valid-jwt"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 40105

    def test_refresh_with_expired_token_rejected(self, client):
        """过期刷新令牌：返回 401(40105)，前端需引导用户重新登录。"""
        user_id = _register(client)
        expired_refresh = create_token(
            user_id=user_id,
            username=_USERNAME,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(seconds=-1),  # 已过期 1 秒
        )

        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": expired_refresh},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 40105

    def test_refresh_missing_field(self, client):
        """参数校验：请求体缺少 refresh_token 返回 422。"""
        resp = client.post("/auth/refresh", json={})
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200


# ---------------------------------------------------------------------------
# 四、访问令牌过期 → 静默刷新 → 自动重试原请求（核心闭环）
# ---------------------------------------------------------------------------


class TestAutoRefreshAndRetry:
    """模拟前端响应拦截器：401(40104) 时静默换新并重试，用户无感知。"""

    def test_expired_access_token_auto_refresh_then_retry(self, client):
        """过期访问令牌：先 401(40104)，刷新换新后重试原请求成功。"""
        user_id = _register(client)
        tokens = _login(client)
        # 手工构造一个已过期的访问令牌（模拟存活到过期后的场景）
        expired_access = create_token(
            user_id=user_id,
            username=_USERNAME,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(seconds=-1),
        )

        # 第一步：携带过期访问令牌请求受保护接口 → 401(40104)
        first_resp = client.get("/auth/me", headers=_auth_header(expired_access))
        assert first_resp.status_code == 401
        assert first_resp.json()["code"] == 40104

        # 第二步：拦截器自动使用刷新令牌调用 /auth/refresh，换取新访问令牌（用户无操作）
        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.json()["data"]["access_token"]
        assert new_access != expired_access

        # 第三步：用新访问令牌自动重试原请求 → 200，业务数据正确
        retry_resp = client.get("/auth/me", headers=_auth_header(new_access))
        assert retry_resp.status_code == 200
        assert retry_resp.json()["data"]["username"] == _USERNAME

    def test_refresh_expired_breaks_silent_retry(self, client):
        """刷新令牌也过期时无法静默续期：401(40105)，应跳转登录页。"""
        user_id = _register(client)
        expired_access = create_token(
            user_id=user_id,
            username=_USERNAME,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(seconds=-1),
        )
        expired_refresh = create_token(
            user_id=user_id,
            username=_USERNAME,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(seconds=-1),
        )

        # 原请求 401(40104)
        assert client.get("/auth/me", headers=_auth_header(expired_access)).status_code == 401
        # 尝试静默刷新失败 401(40105)：闭环中断，前端引导重新登录
        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": expired_refresh},
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["code"] == 40105
