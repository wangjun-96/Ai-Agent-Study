"""JWT 令牌类型枚举：区分访问令牌与刷新令牌，禁止混用。

- access ：访问令牌（Access Token），短期有效，用于访问受保护接口；
- refresh：刷新令牌（Refresh Token），长期有效，仅用于在访问令牌过期后换取新令牌。
"""
from enum import Enum


class TokenType(str, Enum):
    """JWT 令牌类型，写入载荷 type 声明，校验时严格比对，防止令牌混用。"""

    ACCESS = "access"
    REFRESH = "refresh"
