"""语义意图判断：本地向量模型（fastembed）计算文本与意图示例的相似度。

- 全局单例 + 懒加载，首次使用或启动预热时加载模型；
- 模型下载/推理失败时返回 None，调用方自动降级关键词匹配；
- 供长期记忆 should_write 与流程总控 classify_intent 复用。
"""
import math
import threading

from app.core import get_logger, settings

logger = get_logger("semantic_intent")


class SemanticIntentClassifier:
    """本地语义分类器：单例 + 懒加载 + 失败降级。"""

    _instance: "SemanticIntentClassifier | None" = None

    def __init__(self) -> None:
        self._model = None
        self._load_failed = False
        self._lock = threading.Lock()

    @classmethod
    def get(cls) -> "SemanticIntentClassifier":
        """获取全局单例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> object | None:
        """线程安全懒加载 fastembed 文本向量模型，失败只记一次告警。"""
        if self._model is not None:
            return self._model
        if self._load_failed:
            return None
        with self._lock:
            if self._model is not None:
                return self._model
            if self._load_failed:
                return None
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(
                    model_name=settings.LONG_TERM_EMBEDDING_MODEL
                )
                logger.info(
                    "语义向量模型加载成功 model={}", settings.LONG_TERM_EMBEDDING_MODEL
                )
                return self._model
            except Exception as exc:  # noqa: BLE001 模型下载/加载失败统一降级
                self._load_failed = True
                logger.warning(
                    "语义向量模型加载失败，降级为关键词匹配 model={} error={}",
                    settings.LONG_TERM_EMBEDDING_MODEL,
                    exc,
                )
                return None

    def warmup(self) -> bool:
        """预热模型（应用启动后台线程调用），成功返回 True。"""
        return self._load_model() is not None

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        """余弦相似度（纯 Python，避免额外依赖）。"""
        dot = sum(a * b for a, b in zip(left, right))
        norm_left = math.sqrt(sum(a * a for a in left))
        norm_right = math.sqrt(sum(b * b for b in right))
        if norm_left == 0 or norm_right == 0:
            return 0.0
        return dot / (norm_left * norm_right)

    def similarity(self, text: str, examples: list[str]) -> float | None:
        """计算文本与意图示例的最大余弦相似度。

        :return: 相似度分值；模型不可用或入参为空时返回 None（调用方降级）
        """
        text = (text or "").strip()
        if not text or not examples:
            return None
        model = self._load_model()
        if model is None:
            return None
        try:
            vectors = list(model.embed([text, *examples]))
        except Exception as exc:  # noqa: BLE001 推理失败降级
            logger.warning("语义向量推理失败，降级为关键词匹配 error={}", exc)
            return None
        if len(vectors) < 2:
            return None
        base = [float(value) for value in vectors[0]]
        return max(
            self._cosine(base, [float(value) for value in vector])
            for vector in vectors[1:]
        )
