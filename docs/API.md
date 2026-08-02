# API 契约

> 当前仅记录已经实现并对前端开放的稳定契约。认证 Cookie 名为 `access_token`，前端请求需使用
> `credentials: "include"`。JWT 不会出现在任何 JSON 响应中。

## 认证

### `POST /auth/login`

请求：

```json
{"email": "member@example.test", "password": "user-password"}
```

成功返回 `200`，并通过 `Set-Cookie` 下发 `HttpOnly; SameSite=Lax; Path=/` 的
`access_token`；生产环境额外带 `Secure`。

```json
{
  "user": {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "member@example.test",
    "display_name": "示例成员",
    "role": "member"
  }
}
```

用户不存在、密码错误或账号停用统一返回：

```http
HTTP/1.1 401 Unauthorized
```

```json
{"detail": "邮箱或密码错误"}
```

### `POST /auth/logout`

成功返回 `204 No Content`，并清除 `access_token` Cookie。

### `GET /auth/me`

成功返回 `200`：

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "email": "member@example.test",
  "display_name": "示例成员",
  "role": "member"
}
```

未携带 Cookie、Token 过期、签名无效、用户不存在或账号停用时统一返回 `401`。

## 用户管理

以下接口均要求当前用户角色为 `admin`；普通成员返回 `403`。

### `POST /admin/users`

请求：

```json
{
  "email": "new-member@example.test",
  "password": "user-password",
  "display_name": "新成员",
  "role": "member"
}
```

成功返回 `201`，响应结构与 `GET /auth/me` 相同。邮箱按大小写不敏感方式去重，重复邮箱返回：

```http
HTTP/1.1 409 Conflict
```

```json
{"detail": "邮箱已存在"}
```

### `GET /admin/users`

成功返回 `200`：

```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0000-000000000001",
      "email": "member@example.test",
      "display_name": "示例成员",
      "role": "member"
    }
  ]
}
```

所有用户响应都显式排除 `password_hash`。
