# 登录支持邮箱登录 - 设计文档

**日期**: 2026-07-15
**状态**: 待实现

## 背景

现有登录仅支持用户名（username）+ 密码。用户注册时同时填写了 username 和 email，但容易忘记自己填写的 username，只记得邮箱。希望登录输入框既能填用户名，也能填邮箱，只要密码正确就放行。

## 目标

让登录页的"账号"输入框接受 **用户名** 或 **邮箱** 两种标识符，密码校验通过即登录成功。

## 非目标

- 不改造注册流程（依然必须填 username + email + password）。
- 不引入邮箱验证码 / 魔法链接 / 第三方登录。
- 不做邮箱大小写归一化（与现有注册逻辑保持一致）。
- 不新增数据库字段或迁移。

## 改动范围

### 1. 后端 - `routes/auth.py` 的 `login()`

当前实现只按 `username` 查询：

```python
user = User.query.filter_by(username=data['username']).first()
if user is None or not user.check_password(data['password']):
    return jsonify({'error': '用户名或密码错误'}), 401
```

改为按 `username` 查，查不到再按 `email` 查：

```python
identifier = (data.get('username') or '').strip()
user = User.query.filter_by(username=identifier).first()
if user is None:
    user = User.query.filter_by(email=identifier).first()
if user is None or not user.check_password(data['password']):
    return jsonify({'error': '账号或密码错误'}), 401
```

**设计要点**：
- API 字段名仍叫 `username`，但语义放宽为"账号或邮箱"。前端无需改字段名，向后兼容。
- `identifier` 仅做首尾空白裁剪，不做大小写归一化（与现有注册行为一致）。
- 错误信息从"用户名或密码错误"改为"账号或密码错误"，避免误导用户。
- 400 校验信息"请输入用户名和密码"改为"请输入账号和密码"。

### 2. 前端视图 - `static/js/app.views.auth.js` 的 `viewLogin()`

- 输入框 `<label>`：`用户名` → `用户名 / 邮箱`。

### 3. 前端 handler - `static/js/app.handlers.js` 的 `handlersLogin()`

- 失败 alert 文案：`'登录失败'`（兜底）→ `'账号或密码错误'`（与后端口径一致）。

## 边界情况

| 情况 | 处理 |
|---|---|
| 输入字符串同时匹配某用户的 username 和另一用户的 email（理论上可能） | 优先匹配 username（数据库中 username 与 email 分别 unique，但二者字符串空间有交叠可能；现状下概率极低，不做特殊处理） |
| 输入含前后空格（如 ` alice `） | 后端 `.strip()` 裁剪后再查 |
| 输入大小写不同的邮箱（如 `Alice@X.com` vs 注册时的 `alice@x.com`） | 不匹配（SQLite `filter_by(email=...)` 默认大小写敏感），与现有注册逻辑一致，不引入归一化 |
| 用户名密码字段缺失 | 400 返回"请输入账号和密码" |

## 测试要点

由于项目当前无测试套件，按手工验证：

1. 用 username 登录 → 成功。
2. 用 email 登录 → 成功。
3. 正确账号 + 错误密码 → "账号或密码错误"。
4. 不存在的 username/email + 任意密码 → "账号或密码错误"（不泄露账号是否存在）。
5. 空字段提交 → "请输入账号和密码"。
6. 前端输入框 label 显示为"用户名 / 邮箱"。
