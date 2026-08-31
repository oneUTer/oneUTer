# oneUTer GitHub Profile · 使用说明

这套文件面向公开仓库 **`oneUTer/oneUTer`**。主线是 Java 后端与 AI Agent，科研背景位于后半部分。正文以英文为主，配有中文定位说明。

## 文件结构

```text
oneUTer/
├── README.md                 # 主页正文
├── assets/
│   └── header.svg            # 自带的深色动态横幅，必须一起上传
├── .github/
│   └── workflows/
│       └── snake.yml         # 贡献蛇生成与发布工作流
└── SETUP.md                  # 本说明，不会直接显示在个人主页
```

## 首次发布

1. 文件已写入本地 `D:\oneUTer`，本次没有自动提交或推送。先检查 README 中的个人介绍是否准确。
2. 确认 GitHub 仓库名为 `oneUTer`、所有者为 `oneUTer`，且可见性为 **Public**；README 必须在仓库根目录。[GitHub 官方说明](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
3. 将上述文件提交并推送到默认分支 `main`。如果使用网页上传，不要把压缩包本身或外层文件夹当成主页上传；确认隐藏的 `.github` 文件夹也已上传。
4. 打开仓库 **Actions → Generate contribution snake**。首次推送会触发生成；也可以点击 **Run workflow → main → Run workflow** 手动运行。
5. 等任务成功后，工作流会创建或更新 `output` 分支，README 自动读取其中的浅色、深色 SVG 动画，无需手工创建分支或复制生成的图片。

已有本地仓库时，可以在 PowerShell 中逐行执行：

```powershell
Set-Location 'D:\oneUTer'
git status
git add README.md assets/header.svg .github/workflows/snake.yml SETUP.md
git commit -m "feat: refresh profile with Java backend and AI Agent focus"
git push origin main
```

## 动画与权限

- 默认每天 **北京时间 09:23** 更新，使用 UTC 定时配置；GitHub 调度可能延迟。修改 README 或工作流并推送到 `main` 也会触发生成。
- 使用 GitHub 自动提供的 `GITHUB_TOKEN`，不需要手动创建 PAT，也不要把个人令牌写进文件。工作流已声明 `contents: write`，用来写入本仓库的 `output` 分支。
- 若出现 403 / `Permission denied`，检查 **Settings → Actions → General** 中的 Actions 策略、Workflow permissions 以及分支规则是否允许该任务写入 `output`。组织限制可能需要管理员处理。
- `output` 用于生成物；不要把手写主页放到该分支。本配置保留生成物分支历史，不使用强制推送。**不需要启用 GitHub Pages**。
- 首次成功运行前，snake 图片暂时无法加载，这是正常的；成功后仍未显示时，先检查 `output` 中是否有两个 SVG，再等待 GitHub 图片缓存刷新。
- 若长期未更新，检查 Actions 是否停用。公开仓库连续 60 天没有仓库活动时，定时工作流可能被自动禁用；在 Actions 中重新启用即可。[GitHub 调度规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 自定义与显示说明

- 自带横幅是轻量 SVG，使用缓慢的信号、流线和光标动画；尊重系统“减少动态效果”设置。横幅无需第三方图片生成服务。
- GitHub 不允许 README 强制更改整页背景。本套横幅和图标采用深色科技风，正文跟随访问者的 GitHub 主题；snake 提供深浅色版本，使用 `prefers-color-scheme` 匹配浏览器的配色偏好。
- 技术图标与徽章来自 [Skill Icons](https://skillicons.dev/) 和 [Shields.io](https://shields.io/)，需要网络加载；即使服务暂时不可用，正文仍可阅读。
- 技术项写作“当前学习/探索方向”，没有编造项目、熟练度、性能指标、邮箱或工作经历。真实项目公开后，可在 **Build Log** 中补充项目链接、你的贡献和可验证的结果。
- 若默认分支不是 `main`，请修改 `snake.yml` 的 `push.branches` 和上面的推送命令。定时、手动触发所需的工作流应存在于默认分支。
- 若更改用户名，需同步修改 README 的链接、工作流中的仓库判断及横幅文字。
- 两个 Actions 依赖已固定到核对过的提交，升级时需主动更新。生成方式参考 [Platane/snk 官方用法](https://github.com/Platane/snk)，发布参数参考 [发布 Action 源码](https://github.com/crazy-max/ghaction-github-pages/blob/df5cc2bfa78282ded844b354faee141f06b41865/src/main.ts)。

## 验证范围

交付前检查了文件结构、README 引用、SVG 与 YAML 语法以及本地渲染。没有在你的 GitHub 账户上实际运行 Actions；首次发布后，请以 Actions 中的运行结果为准。
