/**
 * 通用表单校验工具：与后端注册接口的密码强度规则保持一致，
 * 用于前端提交前的前置拦截，减少无效请求；最终以后端校验为准。
 */

/** 用户名长度限制（对应后端 Pydantic 约束 2-50） */
export const USERNAME_MIN_LENGTH = 2
export const USERNAME_MAX_LENGTH = 50

/** 密码长度限制（对应后端 Pydantic 约束 6-128） */
export const PASSWORD_MIN_LENGTH = 6
export const PASSWORD_MAX_LENGTH = 128

/**
 * 注册密码强度校验。
 * 规则：必须同时包含字母和数字；禁止包含用户名。
 * 弱密码黑名单由后端统一维护，命中时直接展示后端返回的具体原因。
 *
 * @param password 明文密码
 * @param username 用户名（用于关联性校验）
 * @returns 校验通过返回空串，不通过返回中文错误原因
 */
export function validatePasswordStrength(password: string, username: string): string {
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return '密码必须同时包含字母和数字'
  }
  if (username && password.toLowerCase().includes(username.toLowerCase())) {
    return '密码不能包含用户名'
  }
  return ''
}
