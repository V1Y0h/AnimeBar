# IINA 集成

在 IINA 里按 **⌃⌥K**，把当前播放位置（秒）和片名交给 AnimeBar.app，写入
`~/Library/Application Support/AnimeBar/creation-log.jsonl`。

## 安装

```bash
/Applications/IINA.app/Contents/MacOS/iina-plugin link \
  "/Users/jerryli/Documents/deepseek-harness/实验/AnimeBar/integrations/iina/plugin"
```

会在 `~/Library/Application Support/com.colliderli.iina/plugins/` 下建一个
`plugin.iinaplugin-dev` 符号链接。**开发链接指向本仓库**，所以移动仓库目录会断链。
要脱离仓库，打包成正式插件：

```bash
/Applications/IINA.app/Contents/MacOS/iina-plugin pack plugin
```

然后双击生成的 `.iinaplgz`。

卸载：`iina-plugin unlink <本目录>`。

## 三条踩过的坑（都验证过，别再试）

### 1. keyBinding 的键名必须小写

`{ keyBinding: "Ctrl+Alt+k" }` 生效；写成 `"Ctrl+Alt+K"` 不生效。
失效时**没有任何报错**，只有系统提示音，极易误判成「插件没加载」。

### 2. IINA 不认手工放进 input_conf 的文件

外部直接写入 `input_conf/AnimeBar.conf` 不会被当成 profile 加载（文件的修改时间一直不变就是证据）。
必须走「设置 → 按键 → 导入已有的配置文件」由 IINA 自己登记。

### 3. `run` 能用，但 `${time-pos}` 不展开

这是最费时的一条。input.conf 里

```
Ctrl+Alt+k run "/usr/bin/open" "animebar://capture?t=${time-pos}&src=iina"
```

`run` **确实执行了**（日志里留下了 `t_start: 0` 的记录），但 `${time-pos}` 被原样传下去，
AnimeBar 解析成 0。且没有任何可见反馈，表现和「完全没反应」一模一样。

**结论：取时间码必须走插件 API 的 `core.status.position`，不能指望属性展开。**

## 已知限制

- 只覆盖 IINA。Safari / Chrome 里的网页播放器（如 Abema）不在范围内，需要另做浏览器侧方案。
- 插件是主入口（`entry`）实现，`core` 只在这个上下文可用；`global` 入口有全局菜单但拿不到播放位置。
- 片名走 `title` 参数，已做 URL 编码，中文/空格都安全。
