# HITwh-daily-report

感谢 [HITsz-daily-report](https://github.com/JalinWang/HITsz-daily-report) 的架构

感谢 [Cyberenchanter/HITWH-jktb](https://github.com/Cyberenchanter/HITWH-jktb) 的原始脚本

---

# 疫情无小事，切勿瞒报而破环疫情防治工作

## 本脚本仅为减轻班长和导员的工作压力, 如有不适，请如实手动填写，并及时告知导员！！！

## 本脚本仅为减轻班长和导员的工作压力, 如有不适，请如实手动填写，并及时告知导员！！！

## 本脚本仅为减轻班长和导员的工作压力, 如有不适，请如实手动填写，并及时告知导员！！！



# 使用方法

**！！注意，由于我放在服务器上，故硬编码了 username 和 password，如果你要使用 github action，请自行修改，如果因此泄漏密码， 本人概不负责！！**



1. 安装 requirements.txt 中的包

```python
pip install -r requirements.txt
```

2. 修改 user.json 中的 `username` `password` `wechatOpenID` `userAgent`

>`username`: 工软校园的用户名， 也是学号
>
>`password`: 工软校园的密码
>
>`wechatOpenID`: 通过抓包获取， 你可以使用 Packet Capture (Android) 之类的软件抓取
>
>`userAgent`: 同上

3. 设置定时任务

   设置定时任务运行 report.py , 方式较多，这里不做赘述
