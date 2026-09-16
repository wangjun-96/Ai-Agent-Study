"""头像公开代理接口冒烟测试：pytest + httpx。

覆盖场景：
1. 有头像用户 → 307 重定向到预签名 URL；
2. 无头像用户 → 404(40402)；
3. 用户不存在 → 404(40401)；
4. 无需 JWT 鉴权即可访问（<img> 标签场景）。

运行命令：pytest tests/test_avatar_proxy.py -v
"""
import base64
import hashlib

import pytest

# 1x1 像素合法 PNG
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLv"
    "AAAAAElFTkSuQmCC"
)


class TestAvatarProxy:
    """头像公开代理接口测试。"""

    def test_avatar_redirects_to_presigned_url(self, client, fake_minio):
        """有头像用户：307 重定向，Location 指向预签名 URL。"""
        # 注册带头像用户（走 MinIO 存储链路）
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "avatarproxy", "password": "Goodpass1"},
            files={"avatar": ("face.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 201
        user_id = resp.json()["data"]["id"]

        # 访问头像代理接口（不携带 JWT）
        avatar_resp = client.get(
            f"/api/v1/avatar/{user_id}", follow_redirects=False
        )
        assert avatar_resp.status_code == 307

        # Location 指向 FakeMinio 预签名 URL
        location = avatar_resp.headers["location"]
        assert location.startswith("https://fake-minio/")

        # URL 中的 object_key 与注册时写入的一致
        file_hash = hashlib.md5(_PNG_BYTES).hexdigest()
        object_key = f"{user_id}/{file_hash}.png"
        assert object_key in location

    def test_user_without_avatar_returns_40402(self, client, fake_minio):
        """无头像用户：404(40402)。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "noavatar", "password": "Goodpass1"},
        )
        assert resp.status_code == 201
        user_id = resp.json()["data"]["id"]

        avatar_resp = client.get(f"/api/v1/avatar/{user_id}")
        assert avatar_resp.status_code == 404
        assert avatar_resp.json()["code"] == 40402

    def test_nonexistent_user_returns_40401(self, client, fake_minio):
        """用户不存在：404(40401)。"""
        resp = client.get("/api/v1/avatar/999999")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401

    def test_avatar_no_auth_required(self, client, fake_minio):
        """头像代理接口无需 JWT：不携带 Authorization 头也能访问。"""
        # 注册带头像用户
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "publicavatar", "password": "Goodpass1"},
            files={"avatar": ("a.png", _PNG_BYTES, "image/png")},
        )
        user_id = resp.json()["data"]["id"]

        # 不携带 Authorization 头直接访问
        avatar_resp = client.get(
            f"/api/v1/avatar/{user_id}", follow_redirects=False
        )
        # 不应返回 401（说明无需鉴权）
        assert avatar_resp.status_code == 307
