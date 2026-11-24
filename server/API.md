# LinkChat Spire 接口文档

本文介绍程序或客户端接入 LinkChat Spire 的方法：通过 HTTP 创建和加入房间，通过 WebSocket 接收游戏快照并提交动作。示例使用生产地址 `https://linkchat.online`，自建部署请替换主机名。

> **认证变更说明**：自 **0.41.0** 起，外部 API Key（`lc_api_*`）接入通道已移除（继续使用 API Key 会返回 `401`）。Spire 的全部 HTTP 与 WebSocket 接口统一使用 **用户登录会话** 认证（网页端和 CLI 使用同一认证方式）。

当前版本标识：

| 字段 | 当前值 | 含义 |
| --- | --- | --- |
| `protocol` | `8` | 客户端与服务端交换的数据结构版本 |
| `rules` | `spire-tui-4` | 规则和存档兼容版本 |
| `content` | `0.1.0-alpha.2.dev17` | 卡牌、遗物、事件等内容版本 |
| WebSocket 子协议 | `linkchat-game-v8` | 实时连接协议 |

用户、房间、托管记录等 ID 均为 UUIDv7 字符串。创建房间和开放托管时，请求中的 `requestId` 将直接用作资源 ID，因此须使用 UUIDv7，重试时沿用原值；Python 可安装 `uuid6` 包（`pip install uuid6`）生成 UUIDv7。动作、消息等其他请求 ID 只要求是 UUID。敌人、卡牌实例和回合数等游戏内标识保持原有格式。

## 认证

Spire 接口（`/api/games/spire/*` 与 `/ws/games/spire/*`）仅接受已登录用户的 **会话认证**，可通过 `POST /api/users/login` 获取：

- **Cookie 会话**：登录响应设置 `HttpOnly` Cookie `linkchat_session`。
- **Bearer 会话令牌**：从 `linkchat_session` Cookie 提取会话令牌并在请求头中传递：

```http
Authorization: Bearer <session-token>
```

WebSocket 握手同时携带会话凭据（Cookie 或 `Authorization: Bearer` 请求头）和子协议：

```http
Authorization: Bearer <session-token>
Sec-WebSocket-Protocol: linkchat-game-v8
```

不得将会话令牌写入 URL、查询参数、日志或公开代码。浏览器原生 `WebSocket` 不能设置 `Authorization` 请求头，可直接使用同域或登录后的浏览器 Cookie 建立连接。

权限说明：

- 始终以当前登录账号的身份行动，不能以其他玩家的身份操作；仍须遵守房间成员、房主和托管相关规则。
- 账号退出登录、会话过期或账号被封禁后，现有游戏连接和请求会立即失效。

