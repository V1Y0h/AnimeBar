// AnimeBar Capture —— IINA 插件
//
// 实测结论（都是在这台机器上撞出来的，别再踩）：
//
// 1. keyBinding 的键名必须用小写：`Ctrl+Alt+k` 生效，`Ctrl+Alt+K` 不生效，
//    而且失效时只会有系统提示音，没有任何错误提示。
// 2. 不要走 input.conf：IINA 不认外部手工放进 input_conf 的文件，
//    必须通过「设置 → 按键 → 导入已有的配置文件」登记。
// 3. 即使登记成功，`run` 命令里的 `${time-pos}` 也不会被展开——
//    会原样传进 URL，时间码变成 0。所以取时间必须走插件 API。

const { core, menu, utils, console } = iina;

function capture() {
  const pos = core.status.position;
  const title = core.status.title || "";

  if (typeof pos !== "number" || !isFinite(pos)) {
    core.osd("AnimeBar：取不到时间码");
    return;
  }

  const url =
    "animebar://capture?t=" +
    pos.toFixed(3) +
    "&src=iina&title=" +
    encodeURIComponent(title);

  utils
    .exec("/usr/bin/open", [url])
    .then(function () {
      core.osd("AnimeBar 已记录 " + pos.toFixed(1) + "s");
    })
    .catch(function (err) {
      core.osd("AnimeBar 唤起失败");
      console.log("animebar: exec 失败 " + String(err));
    });
}

menu.addItem(
  menu.item("AnimeBar：记录当前时间", capture, { keyBinding: "Ctrl+Alt+k" }),
);
