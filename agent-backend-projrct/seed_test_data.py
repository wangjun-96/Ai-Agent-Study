"""测试数据填充脚本：直接向 MySQL 插入完整测试链路数据，不做删除。

生成数据链路：
1 个用户 → 3 个会话（学习/面试/笔记）→ 每个会话若干消息（含 segments）→ 1 条面试记录 + 资源

运行方式：在项目根目录执行
    .venv\Scripts\python.exe seed_test_data.py
"""
import hashlib
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    ChatMessage,
    Interview,
    Resource,
    Session as SessionModel,
    User,
)
from app.enums.resource_type import ResourceType
from app.enums.select_model import SelectModel
from app.enums.session_model import SessionModel as SessionModelEnum
from app.enums.interview_status import InterviewStatus
from app.enums.storage_scene import StorageScene
from app.enums.upload_purpose import UploadPurpose
from app.security import hash_password

# ===========================================================================
# 测试账号（用户名密码告知前端，逐条测试用）
# ===========================================================================
TEST_USERNAME = "testuser"
TEST_PASSWORD = "Test1234"


def main() -> None:
    db: Session = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # 1. 用户：已有则复用，无则新建
        # ------------------------------------------------------------------
        existing = db.query(User).filter(User.username == TEST_USERNAME).first()
        if existing:
            user = existing
            print(f"[复用] 用户 id={user.id} username={user.username}")
        else:
            user = User(
                username=TEST_USERNAME,
                password=hash_password(TEST_PASSWORD),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[新建] 用户 id={user.id} username={user.username}")

        # ------------------------------------------------------------------
        # 2. 资源（2个图片 + 1个文件，供消息 segments 引用）
        # ------------------------------------------------------------------
        resources: list[Resource] = []
        res_defs = [
            ("风景图.jpg", ResourceType.IMAGE, "img001", "minio://ai-resource/user_1/images/img001.jpg"),
            ("截图.png",   ResourceType.IMAGE, "img002", "minio://ai-resource/user_1/images/img002.png"),
            ("简历.pdf",   ResourceType.FILE,  "doc001", "minio://ai-resource/user_1/files/doc001.pdf"),
        ]
        for name, rtype, fhash, path in res_defs:
            r = db.query(Resource).filter(
                Resource.file_hash == fhash,
                Resource.user_id == user.id,
            ).first()
            if r:
                resources.append(r)
                print(f"[复用] 资源 id={r.id} name={r.file_name}")
            else:
                r = Resource(
                    resource_type=rtype.value,
                    storage_scene=StorageScene.LONG.value,
                    update_purpose=UploadPurpose.GENERAL.value,
                    file_name=name,
                    file_hash=fhash,
                    storage_path=path,
                    user_id=user.id,
                    expire_time=None,
                )
                db.add(r)
                db.commit()
                db.refresh(r)
                resources.append(r)
                print(f"[新建] 资源 id={r.id} name={r.file_name}")

        res_img1, res_img2, res_file = resources

        # ------------------------------------------------------------------
        # 3. 会话（学习 / 面试 / 笔记）
        # ------------------------------------------------------------------
        sessions: dict[str, SessionModel] = {}
        session_defs = [
            ("Python 学习计划", SessionModelEnum.STUDY),
            ("Java 后端模拟面试", SessionModelEnum.INTERVIEW),
            ("项目笔记整理", SessionModelEnum.NOTE),
        ]
        for title, model in session_defs:
            s = db.query(SessionModel).filter(
                SessionModel.user_id == user.id,
                SessionModel.title == title,
            ).first()
            if s:
                sessions[title] = s
                print(f"[复用] 会话 id={s.id} title={s.title} model={s.session_model}")
            else:
                s = SessionModel(
                    user_id=user.id,
                    title=title,
                    session_model=model.value,
                )
                db.add(s)
                db.commit()
                db.refresh(s)
                sessions[title] = s
                print(f"[新建] 会话 id={s.id} title={s.title} model={s.session_model}")

        s_study = sessions["Python 学习计划"]
        s_interview = sessions["Java 后端模拟面试"]
        s_note = sessions["项目笔记整理"]

        # ------------------------------------------------------------------
        # 4. 消息（每个会话若干条，含 segments）
        # ------------------------------------------------------------------
        messages: list[ChatMessage] = []

        # 消息定义：(session, select_model, request_text, response_text, request_segs, response_segs)
        msg_defs = [
            # 学习会话：用户带图片附件提问，AI 文本回复
            (
                s_study, SelectModel.KNOWLEDGE,
                "请讲解 Python 装饰器的原理",
                "装饰器本质上是一个函数，接收函数作为参数并返回新函数……",
                [{"type": "image", "resource_id": res_img1.id, "url": "https://example.com/img001.jpg", "name": "风景图.jpg"}],
                [],
            ),
            (
                s_study, SelectModel.PRACTICE,
                "做一道链表反转的题目",
                "好的，这是一道经典的链表反转题……",
                [],
                [],
            ),
            # 面试会话：用户提问，AI 回复带图片
            (
                s_interview, SelectModel.MOCK_INTERVIEW,
                "开始 Java 后端模拟面试",
                "好的，让我们开始。第一个问题：请解释 JVM 的内存模型……",
                [],
                [{"type": "image", "resource_id": res_img2.id, "url": "https://example.com/img002.png", "name": "截图.png"}],
            ),
            (
                s_interview, SelectModel.INTERVIEW_REVIEW,
                "面试复盘",
                "本次面试表现良好，以下是需要改进的知识点……",
                [{"type": "file", "resource_id": res_file.id, "url": "https://example.com/doc001.pdf", "name": "简历.pdf"}],
                [],
            ),
            # 笔记会话：纯文本
            (
                s_note, SelectModel.DEFAULT,
                "记录今天的学习内容",
                "已为你创建笔记，请继续输入内容……",
                [],
                [],
            ),
        ]

        for session, sel_model, req_text, resp_text, req_segs, resp_segs in msg_defs:
            # 用 request_id 去重
            req_id = hashlib.md5(f"{session.id}_{req_text}".encode()).hexdigest()
            existing_msg = db.query(ChatMessage).filter(
                ChatMessage.request_id == req_id
            ).first()
            if existing_msg:
                messages.append(existing_msg)
                print(f"[复用] 消息 id={existing_msg.id} session={session.title}")
            else:
                msg = ChatMessage(
                    user_id=user.id,
                    session_id=session.id,
                    select_model=sel_model.value,
                    request_id=req_id,
                    request_text=req_text,
                    response_text=resp_text,
                    file_extracted_text=None,
                    request_segments=req_segs or None,
                    response_segments=resp_segs or None,
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)
                messages.append(msg)
                print(f"[新建] 消息 id={msg.id} session={session.title}")

        # ------------------------------------------------------------------
        # 5. 面试记录（关联面试会话的第一条面试消息）
        # ------------------------------------------------------------------
        interview_msg = messages[2]  # "开始 Java 后端模拟面试"
        existing_iv = db.query(Interview).filter(
            Interview.message_id == interview_msg.id
        ).first()
        if existing_iv:
            interview = existing_iv
            print(f"[复用] 面试记录 id={interview.id} message_id={interview_msg.id}")
        else:
            interview = Interview(
                session_id=s_interview.id,
                message_id=interview_msg.id,
                user_id=user.id,
                qa_object={
                    "id": "qa-001",
                    "question": "请解释 JVM 的内存模型",
                    "answer": "JVM 内存模型包括堆、栈、方法区、程序计数器等……",
                    "created_at": 1694502400,
                },
                interview_duration=1800,
                status=InterviewStatus.IN_PROGRESS.value,
            )
            db.add(interview)
            db.commit()
            db.refresh(interview)
            print(f"[新建] 面试记录 id={interview.id} message_id={interview_msg.id}")

        # 回写消息的 interview_id
        if interview_msg.interview_id is None:
            interview_msg.interview_id = interview.id
            db.commit()
            print(f"[回写] 消息 id={interview_msg.id} interview_id={interview.id}")

        # ------------------------------------------------------------------
        # 汇总
        # ------------------------------------------------------------------
        print("\n" + "=" * 60)
        print("测试数据填充完成！")
        print("=" * 60)
        print(f"用户名: {TEST_USERNAME}")
        print(f"密  码: {TEST_PASSWORD}")
        print(f"用户ID: {user.id}")
        print("-" * 60)
        print("会话列表:")
        for title, s in sessions.items():
            print(f"  id={s.id} model={s.session_model} title={s.title}")
        print("-" * 60)
        print("消息列表:")
        for msg in messages:
            seg_info = ""
            if msg.request_segments:
                seg_info += f" req_segs={len(msg.request_segments)}"
            if msg.response_segments:
                seg_info += f" resp_segs={len(msg.response_segments)}"
            if msg.interview_id:
                seg_info += f" interview_id={msg.interview_id}"
            print(f"  id={msg.id} session_id={msg.session_id} select_model={msg.select_model}{seg_info}")
        print("-" * 60)
        print(f"面试记录: id={interview.id} status={interview.status}")
        print("-" * 60)
        print("资源列表:")
        for r in resources:
            print(f"  id={r.id} type={r.resource_type} name={r.file_name} path={r.storage_path}")
        print("=" * 60)
        print("\n可测试的接口:")
        print(f"  登录:        POST /api/v1/auth/login            {{\"username\":\"{TEST_USERNAME}\",\"password\":\"{TEST_PASSWORD}\"}}")
        print(f"  会话列表:    GET  /api/v1/sessions/?page=1&page_size=10")
        print(f"  按模式过滤:  GET  /api/v1/sessions/?session_model=1")
        print(f"  编辑会话:    PUT  /api/v1/sessions/{s_study.id}  {{\"title\":\"新标题\"}}")
        print(f"  消息列表:    GET  /api/v1/sessions/{s_study.id}/messages?page=1&page_size=10")
        print(f"  面试详情:    GET  /api/v1/interviews/{interview.id}")
        print(f"  用户列表:    GET  /api/v1/users/")
        print(f"  头像代理:    GET  /api/v1/avatar/{user.id}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