关于受管 Agent 运行时接入协议，请参阅 [Agent 接入指南](https://docs.linkchat.online/agent.html)。

## 接入步骤

1. 通过 `GET /api/games/spire/rooms` 查询可继续或可加入的房间，或创建新房间。
2. 合作模式下，其他账号调用 `POST /rooms/{roomId}/join` 加入；创建者自动成为房间成员。
3. 连接房间 WebSocket，接收首个完整快照并保存其中的 `leaseId`。需要房间聊天时，在连接 URL 添加 `?roomChat=1`，并检查快照中的 `features.roomChat`。
4. 只从最新快照的 `options[].action` 选择动作；需要选牌时按 `choice` 的要求补充 `choice` 或 `cards`。
5. 为每次逻辑动作生成新的 `actionId`，与当前 `leaseId` 一起提交。
6. 持续接收 WebSocket 完整快照；订阅聊天后须先将 `ROOM_CHAT` 事件分流，不得使用该事件覆盖游戏状态。以小于 45 秒的间隔发送文本 `PING`，建议每 30 秒发送一次。

可执行的动作以快照的 `options[].action` 为准，内容更新后选项也会变化，客户端不应自行推导选项。战斗中的出牌、药水和结束回合由客户端按[动作参考](#action-reference)构造。

## 接口总览

| 方法 | 路径 | 用途 | 写操作 |
| --- | --- | --- | --- |
| `GET` | `/api/games/spire/catalog` | 资料库分类、角色与进阶元数据 | 否 |
| `GET` | `/api/games/spire/catalog/{category}` | 按小类搜索并分页列出条目 | 否 |
| `GET` | `/api/games/spire/catalog/{category}/{id}` | 条目详情、升级或进阶预览 | 否 |
| `GET` | `/api/games/spire/rooms` | 列出全站可见的未结束房间 | 否 |
| `POST` | `/api/games/spire/rooms` | 创建房间 | 是 |
| `POST` | `/api/games/spire/rooms/{roomId}/join` | 加入或恢复加入合作房间 | 是 |
| `POST` | `/api/games/spire/rooms/{roomId}/abandon` | 房主按 revision 放弃存档，无需租约 | 是 |
| `GET` | `/api/games/spire/rooms/{roomId}` | 获取当前玩家可见的完整快照 | 否 |
| `GET` | `/api/games/spire/rooms/{roomId}/logs` | 分页读取当前战斗的结构化日志 | 否 |
| `GET` | `/api/games/spire/rooms/{roomId}/players/{playerId}/inspection` | 分页查看房间玩家的公开装备 | 否 |
| `POST` | `/api/games/spire/rooms/{roomId}/actions` | 提交游戏动作 | 是 |
| `POST` | `/api/games/spire/rooms/{roomId}/actions/batch` | 顺序提交最多 8 个动作 | 是 |
| `POST` | `/api/games/spire/rooms/{roomId}/chat` | 发送房间临时消息 | 是 |
| `WS` | `/ws/games/spire/rooms/{roomId}` | 接收快照并取得动作租约 | 是 |

所有请求和响应使用 UTF-8 JSON。路径中的 `roomId`、请求中的 `requestId`、`actionId`、`messageId` 和 `leaseId` 均为 UUID 字符串；批量请求的 `batchId` 也使用 UUID。

## 房间

### 列出房间

```http
GET /api/games/spire/rooms
```

所有账号共用一个房间大厅，房间不属于任何频道。接口返回当前账号可见的未结束房间，按更新时间倒序，最多 50 个：

- 尚未开始（`phase` 为 `lobby`）且房主在线的合作房间，所有账号可见；
- 已开始的合作房间只有成员可见，房主始终可见其拥有的房间；
- 单人房间只有房主可见。

每个房间包含 `ownerId`、`ownerName`、`act`（从 1 开始）、`hostOnline`、`revision`、`hasPassword` 等字段，玩家包含 `character`。`features` 列出服务端支持的能力，例如 `roomPasswords`。

```json
{
  "protocol": 8,
  "phases": ["lobby", "map", "combat", "reward", "rest", "shop", "event", "treasure", "actComplete", "ending", "victory", "defeat", "abandoned"],
  "rooms": [
    {
      "id": "019a0e24-6b79-72e0-93bd-a59c442aa315",
      "ownerId": "00000000-0000-7000-8000-00000000000c",
      "ownerName": "Alice",
      "mode": "coop",
      "phase": "combat",
      "paused": false,
      "floor": 7,
      "ascension": 10,
      "act": 1,
      "hostOnline": true,
      "hasPassword": false,
      "players": [{"id": "00000000-0000-7000-8000-00000000000c", "name": "Alice", "character": "ironclad"}],
      "compatible": true
    }
  ]
}
```

`compatible=false` 表示房间存档的规则或内容版本与当前服务端不一致，可以显示，但不能进入或操作。

### 创建房间

```http
POST /api/games/spire/rooms
Content-Type: application/json

{
  "requestId": "019a0e24-6b79-72e0-93bd-a59c442aa315",
  "seed": "EXTERNAL-DEMO-001",
  "mode": "coop",
  "ascension": 0
}
```

字段说明：

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `requestId` | 是 | 本次创建的幂等 UUID，同时成为 `roomId` |
| `seed` | 否 | 最多 64 个字符；空字符串表示服务端生成种子 |
| `mode` | 否 | `solo` 或 `coop`，默认 `coop` |
| `password` | 否 | 多人房间可选密码，固定 6 位数字（`0-9`，如 `"042817"`，须为字符串）；省略或 `null` 为无密码，单人模式不支持 |
| `ascension` | 否 | 严格整数 `0..10`，默认 `0` |
| `character` | 否 | `ironclad/silent/defect/regent/necrobinder`，默认 `ironclad` |
| `replaceRoomId`、`replaceRevision` | 否 | 单人替换旧存档时必须同时提供旧房间 UUID 和当前版本；不匹配返回 409 |

成功响应：

```json
{"id":"019a0e24-6b79-72e0-93bd-a59c442aa315"}
```

网络请求失败后，应使用完全相同的请求体和 `requestId` 重试；相同 ID 用于不同参数时返回 `409`。每个账号只有一个单人存档：已有未结束的单人房间时，创建请求直接返回该房间；如需重新开始，应提供替换参数。旧存档结束与新存档创建在同一事务中完成，失败时旧存档不受影响。每个账号最多同时拥有 3 个未结束的合作房间。

房间列表的 `hasPassword` 表示是否设置了密码。服务端只保存密码的加盐哈希，列表和快照中都不会出现密码；重试创建请求时须提供原密码。

### 加入房间

```http
POST /api/games/spire/rooms/019a0e24-6b79-72e0-93bd-a59c442aa315/join
```

请求体可以为空，也可以指定角色，例如 `{"character":"silent"}`。加入设有密码的房间时，新成员须提供密码，例如 `{"password":"042817"}`；密码缺失或错误返回 `403 invalid_room_password`，不会占用席位。已有成员重新进入房间时无需提供密码，角色沿用存档中的配置。

- 其他账号仅可在房主在线时加入或连接房间，否则返回 `409 host_offline`，WebSocket 以 1008 关闭。
- 只有 `lobby` 阶段能加入新玩家，合作房间最多 4 人；已开始的房间只有原成员能继续。
- 单人房间不能被其他账号发现或加入。

成功响应：

```json
{"id":"019a0e24-6b79-72e0-93bd-a59c442aa315"}
```

### 获取房间快照

```http
GET /api/games/spire/rooms/{roomId}
```

调用者必须已经在房间中。响应与 WebSocket 的完整快照结构相同，但不含 `leaseId`；该接口适用于恢复界面显示和只读接入，不能单独用于提交动作。

### 多人开始条件

合作房间至少需要两名不同玩家在线才能准备、开始或恢复游戏；同一账号的多个连接仅计为一名玩家。人数不足的 `ready` 请求返回 `409 insufficient_players`，不更新存档。快照中的 `partyRequirement={minimum,online,canReady}` 显示当前人数要求；人数不足时不提供准备/继续选项。创建等待房间和选择角色不受此限制，单人模式仍允许一人开始及恢复。

### 放弃当前存档

`POST /api/games/spire/rooms/{id}/abandon`，请求体 `{"revision":8}`。仅房主且具有游戏控制权限可调用，无需建立游戏连接。revision 必须匹配当前存档，否则返回 `409 stale_revision`，应刷新并重新确认。成功返回 `{"id":"房间 ID"}`，已放弃的存档可安全重试。非房主返回 `403 host_only`。放弃会立即结束整局，不需要其他成员同意。

在线的房主也可以通过带租约的 `actions` 提交 `{"type":"abandon"}`。已结束的存档不能再放弃。

## WebSocket 与租约

连接地址：

```text
wss://linkchat.online/ws/games/spire/rooms/{roomId}
```

连接成功后服务端发送当前玩家的完整快照，其中 `leaseId` 是该账号在该房间的当前控制租约。一个账号在一个房间只能有一个控制连接；新连接会替换旧连接，旧连接以关闭码 `4001` 结束。客户端必须停止使用旧连接取得的 `leaseId`。

服务端在房间状态改变时发送新的完整快照，而不是 JSON Patch。客户端应按 `revision` 覆盖本地状态；不得将客户端推算的结果作为最终状态。

可选地追加 `?roomChat=1` 订阅 `ROOM_CHAT` 房间消息事件，详见[房间即时聊天](#room-chat)。消息通过 HTTP 发送，不能向 WebSocket 直接发送聊天文本或聊天 JSON；WebSocket 上行只接受文本 `PING` 和动作 JSON，见[低延迟动作通道](#action-channel)。

心跳使用文本帧：

```text
客户端 -> PING
服务端 -> PONG
```

两次 `PING` 的间隔不能超过 45 秒，建议 30 秒一次。消息超限、认证失效、协议错误或 45 秒没有心跳时，服务端会关闭连接。有控制连接断开时游戏暂停，原成员全部重新连接后自动恢复。

常见关闭码：

| 关闭码 | 含义 |
| --- | --- |
| `1008` | 认证、房间成员身份、Origin、子协议或消息格式不符合要求 |
| `4001` | 同账号的新控制连接已替换当前连接 |

带 `Origin` 请求头的连接必须与服务器同源；不带 `Origin` 的程序（如 Python、Node.js 客户端）可以直接连接。

## 快照

快照是按当前玩家裁剪的投影，主要字段如下：

| 字段 | 说明 |
| --- | --- |
| `protocol`、`rules`、`content` | 协议、规则和内容兼容版本 |
| `roomId`、`mode` | 房间标识和 `solo`/`coop` 模式；协议 8 删除了 `channelId` |
| `revision` | 状态版本；每次成功改变状态后递增 |
| `phaseId` | 当前阶段实例 ID，用于拒绝来自旧界面的动作 |
| `phase` | 当前阶段，取值见房间列表的 `phases` |
| `paused`、`floor`、`turn`、`seed` | 暂停状态、楼层、回合和规范化种子 |
| `ascension` | 本局升阶等级，范围 A0–A10 |
| `online` | 当前有控制连接的玩家 ID 数组 |
| `leaseId` | 仅 WebSocket 快照存在；提交动作和发送房间消息所需的当前租约 |
| `upgradePreviews` | 按来源和卡牌 ID 索引的当前实例升级预览，见“卡牌升级预览” |
| `partyRequirement` | `minimum`、`online`、`canReady`；新局准备人数要求，存档在原成员控制连接到齐后自动恢复 |
| `features.roomChat` | 为 `true` 表示支持房间即时聊天 |
| `endTurn` | `canEndTurn`、`canUndoEndTurn` 和不可操作原因 |
| `players` | 所有玩家的公开状态，不含其手牌和抽牌顺序 |
| `enemies` | 敌人、意图和公开状态 |
| `self` | 当前玩家的手牌、牌组、弃牌、消耗牌、遗物、药水等奖励信息 |
| `options` | 当前可执行选项；每项含 `id`、`label`、`action` 和可选的 `choice` |
| `act`、`mapView` | 旅程初始化后各阶段可用的幕信息与公开地图；`act.index` 从 0 开始，`act.row` 为幕内层数，顶层 `floor` 为累计楼层 |
| `pendingChoice` | 待完成的卡牌选择及最少、最多数量 |
| `pendingDecision` | 待完成的结构化决定及最少、最多数量 |
| `event`、`eventProgress` | 当前事件及其公开进度 |
| `log`、`battleLog` | 最近 20 条当前玩家可见的结构化战斗日志及分页元数据 |

**多人独立选择**：多人游戏中，出牌、药水、回合开始、事件、商店、营地和奖励触发的个人选择都由各玩家分别完成。存在待选项的玩家须先完成个人选择，其他玩家不受影响，可以继续出牌、使用药水或结束回合。`pendingChoice` / `pendingDecision` 仅包含接收者的个人选择，客户端应以当前玩家的 `options` 和 `endTurn` 为准；存在未完成选择的玩家时，敌方回合不会开始。候选牌可能因队友的动作而变化，客户端应清除已不属于最新选项的本地选择，过期的选择会被拒绝。战斗结束或选择者倒地时，相应的等待自动取消。共享事件先投票，再分别结算个人效果；所有玩家完成后才进入下一阶段。

快照中 `features.independentChoices=true` 表示支持独立选择，可选字段 `choiceStatus:[{id:玩家ID,status:"choosing"|"ready"|"done"}]` 显示每位玩家的进度，但不包含队友的候选牌或选择内容。卡牌可以带 `starCost`（非负整数或 `"X"`），用于显示 `[能量,辉星]`。

`self.draw` 是供检查的稳定排序视图，不代表未来抽牌顺序。公开路线通过 `mapView` 返回；服务端不会返回 RNG 内部状态、队友手牌或真实抽牌顺序。

### 选牌费用展示（可选字段）

卡牌候选的 `options[]` 和 `pendingDecision.options[]` 可带 `displayCards` 数组及 `displayPrefix` 字符串。每张展示牌包含 `id/name/cost/description`，可带 `starCost`；`cost` 为非负整数、`"X"` 或 `"—"`，`starCost` 为非负整数或 `"X"`。成组选择会包含组内每张牌。`displayPrefix` 保留“领取”等前缀，默认为空。

可选布尔标记 `freeEnergy/freeStars` 表示当前展示为零的对应资源因免费效果而免费；客户端可将该数字 `0` 显示为绿色。天然零费不附加免费标记。战斗选牌按当前实例和持有者计算费用；选中后免费、加入手牌或整场免费等效果只在副本上预览。X 与不可打出标记保持实际规则，费用增加后不再为零时不标为免费。牌组操作、永久奖励和组合选择显示非战斗实例费用。

展示数据只属于接收者，不包含原始候选实例、费用修改记录或随机流。`label` 仍包含完整纯文本费用，旧客户端可直接使用；没有展示字段时新客户端也继续使用 `label`。候选排序、选择身份、动作结构、规则及存档版本保持不变。提交时继续复制 `options[].action`，不得将展示牌作为 `play` 动作发送。

### 目标伤害预览

战斗快照的 `self.hand[]` 攻击牌，以及战斗牌堆的升级预览，可以包含可选的 `damagePreview`：

```json
{"basis":"currentStateBeforeBlock","byTarget":{"e0":{"damage":12,"hits":1},"e1":{"damage":18,"hits":1}}}
```

`byTarget` 的键为当前存活敌人的 ID。`damage` 是按当前状态计算、尚未扣除格挡的首段攻击伤害，复用实际攻击的动态基础值与伤害修正公式，包括完美打击、力量、活力、虚弱、易伤和适用的遗物效果；`hits` 是本次攻击的次数，可能为 0。它不是预计生命损失或整张牌的连锁结算总伤害；不提前执行出牌前触发、随机目标、抽牌、消耗触发、击杀追加攻击或重放，后续状态变化可能改变伤害。随机攻击的数值表示命中该敌人时的伤害，次数并不保证全部命中该敌人。

客户端在切换或悬停目标时读取对应项，收到新快照后刷新。非攻击牌不包含该字段；字段缺失时应显示常规说明。预览不改变房间状态，也不会透露抽牌顺序。

选项示例：

```json
{
  "id": "enemy-3",
  "label": "打击 [1] 造成 6 点伤害",
  "action": {
    "type": "play",
    "card": "card-17",
    "target": "enemy-3",
    "phaseId": 18
  },
  "choice": null
}
```

`action` 的具体字段会随阶段和内容变化。客户端应原样复制选中项的 `action`，不应自行重建该对象。若 `choice` 指示需要从 `deck`、`deckUpgrade` 等来源选牌，应根据 `pendingChoice`/界面选择补入服务端要求的 `choice` 或 `cards` 字段。

## 提交动作

```http
POST /api/games/spire/rooms/{roomId}/actions
Content-Type: application/json

{
  "actionId": "88c0df8e-28f2-4e3b-b424-8d1f4898c91f",
  "leaseId": "8fe2f945-ee94-4577-82ee-df91e79774d7",
  "action": {
    "type": "ready"
  }
}
```

- `actionId`：每个逻辑动作新建一个 UUID，在同一房间、同一账号内去重。
- `leaseId`：最新 WebSocket 快照中的值。重新连接后须使用新租约。
- `action`：从最新快照 `options[].action` 复制；除 `pause`、`ready`、`abandon` 外必须携带当前 `phaseId`，包括 `character`。
- `action` 序列化后最多 8 KiB（按服务端转义非 ASCII 字符后的 JSON 计算，不是 HTTP 请求体长度）。

相同 `actionId` 和完全相同的 `action` 可安全重试，不会重复执行，响应为当前投影。相同 `actionId` 携带不同动作返回 `409`。成功响应是动作执行后的完整玩家投影，但不含 `leaseId`；继续使用 WebSocket 保存的当前租约。操作者不会收到同一动作的额外 WS 快照，其他成员仍正常收到广播。

动作接口按租约限流，每个租约每秒最多 12 个动作。其他 HTTP 接口按当前账号限流，每分钟最多 120 次。

常见动作类型包括 `ready`、`character`、`vote`、`play`、`end`、`undoEnd`、`potion`、`reward`、`buy`、`rest`、`event`、`choose`、`decide`、`continue` 和 `abandon`。该列表不是稳定枚举；是否可执行仍以最新 `options` 为准。

<a id="action-reference"></a>

### 动作参考

除战斗中的出牌、药水与结束回合外，所有动作都从 `options[].action` 复制。下表帮助客户端补全字段，不代替 `options`。

**选项中的补充字段**

| 选项字段 | 客户端处理方式 |
| --- | --- |
| `choice: "deck"` | 在 `action.choice` 填入 `self.deck` 中的卡牌 ID（移除、事件选牌等） |
| `choice: "deckUpgrade"` | 填入 `self.deck` 中可升级的卡牌 ID（营地升级等） |
| `choice: "deckEnchant"` | 填入 `self.deck` 中的卡牌 ID（附魔类事件） |
| `pick` | 多选候选行，本身没有动作；按 `pendingChoice.minimum..maximum` 收集若干 `pick`，填入 `id` 为 `confirmChoice` 的选项所对应动作的 `cards` 数组后提交 |
| `pendingDecision` | 单选时每行均为 `{"type":"decide","decisionId":..,"selections":[id]}`；多选时将多个 `pendingDecision.options[].id` 合并至 `selections`；`minimum` 为 0 时可提交空数组表示取消 |

`pendingChoice` 为 1 张时每行都是完整的 `{"type":"choose","choiceId":..,"cards":[cardId]}`，`minimum` 为 0 时另有跳过行（`cards:[]`）。存在本人的 `pendingChoice` 时只接受 `choose`，存在本人的 `pendingDecision` 时只接受 `decide`；有未领取的卡牌、遗物或金币奖励时只接受奖励类动作和药水动作。

**战斗动作由客户端构造**

战斗阶段的 `options` 只包含选牌、决定和奖励；出牌、药水和回合控制按以下格式构造，并携带当前 `phaseId`：

| 动作 | 格式 | 说明 |
| --- | --- | --- |
| 出牌 | `{"type":"play","card":"手牌 ID","target":"e0","choice":"另一张手牌 ID"}` | `self.hand[].target` 为 `enemy` 时须提供存活敌人的 ID；为 `ally` 时须提供存活队友的玩家 ID（UUIDv7 字符串，不得为当前玩家）；其他目标省略 `target`。`self.hand[].choice` 为 `upgrade` 或 `exhaust` 时，在 `choice` 填入另一张手牌 ID |
| 药水 | `{"type":"potion","potion":"药水 ID","target":"e0"}` | `self.potions[].target` 为 `AnyEnemy` 时须提供敌人 ID；`AnyPlayer` 可指定玩家 ID，省略时作用于当前玩家。`usage` 为 `Automatic` 的药水不能主动使用，非 `AnyTime` 的药水只能在战斗中使用 |
| 丢弃药水 | `{"type":"dropPotion","potion":"药水 ID"}` | 药水栏满时可先丢弃再领取新药水 |
| 结束回合 | `{"type":"end"}` / `{"type":"undoEnd"}` | 以 `endTurn.canEndTurn` / `canUndoEndTurn` 为准；合作中全员结束后敌方才行动 |

手牌没有「可打出」字段：`cost` 为整数且不大于当前能量（带 `starCost` 时辉星数量也须满足要求）、`kind` 不是 `status`/`curse`、描述中没有「无法打出」时才应尝试；`cost` 为 `"X"` 时消耗全部能量。最终是否合法以服务端结果为准，`invalid_action` 表示应重新读取快照后再决策。

**各阶段常见动作**

| 阶段 | 动作 |
| --- | --- |
| `lobby` | `ready`；`character`（`{"type":"character","character":"silent"}`，仅大厅或开局前未定角色时提供） |
| `map` | `vote`（`{"type":"vote","node":"0:1:2"}`），节点 ID 与 `mapView.reachable` 一致；合作中全员投票后按种子从所有选票中**随机抽取一张**，不是多数决 |
| `reward` | `reward`（`card` 为卡牌 ID、`skip`，可能有 `reroll`/`sacrifice`）、`goldReward`（`choice: claim/skip`）、`customRelicReward`、`customReward`、`claimPotion`/`skipPotion`、`rewardRemove`（带 `choice:"deck"`）/`skipRemoval` |
| `rest` | `rest`（`option`：`heal`、`upgrade`（带 `choice:"deckUpgrade"`）、`mend`（随后用 `decide` 选择存活队友）、以及遗物带来的其他选项）；`continue` |
| `shop` | `buy`（`item`，行内 `shop` 字段给出商品详情与价格）、`removeCard`（带 `choice:"deck"`）、`continue` |
| `event` | `event`（`option`、`event`、`page`）；后续选择以 `pendingChoice`/`pendingDecision` 出现。先古之民也是 `event` 阶段 |
| `treasure` | `treasurePick`（`index`，`null` 表示放弃，合作中为可更改的投票）；结算后 `continue` |
| `actComplete` | `nextAct`，全员提交后进入下一幕 |
| `ending` | `event`（终章选项） |

`victory`、`defeat`、`abandoned` 为终局，没有选项。房主在任何阶段都可以提交 `abandon`。

## 只读接口

### 战斗日志

```http
GET /api/games/spire/rooms/{roomId}/logs?battleId=3&after=100&limit=100
```

读取当前战斗的结构化日志。`limit` 范围为 1 到 200，默认 100；`before` 与 `after` 不能同时使用。传入的 `battleId` 与当前战斗不符时返回 `409 stale_phase`。响应包含 `battleId`、`total`、`first`、`last`、`incomplete`、`entries`、`before` 和 `after`。日志按调用者身份投影，队友的私有抽牌和卡牌来源不会泄露。该接口不需要租约，不改变状态。

### 查看玩家装备

```http
GET /api/games/spire/rooms/{roomId}/players/{playerId}/inspection?page=0&size=40
```

调用者必须已加入房间。`page` 从 0 开始，`size` 范围为 1 到 200，默认 40。越界的页返回空 `rows`；负数 `page` 或超出范围的 `size` 返回 `400 invalid_request`。响应的 `pageSize` 为本次使用的每页数量。该接口不需要租约，也不改变房间状态。

```json
{
  "player": "00000000-0000-7000-8000-00000000001b",
  "name": "Bob",
  "character": "silent",
  "hp": 52,
  "maxHp": 70,
  "gold": 121,
  "total": 16,
  "pageSize": 40,
  "page": 0,
  "rows": [
    {
      "id": "card-22",
      "pile": "deck",
      "key": "StrikeSilent",
      "upgraded": false,
      "name": "打击",
      "cost": 1,
      "description": "造成伤害。"
    }
  ]
}
```

`rows[].pile` 为 `deck`、`relics`、`potions` 或 `status`；不同类型的行字段不同。响应不会暴露队友手牌、抽牌顺序或私有选择。

### 卡牌升级预览

完整快照的 `upgradePreviews[source][cardId]` 提供 `{card,before,after}`，source 为 `hand/deck/draw/discard/exhaust/reward/shop`。缺少某张牌的条目表示该来源下没有可用升级预览。同一卡牌在手牌与永久牌组中的费用、效果可能不同，必须按来源读取。

收到新快照时整体替换预览。预览不会真正升级卡牌，实际升级通过动作提交。

## 错误格式

接口出错时通常返回 `{"message":"..."}` 或结构化错误对象（当路由返回结构化错误时格式如下）：

```json
{
  "error": {
    "code": "stale_phase",
    "message": "阶段已经变化，请刷新快照。",
    "retryable": false
  },
  "requestId": "025582fc-f509-4700-b73f-47000c59a684"
}
```

HTTP 响应同时包含：

```http
X-Request-ID: 025582fc-f509-4700-b73f-47000c59a684
Cache-Control: no-store
```

常见错误码：

| HTTP | `error.code` | 处理方式 |
| --- | --- | --- |
| `400` | `invalid_request` | 修正查询参数或请求语义 |
| `401` | `invalid_token` | 检查用户登录会话是否有效或是否误用了已移除的 `lc_api_*` Key |
| `403` | `not_participant` | 当前账号尚未加入房间或无权操作该存档 |
| `404` | `room_not_found` | 房间不存在或因单人房间隐私而不可见 |
| `404` | `player_not_found` | 玩家不在该房间 |
| `409` | `stale_phase` | 获取最新快照后，用新 `actionId` 重新决策 |
| `409` | `stale_lease` | 重新连接 WebSocket，使用新 `leaseId` |
| `409` | `invalid_action` | 丢弃本地动作，从最新 `options` 重新选择 |
| `409` | `idempotency_conflict` | 同一 `actionId` 被用于不同动作，或当前连接内同一 `messageId` 被用于不同消息内容；改正客户端逻辑 |
| `403` | `invalid_room_password` | 房间密码缺失或错误 |
| `409` | `host_offline` | 等待房主上线后重新加入 |
| `409` | `incompatible_room` | 存档版本与当前服务端不兼容，无法继续 |
| `413` | `action_too_large` | 缩小动作 JSON |
| `422` | `validation_error` | 按接口模型修正字段、类型或额外字段 |
| `429` | `rate_limited` | 按 `Retry-After` 等待 |
| `503` | `spire_unavailable` | 仅在 `retryable=true` 时指数退避重试 |

登录会话接口在简单校验失败时也直接返回 `{"message":"..."}`。

## 重试与并发

- 创建房间重试：保留同一个 `requestId` 和完全相同的请求参数。
- 动作重试：保留同一个 `actionId`、`leaseId` 和完全相同的 `action`。
- 收到 `stale_phase`、`stale_lease` 或 `invalid_action`：不应直接重复提交原动作；先取得最新快照，再用新的 `actionId` 决策。
- 收到 `429`：遵循 `Retry-After`。游戏动作的限制以租约为单位。
- 收到可重试的 `5xx`：使用带抖动的指数退避。创建和动作已有幂等键，重试时不得生成新键。
- 多人共享阶段允许不同玩家并发提交普通动作；服务端按房间串行写入数据库，并用 `revision` 防止覆盖。

## curl 示例

```bash
export LINKCHAT_BASE_URL='https://linkchat.online'
export ROOM_ID="$(python -c 'from uuid6 import uuid7; print(uuid7())')"

# 先通过 /api/users/login 登录并将 Cookie 保存到 cookies.txt
curl --fail-with-body -c cookies.txt \
  "$LINKCHAT_BASE_URL/api/users/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"your-email@example.com","password":"your-password"}'

curl --fail-with-body -b cookies.txt \
  "$LINKCHAT_BASE_URL/api/games/spire/rooms"

curl --fail-with-body -b cookies.txt \
  "$LINKCHAT_BASE_URL/api/games/spire/rooms" \
  -H 'Content-Type: application/json' \
  -d "{\"requestId\":\"$ROOM_ID\",\"mode\":\"coop\",\"seed\":\"EXTERNAL-DEMO-001\"}"

curl --fail-with-body -b cookies.txt \
  "$LINKCHAT_BASE_URL/api/games/spire/rooms/$ROOM_ID"
```

curl 适合调试 HTTP 接口；获取 `leaseId` 并执行游戏操作需使用 WebSocket 客户端。

## Python 最小控制示例

以下示例需要 `httpx` 和 `websockets`：

```python
import asyncio
import json
import os
import uuid
from uuid6 import uuid7

import httpx
import websockets

BASE = os.getenv("LINKCHAT_BASE_URL", "https://linkchat.online").rstrip("/")
TOKEN = os.environ["LINKCHAT_SESSION_TOKEN"]  # 从 POST /api/users/login 的 linkchat_session Cookie 获取
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS) as http:
        room_id = str(uuid7())
        response = await http.post(
            "/api/games/spire/rooms",
            json={
                "requestId": room_id,
                "mode": "solo",
                "seed": "PYTHON-DEMO-001",
            },
        )
        response.raise_for_status()
        room_id = response.json()["id"]

        ws_url = BASE.replace("https://", "wss://").replace("http://", "ws://")
        async with websockets.connect(
            f"{ws_url}/ws/games/spire/rooms/{room_id}",
            subprotocols=["linkchat-game-v8"],
            additional_headers=HEADERS,
        ) as ws:
            snapshot = json.loads(await ws.recv())
            lease_id = snapshot["leaseId"]

            assert snapshot["protocol"] == 8
            # Pick one explicit action offered by this snapshot.
            action = next(
                row["action"] for row in snapshot["options"]
                if row.get("action") and row["action"]["type"] not in ("abandon", "pause")
            )
            action = {**action, "phaseId": snapshot["phaseId"]}
            action_id = str(uuid.uuid4())
            await ws.send(json.dumps({
                "type": "ACTION", "actionId": action_id,
                "leaseId": lease_id, "action": action,
            }))
            while True:
                message = await ws.recv()
                if message == "PONG":
                    continue
                event = json.loads(message)
                if event.get("type") == "ACTION_ERROR":
                    raise RuntimeError(event["error"])
                if event.get("type") == "ACTION_RESULT" and event["actionId"] == action_id:
                    snapshot = event["state"]
                    break
            # Closing this demo's controller pauses its room.

asyncio.run(main())
```

示例需要支持 `additional_headers` 参数的 websockets 版本。实际客户端应持续运行接收循环和心跳循环：先区分 `ACTION_RESULT` / `ACTION_ERROR`，再按 `revision` 应用确认响应中的 `state` 或新快照。订阅房间聊天后，应先分流 `ROOM_CHAT` 事件，避免覆盖游戏状态。

## 版本兼容

- 客户端必须检查快照和房间列表中的 `protocol`，发现不支持的版本时应停止操作并提示升级。控制连接必须使用子协议 `linkchat-game-v8`，旧子协议将在握手阶段被拒绝。
- `rules` 或 `content` 变化时，服务端不会重算旧存档；不兼容的存档会被拒绝加载。
- 可忽略未知响应字段，但不应假设 `options[].action` 的字段固定不变。
- 不应依赖动作类型的完整列表、选项顺序或中文 `label` 文案来判断规则。
- 本接口不支持导入原作存档、连接原作联机，也不提供随机数内部状态。

<a id="room-chat"></a>

## 房间即时聊天

房间聊天独立于频道聊天，仅允许当前房间成员收发消息。消息不持久化至存档、战斗日志或频道，不提供历史记录，断线重连后不补发。快照中 `features.roomChat: true` 表示支持此功能。

客户端通过 `/ws/games/spire/rooms/{roomId}?roomChat=1` 显式订阅聊天事件，认证方式和 `linkchat-game-v8` 子协议不变。未订阅聊天时不发送 ROOM_CHAT；游戏快照、动作确认与 PONG 不受影响。客户端应先按 `type === "ROOM_CHAT"` 分流聊天事件，再校验游戏快照；聊天不会推进 `revision` 或 `phaseId`。

发送接口：`POST /api/games/spire/rooms/{roomId}/chat`，需要当前登录会话、房间成员身份及当前连接的 `leaseId`。请求示例：

```json
{
  "messageId": "8ff3e207-f23c-4556-96cb-b99837b92240",
  "leaseId": "7c2f5634-78e1-4e6d-8a48-b7d7d2c18f30",
  "content": "等我一下，先不要结束回合"
}
```

示例 UUID 仅用于展示格式；实际调用时生成新的 `messageId`，并使用当前房间 WebSocket 快照中的 `leaseId`。

`content` 原始输入为 1–200 个 Unicode 码点的纯文本；先将空白（包括换行与制表符）归并为空格，再拒绝空白内容、剩余 C0/C1 控制符及 U+202A–U+202E、U+2066–U+2069 双向文本控制符。作者身份由服务端确定，不允许通过请求指定。每个当前玩家租约每 10 秒最多发送 5 条，超过返回 429；此额度与游戏动作额度分开，同时受账号每分钟 120 次非动作 HTTP 请求额度限制。

成功响应与 WebSocket 事件使用同一对象：

```json
{
  "type": "ROOM_CHAT",
  "id": "8ff3e207-f23c-4556-96cb-b99837b92240",
  "roomId": "019a0e24-6b79-72e0-93bd-a59c442aa315",
  "userId": "00000000-0000-7000-8000-00000000000c",
  "name": "Alice",
  "content": "等我一下，先不要结束回合",
  "createdAt": "2026-09-24T03:00:00+00:00"
}
```

当前连接内消息 ID 的去重回执保留 60 秒，相同 ID 与内容返回同一确认且不重复广播；相同 ID 用于不同内容时返回 409。回执随连接释放，仅用于短期重试，不是消息历史。广播前重新检查每位接收者的访问权限。

### 接收与发送示例

连接地址为 `wss://linkchat.online/ws/games/spire/rooms/{roomId}?roomChat=1`。接收循环应先识别心跳，再分流聊天事件与游戏快照：

```python
raw = await ws.recv()
if raw == "PONG":
    pass
else:
    event = json.loads(raw)
    if event.get("type") == "ROOM_CHAT":
        # 按 (roomId, userId, id) 去重；首次收到后显示 60 秒。
        show_room_message(event)
    else:
        # 这里才执行 protocol、revision 等游戏快照校验。
        accept_snapshot(event)
```

上例的 `show_room_message` 和 `accept_snapshot` 由客户端实现，仍需独立运行心跳。消息通过 HTTP 发送，不通过 WebSocket 提交：

```bash
curl -sS -X POST "https://linkchat.online/api/games/spire/rooms/$ROOM_ID/chat" \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  --data '{"messageId":"8ff3e207-f23c-4556-96cb-b99837b92240","leaseId":"7c2f5634-78e1-4e6d-8a48-b7d7d2c18f30","content":"等我一下"}'
```

设置 `ROOM_ID`、已登录的 `cookies.txt` 并替换请求中的 UUID；当前控制连接必须保持打开。HTTP 确认也可用于展示本人消息，但须与 WebSocket 推送的消息去重。5xx 或网络中断后的短期手动重试复用同一消息 ID 和内容；重连后须使用新租约。旧连接的去重回执不跨连接保留，因此重新发送不具备跨连接幂等保证。

## 资料库（只读）

以下接口只需要用户登录会话：

- `GET /api/games/spire/catalog`：内容版本、能力声明、分类数量、五角色初始配置、A0–A10 说明。
- `GET /api/games/spire/catalog/{category}`：`category` 为 `cards/monsters/relics/potions/characters`。支持 `q`、`group`、`offset`（默认 0）、`limit`（1–100，默认 50）；返回 `items/total/groups/offset/limit/version`。
- `GET /api/games/spire/catalog/{category}/{id}`：返回名称、`lines` 与关联 `links`。卡牌支持 `upgraded=true`，怪物支持 `ascension=0..10`；怪物为单人基础生命、全部招式、初始状态与部分条件说明，实际动作顺序由战斗状态决定。

`category` 是大类；响应的 `groups` 是该大类全部小类名称，不受当前搜索词、分页或 `group` 筛选影响。卡牌按角色/卡池分组，遗物和药水按角色/通用/特殊分组，怪物按遭遇类型分组。将返回的名称原样作为 `group` 传回；省略或传空字符串表示全部。`q` 和 `group` 最多 100 个字符，`offset` 必须非负。

中文查询参数必须进行 URL 编码，例如：

```bash
curl -sS --get 'https://linkchat.online/api/games/spire/catalog/cards' \
  -b cookies.txt \
  --data-urlencode 'group=铁甲战士' \
  --data-urlencode 'q=打击' \
  --data-urlencode 'limit=40'
```

列表条目至少包含 `id/name/group`，部分大类还有 `kind/rarity`。详情中的 `links` 是 `{category,id,name}` 数组，指向关联的卡牌或遗物。

资料库只读，不影响任何房间或存档。

## 场景 SL

SL 用于将当前场景恢复至进入该场景时的初始状态。支持战斗、事件、营地、商店和宝箱；事件中触发的战斗或奖励会恢复到整个事件的开始。奖励阶段、地图、终局或没有存档点时返回 `409 sl_unavailable`。

快照中 `features.sl=true` 表示支持 SL，`sl={available,token,hostOnly,canReset}` 描述当前场景：`token` 是当前场景和阶段的随机 UUID（不是节点编号），`canReset` 表示当前账号是否具有发起 SL 的权限。单人游戏随时可以恢复；多人游戏只有房主能直接恢复，不需要投票，其他成员请求会返回 `403 host_only`。

发起 SL：通过 `POST /rooms/{id}/chat` 发送 `content:"/sl"`，同时携带 `messageId`、当前控制连接的 `leaseId` 和 `scopeToken`（即快照中的 `sl.token`）。普通聊天不需要 `scopeToken`。SL 同样需要当前登录会话、房间成员身份和当前租约。成功后房间会收到一条 `ROOM_CHAT`（带 `command:"sl"`、`restored`）和新的完整快照。

- 恢复范围包含随机数状态，相同操作序列将产生相同结果。
- 进入新场景会清除旧的存档点；阶段变化或暂停时 `token` 会更换。
- SL 成功后 `revision` 和 `phaseId` 都会增加，旧的动作和选择不能再执行。
- 用同一个 `messageId` 和 `token` 重试会返回原结果，不会重复恢复；用旧 `token` 发起新请求返回 `409 stale_checkpoint`。

## 存档托管

存档拥有者可将整局存档委托给其他账号操作，支持指定账号或开放公开邀请，由首个符合条件的账号接管。受托账号以自身身份操作原角色，存档拥有者可旁观并随时收回控制权。房间列表的 `features.delegation=true` 表示服务端支持此功能。

以下路径均以 `/api/games/spire/rooms/{roomId}` 为前缀，使用操作者本人的登录会话：

| POST 路径 | 请求体 | 行为 |
| --- | --- | --- |
| `/delegation` | `requestId` UUID、`revision`、可选 `inviteeId` UUIDv7 字符串、`allowSl`（默认 true） | 仅存档拥有者可开放；指定账号或公开首接管，保存独立的托管前快照与场景 SL 点并暂停 |
| `/delegation/{id}/claim` | `{}` | 指定账号或公开邀请的第一个存档外账号接管；重复接管不会新增角色 |
| `/delegation/{id}/restore-before` | `requestId` UUID、`revision` | 拥有者或已获 SL 权限的受托账号恢复托管前；授权仍有效 |
| `/delegation/{id}/revoke` | `revision`、`restoreBefore`（默认 false） | 仅拥有者收回，可保留当前进度或恢复托管前 |

邀请的 UUID 不是免认证凭证。公开房间列表只显示邀请摘要；接管前不能读取单人存档的私有牌组。现有房间成员不能同时接管另一角色。

托管期间，快照包含 `actorId`（实际操作者）、`readOnly` 和 `delegation`。`self.id` 始终为被操作的角色 ID；战斗日志分页与快照均按被操作角色的可见性返回，队友私有记录仍隐藏。旁观 `endTurn` 保留 `reason` 字符串，两个操作开关均为 false。动作回执记录实际操作者，角色、存档拥有者及奖励归属不变。托管中的拥有者连接为旁观，不会自动收回控制权；旁观客户端不得从手牌或 `endTurn` 合成操作。在线人数按角色控制席位计，不重复计算拥有者与受托账号。

`delegation` 包含 `id/status/ownerId/inviteeId/delegateId/allowSl/canRevoke/canRestoreBefore`。房间列表的 `canClaimDelegation` 表示当前账号是否可接管；发起者离线时邀请仍可见；托管中的终局存档保留可发现性，以便选择 SL。

开启 SL 时，受托账号可使用原有房间聊天 `/sl` 恢复当前场景，也可通过 `restore-before` 恢复整局到托管前。多人恢复影响整队，只有房主能授予此权限。恢复原随机流、场景存档点并重新建立阶段 ID；相关控制连接以 4001 关闭，需显式重连，旧写请求不能重新作用于恢复后的状态。回滚只撤销本房间产生的账号进度，其他房间不受影响。已有另一局活动单人存档时，禁止恢复旧存档以避免同时存在两个活动单人存档。

客户端对结果不确定的写请求保留原请求体和 UUID 重试；新的确认操作使用新的 UUID。恢复前端点按 UUID 去重；收回端点以授权 ID 和恢复方式去重，不能用旧请求撤销后续的新授权。受托账号没有放弃、替换或转移存档所有权的权限。

<a id="action-channel"></a>

## 低延迟动作通道

除 HTTP 外，客户端还可通过 WebSocket 控制连接直接提交动作，以降低通信延迟。游戏规则仍由服务端结算；所有控制连接均支持此通道，无需额外参数。

连接 `/ws/games/spire/rooms/{roomId}` 后，除了文本 `PING`，还可以发送动作 JSON：

```json
{
  "type": "ACTION",
  "actionId": "11111111-1111-4111-8111-111111111111",
  "leaseId": "当前连接取得的 UUID",
  "action": {"type": "play", "card": "卡牌实例 ID", "target": "目标 ID", "phaseId": 12}
}
```

`action` 字段与 HTTP 动作完全相同，具体字段以动作章节为准。成功返回一次完整快照确认，不再额外向操作者广播同一动作快照：

```json
{"type":"ACTION_RESULT","actionId":"原动作 UUID","state":{"revision":13,"leaseId":"当前租约","其他字段":"完整玩家快照"},"timing":{"rules":1.2,"commit":0.8,"total":4.1},"stopQueue":false}
```

失败返回 `{"type":"ACTION_ERROR","actionId":"原动作 UUID","error":{"status":409,"code":"invalid_action","message":"原因","retryable":false},"timing":{}}`。无有效动作 ID 的格式错误可能返回 `actionId:null`。认证失效会关闭连接。每次动作执行及每次下行发送均重新检查授权。

客户端可在前一动作确认前发送下一动作，并设置 `afterActionId` 为紧邻前序动作 UUID。服务端按同一连接的接收顺序执行；前序失败、阶段或回合变化、出现待选项、暂停或终局时，后续依赖动作返回 `409 queue_stopped`，不会执行。成功确认的 `stopQueue=true` 表示应停止继续发送该链。重复已提交动作只返回当前快照，且停止自动延续链。没有 `afterActionId` 的动作是独立请求。

客户端同时还会收到其他玩家动作引起的快照广播，按 `revision` 更新即可。

完整 WS 消息上限为解压后的 4 MiB，服务端完整下行 JSON 也按 UTF-8 字节检查；超限关闭 `1009`，客户端停止重试。动作对象序列化上限仍为 8 KiB；每玩家每秒最多 12 个新动作。心跳仍使用文本 PING/PONG。慢连接下行队列最多 32 条，溢出关闭码为 `1013`；客户端应重连取得最新快照。旧子协议无法建立控制连接。

### HTTP 单动作与断线核对

`POST /api/games/spire/rooms/{id}/actions` 返回完整快照，同时广播给其他成员，不再向操作者额外发送同一快照。

HTTP `?receiptOnly=true` 只查询已有成功回执，不执行新动作；无回执返回 `409 action_not_committed`。**未查询到回执不表示动作已取消**：其他连接或此前排队的动作可能仍在执行。

### WebSocket 有序核对

快照中 `features.actionSync=true` 表示支持核对。动作超时、结果未知或断线重连后，可发送 `SYNC` 查询动作的提交状态。

```json
{"type":"SYNC","requestId":"请求 UUID","leaseId":"当前租约 UUID","actionIds":["待确认动作 UUID"]}
```

`actionIds` 最多 8 个，可为空。服务端在该连接此前动作处理完后，于房间锁内重新验证当前租约并查询回执：

```json
{"type":"SYNC_RESULT","requestId":"请求 UUID","leaseId":"当前租约 UUID","results":[{"actionId":"动作 UUID","status":"committed"}],"state":{"其他字段":"最新完整快照（含 leaseId）"}}
```

每个动作的状态为 `committed` 或 `not_committed`。核对期间不得发送新动作，收到结果后先应用 `state` 再继续。未提交的动作应由玩家重新选择，不应自动重发。核对超时时重新连接，用新租约再核对一次。

关闭码：临时故障或超时为 `1011`，拥塞为 `1013`，授权失败为 `1008`，租约被替换为 `4001`。握手返回 4xx（408、429 除外）时停止重连；网络错误和 5xx 继续退避重连，429 按 `Retry-After` 等待。建议退避间隔为 1、2、4、8、15 秒并加随机抖动，连接稳定 30 秒后再重置。

HTTP 普通重试仍可用原 actionId 重发；这可能执行尚未提交的动作，因此不应将整条不确定队列直接逐一重发。WS 5xx 或连接中断属于结果未知，不能据此判断事务一定失败。

### HTTP 批量动作

`POST /api/games/spire/rooms/{id}/actions/batch`：

```json
{
  "batchId":"22222222-2222-4222-8222-222222222222",
  "leaseId":"当前租约 UUID",
  "actions":[
    {"actionId":"33333333-3333-4333-8333-333333333333","action":{"type":"play","card":"卡牌实例 ID","phaseId":12}}
  ]
}
```

一次 1–8 个动作，actionId 不得重复，规范化后的动作数组上限 64 KiB，单动作及频率限制同单动作接口。返回：

```json
{"batchId":"原批次 UUID","results":[{"actionId":"已完成动作 UUID","revision":13,"duplicate":false}],"stopped":null,"state":{"其他字段":"最终完整快照"},"timing":{"total":5.4}}
```

动作按顺序执行，遇到首个无效动作停止，成功前缀和批次回执在同一事务提交；内部保存或提交异常则整批回滚。无效动作记录为 `stopped:{index,actionId,error}`（索引从 0 开始）；阶段、回合、待选择等边界或已存在动作回执会截断尾部，记录为 `stopped:{index,reason:"decision_boundary"}`。因此 HTTP 200 不代表所有步骤均执行，必须检查 results 和 stopped。首步租约等校验失败也可返回空 results 和 stopped，并保存该批次结果。

同 batchId、同有序动作列表重试，返回原 results/stopped 和当前快照，不会继续执行原批次中未执行的后续动作；允许重连后更换 leaseId。同 batchId 更换动作列表返回 `409 idempotency_conflict`。批量接口只向其他成员广播，操作者使用响应更新。建议只批量发送当前状态下已确定的连续操作，在需要选择目标、奖励或下一阶段时重新读取快照。

### 压缩与耗时

超过 1024 字节的 JSON 响应会在客户端支持时使用 gzip 压缩，WebSocket 支持 permessage-deflate。两者都是可选的，不支持压缩的客户端也能正常连接。

HTTP 动作的成功响应带有 `Server-Timing` 头，WebSocket 确认和批量响应带有 `timing` 字段，单位为毫秒，表示服务端处理各阶段的耗时，不含网络传输时间。
