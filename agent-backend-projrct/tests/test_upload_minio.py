"""MinIO 上传链路冒烟测试：pytest + httpx。

不依赖真实 MinIO 服务：用 FakeMinio 覆写 get_minio_storage 依赖，
数据库仍走 conftest 的 SQLite 内存库，JWT 走真实「注册→登录」链路。

运行命令：pytest tests/test_upload_minio.py -v
"""
import base64
import hashlib
from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Resource, User

# 1x1 像素合法 PNG（内容固定，MD5 可推导）
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLv"
    "AAAAAElFTkSuQmCC"
)


class TestMinioUpload:
    """MinIO 通用上传接口冒烟测试。"""

    def test_upload_requires_auth(self, client):
        """未登录上传：统一返回 401(40104)。"""
        resp = client.post(
            "/api/v1/files/upload",
            files={"file": ("a.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 40104

    def test_upload_image_as_avatar_updates_user_avatar(
        self, client, login_user, fake_minio, db_session
    ):
        """图片 + 头像用途：上传 MinIO、落元数据、回写 users.avatar。"""
        headers, user_id = login_user("avatarup", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"storage_scene": 0, "upload_purpose": 1},
            files={"file": ("my.png", _PNG_BYTES, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # 资源分类与场景 / 用途回显
        assert data["resource_type"] == 1
        assert data["storage_scene"] == 0
        assert data["upload_purpose"] == 1
        assert data["is_avatar"] is True
        assert data["duplicated"] is False

        # MinIO 对象确实写入，路径符合 minio://{bucket}/{user_id}/{md5}.png
        file_hash = hashlib.md5(_PNG_BYTES).hexdigest()
        object_key = f"{user_id}/{file_hash}.png"
        assert object_key in fake_minio.objects
        assert data["storage_path"] == f"minio://ai-resource/{object_key}"
        # 返回可访问的预签名 URL
        assert data["url"].startswith("https://fake-minio/")

        # users.avatar 已回写为 storage_path
        user = db_session.scalars(
            select(User).where(User.username == "avatarup")
        ).first()
        assert user.avatar == data["storage_path"]

        # 长过期场景：过期时间约为 30 天后
        expire_time = datetime.fromisoformat(data["expire_time"])
        delta_days = (expire_time - datetime.now()).total_seconds() / 86400
        assert 29 <= delta_days <= 30

    def test_upload_image_general_purpose_keeps_avatar(
        self, client, login_user, fake_minio, db_session
    ):
        """图片 + 普通用途：仅存储，不更新 users.avatar。"""
        headers, _ = login_user("generalup", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"upload_purpose": 0},
            files={"file": ("pic.png", _PNG_BYTES, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_avatar"] is False

        user = db_session.scalars(
            select(User).where(User.username == "generalup")
        ).first()
        assert user.avatar is None

    def test_upload_document_never_updates_avatar(
        self, client, login_user, fake_minio, db_session
    ):
        """文档即使声明头像用途，也不回写 avatar（仅图片可做头像）。"""
        headers, user_id = login_user("docup", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"upload_purpose": 1},
            files={"file": ("note.txt", b"hello", "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["resource_type"] == 0
        assert data["is_avatar"] is False

        user = db_session.scalars(
            select(User).where(User.username == "docup")
        ).first()
        assert user.avatar is None

    def test_upload_audio(self, client, login_user, fake_minio):
        """音频上传：资源类型为 2，短过期场景过期时间约 2 小时。"""
        headers, user_id = login_user("audioup", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"storage_scene": 1},
            files={"file": ("voice.mp3", b"ID3fakeaudio", "audio/mpeg")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["resource_type"] == 2
        assert data["storage_scene"] == 1

        expire_time = datetime.fromisoformat(data["expire_time"])
        delta_hours = (expire_time - datetime.now()).total_seconds() / 3600
        assert 1.9 <= delta_hours <= 2.0

    def test_duplicate_upload_reuses_resource(
        self, client, login_user, fake_minio
    ):
        """同用户重复上传相同 MD5：复用元数据，duplicated=true，不重复写对象。"""
        headers, user_id = login_user("dupe", "Goodpass1")
        first = client.post(
            "/api/v1/files/upload",
            files={"file": ("a.png", _PNG_BYTES, "image/png")},
            headers=headers,
        )
        assert first.status_code == 200
        first_id = first.json()["data"]["resource_id"]
        assert len(fake_minio.objects) == 1

        second = client.post(
            "/api/v1/files/upload",
            files={"file": ("b.png", _PNG_BYTES, "image/png")},
            headers=headers,
        )
        assert second.status_code == 200
        data = second.json()["data"]
        assert data["duplicated"] is True
        assert data["resource_id"] == first_id
        # 对象未重复写入
        assert len(fake_minio.objects) == 1

    def test_extract_only_scene_returns_text_without_storage(
        self, client, login_user, fake_minio
    ):
        """storage_scene=2：只提取文本，不上传对象、不写元数据。"""
        headers, _ = login_user("extract", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"storage_scene": 2},
            files={"file": ("doc.txt", "你好世界".encode("utf-8"), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["extracted_text"] == "你好世界"
        assert data["storage_path"] == ""
        assert data["resource_id"] is None
        assert data["url"] is None
        assert len(fake_minio.objects) == 0

    def test_error_branches(self, client, login_user, fake_minio):
        """错误分支：空文件 40005 / 超大小 40004 / 类型不支持 40003。"""
        headers, _ = login_user("errors", "Goodpass1")

        empty = client.post(
            "/api/v1/files/upload",
            files={"file": ("empty.png", b"", "image/png")},
            headers=headers,
        )
        assert empty.status_code == 400
        assert empty.json()["code"] == 40005

        oversized = client.post(
            "/api/v1/files/upload",
            files={"file": ("big.png", b"x" * (settings.UPLOAD_MAX_SIZE + 1), "image/png")},
            headers=headers,
        )
        assert oversized.status_code == 400
        assert oversized.json()["code"] == 40004

        bad_type = client.post(
            "/api/v1/files/upload",
            files={"file": ("run.exe", b"MZbinary", "application/octet-stream")},
            headers=headers,
        )
        assert bad_type.status_code == 400
        assert bad_type.json()["code"] == 40003

    def test_invalid_scene_returns_422(self, client, login_user, fake_minio):
        """storage_scene 取值非法：参数校验失败 422。"""
        headers, _ = login_user("badscene", "Goodpass1")
        resp = client.post(
            "/api/v1/files/upload",
            data={"storage_scene": 9},
            files={"file": ("a.png", _PNG_BYTES, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 422


class TestRegisterAvatarMinio:
    """注册接口头像走 MinIO 的专项冒烟测试。"""

    def test_register_avatar_resource_not_expiring(
        self, client, fake_minio, db_session
    ):
        """注册头像：资源记录 purpose=1/scene=0/expire_time=null（不被定时清理）。"""
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "regavatar", "password": "Goodpass1"},
            files={"avatar": ("face.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 201, resp.text
        user_id = resp.json()["data"]["id"]

        # 资源元数据：头像用途、长存储层级、但不过期
        resource = db_session.scalars(
            select(Resource).where(Resource.user_id == user_id)
        ).first()
        assert resource is not None
        assert resource.update_purpose == 1
        assert resource.storage_scene == 0
        assert resource.resource_type == 1
        assert resource.expire_time is None

    def test_register_bad_avatar_does_not_call_storage(
        self, client, fake_minio, db_session
    ):
        """头像非法（类型/空文件）：prepare 阶段拒绝，不访问 MinIO、不建号。"""
        # 非图片
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": "badreg", "password": "Goodpass1"},
            files={"avatar": ("note.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40003
        # 空文件
        empty_resp = client.post(
            "/api/v1/auth/register",
            data={"username": "emptyreg", "password": "Goodpass1"},
            files={"avatar": ("x.png", b"", "image/png")},
        )
        assert empty_resp.status_code == 400
        assert empty_resp.json()["code"] == 40005

        # 均未触达 MinIO，且无用户创建
        assert len(fake_minio.objects) == 0
        assert db_session.scalars(
            select(User).where(User.username.in_(["badreg", "emptyreg"]))
        ).first() is None
