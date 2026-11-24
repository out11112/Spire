# Spire

独立的多人合作爬塔卡牌游戏服务端与终端 CLI 客户端（`https://github.com/out11112/Spire`）。

- **独立服务**：部署在独立子域名（默认 `https://spire.linkchat.online`），使用独立数据库 `spire.db`。
- **账号互通**：注册与登录完全复用 LinkChat 账号体系（默认认证地址 `https://linkchat.online`）；如果本机已登录 `linkchat` CLI，启动 `spire` 时会自动复用登录态。
- **开箱即用**：安装 CLI 后直接输入 `spire` 即可启动。

## 目录结构

- `server/`：独立 FastAPI 服务端（`spire-server` + `linkchat_spire` 游戏引擎）
- `cli/`：独立终端 TUI 客户端（提供 `spire` 命令）

## 快速开始

### 启动服务端

```bash
cd server
python -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
# 如与 LinkChat 同机部署，可将 LINKCHAT_AUTH_URL 改为 http://127.0.0.1:8000
.venv/bin/spire-server
```

### 安装并启动 CLI

需要 Node.js >= 22，直接通过发布包全局安装即可：

```sh
npm install -g https://spire.linkchat.online/releases/spire/0.1.0/spire-0.1.0.tgz --ignore-scripts
spire
```

或从源码本地构建安装：

```bash
cd cli
npm install
npm run build
npm link   # 注册全局 spire 命令

spire      # 直接启动（未登录时引导登录或注册 LinkChat 账号）
```

常用参数：

```bash
spire login                                  # 登录或注册 LinkChat 账号
spire logout                                 # 退出登录
spire --server http://127.0.0.1:8100         # 连接本地测试服
spire --auth http://127.0.0.1:8000           # 指定 LinkChat 认证地址
```

## 开源协议与声明

- 本项目源代码采用 [MIT License](LICENSE) 开源。
- 本项目为社区非商业项目，与 Mega Crit 无关；原版游戏设定与相关内容版权归原作者所有。
