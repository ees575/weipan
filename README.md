# 尾盘摸高选股（GitHub 版）

24 小时在线，不需要任何人的电脑开机。

## 一次性开通（3 步）

1. 在 GitHub 上建一个空仓库，名字随便（比如 weipan），**不要**勾选 README
2. 把本目录推到该仓库：
   `ash
   git init && git add -A && git commit -m init
   git remote add origin git@github.com:ees575/weipan.git
   git push -u origin main
   `
3. 仓库 → Settings → Pages → Source 选 **GitHub Actions**

完成后访问：https://ees575.github.io/weipan/

## 刷新频率

交易时段（北京时间 09:30-11:30、13:00-15:00）每 **5 分钟** 自动跑一次全市场扫描，
把结果写进 docs/index.html 并发布。

尾盘关键时点能拿到：14:35 / 14:40 / 14:45 / 14:50 / 14:55 / 15:00

## 注意

- GitHub 免费额度：公开仓库 Actions 不限时长
- Pages 是公开页面，知道网址的人都能看（没有密码门）
- 页面是静态的，不是 2 秒实时——想要秒级必须有自己的服务器

## 手动跑一次

Actions 页面 → 尾盘摸高选股 → Run workflow
