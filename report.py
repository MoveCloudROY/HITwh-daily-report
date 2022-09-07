#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  thanks for the authors of these repositories
#  1. some urls and login steps
#  https://github.com/Cyberenchanter/HITWH-jktb
#  2. framework
#  https://github.com/JalinWang/HITsz-daily-report
#
import time
from typing import List

import requests
import json
import base64
import ddddocr
import http.cookiejar as cookielib
from urllib.parse import urlparse, parse_qs


# ========================================= #
# 报错
class ReportException(Exception):
    """上报异常错误信息"""

    class LoginError(Exception):
        """登录失败"""

    class GetVerifyCodeError(Exception):
        """获取验证码失败"""

    class VerifyCodeWrongError(Exception):
        """验证码错误过多"""

    class GetWeChatCodeError(Exception):
        """获取微信Code失败"""

    class OAuth2Error(Exception):
        """微信鉴权失败"""

    class GetFormsError(Exception):
        """获取今日表单失败"""

    class TableError(Exception):
        """上报表格变动"""

    class SubmitError(Exception):
        """上报失败"""

    class ReportExistError(Exception):
        """已经上报"""


# ========================================= #
# 预处理配置信息

# 用户信息
with open('./user.json', 'r') as f:
    user_info = json.load(f)

# request url & headers
with open('requests_path.json', 'r') as f:
    requests_path: dict = json.load(f)

    requests_path["headers"].update({"User-Agent": user_info['userAgent'],
                                    "Referer": f"http://xy.4009955.com/sfrzwx/auth/login?openid={user_info['wechatOpenID']}&dlfs=zhmm"})  # type: dict


# ========================================= #
class Report:
    def __init__(self):
        self.today_form_id = None
        self.wechat_code = None
        self.name = None
        self.college = None
        self.mysession = requests.session()

    # 获取并解析验证码
    def get_verify_code(self):
        url = requests_path["url"]["verify_code"]
        headers: dict = requests_path["headers"]
        headers.update({"X-Requested-With": "XMLHttpRequest"})

        response = self.mysession.post(url, headers=headers, verify=False, timeout=5)

        if response.status_code != 200:
            raise ReportException.GetVerifyCodeError("获取验证码失败")

        body = response.json()
        verify_code: str = body["data"]["content"]
        verify_code_bytes = base64.standard_b64decode(verify_code.split(',')[1])
        return ddddocr.DdddOcr(show_ad=False).classification(verify_code_bytes)

    # 登录校园云应用平台
    def login(self):
        url = requests_path["url"]["login"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})

        for cnt in range(5):
            verify_code_ans = self.get_verify_code()
            params = {
                "dlfs": "zhmm",
                "openid": user_info['wechatOpenID'],
                "sjschool": "",
                "sjh": "",
                "yzm": "",
                "zhschool": user_info['schoolName'],
                "username": user_info['username'],
                "password": user_info['password'],
                "code": verify_code_ans
            }

            # 禁用跳转，用于处理登录失败的问题
            response = self.mysession.post(url, data=params, headers=headers, verify=False, timeout=5,
                                           allow_redirects=False)

            if response.status_code != 302:
                raise ReportException.LoginError("登录错误")

            next_url = response.next.url
            next_url_parse = urlparse(next_url)

            if next_url_parse.path != "/sfrzwx/auth/login":
                break

            print("验证码错误， 3s后再尝试")
            time.sleep(3)
        else:
            raise ReportException.VerifyCodeWrongError("验证码错误过多")
        # 登录成功， 跳转并更新 cookie
        headers: dict = requests_path["headers"]
        headers.update({"X-Requested-With": "XMLHttpRequest"})
        response = self.mysession.get(next_url, headers=headers)
        # print(f"GET {next_url} {response.status_code}")
        print("登录成功")
        return

    # 获取微信登录Code
    def get_wechat_code(self):
        url = requests_path["url"]["wechat_code"]
        headers: dict = requests_path["headers"]
        headers.update({"X-Requested-With": "XMLHttpRequest"})

        response = self.mysession.get(url, headers=headers, verify=False, allow_redirects=False)

        if response.status_code != 302:
            raise ReportException.GetWeChatCodeError("获取WeChat Code错误")

        # print(f'GET {url} {response.status_code}')
        next_url = response.next.url
        next_url_parse = urlparse(next_url)
        self.wechat_code = parse_qs(next_url_parse.query).get('code')[0]  # "code=balabala...&state=..."
        print("WeChat Code获取成功")

    def check_wechat_oauth(self):
        url = requests_path["url"]["OAuth2"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})

        data = {
            "code": self.wechat_code
        }
        response = self.mysession.post(url, json=data, headers=headers, verify=False, timeout=5, allow_redirects=False)

        if response.status_code != 200:
            raise ReportException.OAuth2Error("微信鉴权错误")
        print("WeChat OAuth2 通过")

    def check_report(self):
        # 获取今日表单id及填写状态
        url = requests_path["url"]["todayForms"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})

        response = self.mysession.post(url, headers=headers, verify=False, timeout=5, allow_redirects=False)

        if response.status_code != 200:
            raise ReportException.GetFormsError("获取今日表单id及状态错误")

        today_form = response.json()

        is_reported = today_form["data"]["content"][0]["tbzt"]
        self.today_form_id = today_form["data"]["content"][0]["bdtbslid"]

        # 判断是否填写过
        if is_reported == 1:
            raise ReportException.ReportExistError("已填报，无需再次填写")

        # 获取历史表单id和日期
        url = requests_path["url"]["historyForms"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})

        page_data = {
            "page": 1,  # 获取一页
            "pageSize": 50  # 一页50个items
        }

        response = self.mysession.post(url, json=page_data, headers=headers, verify=False, allow_redirects=False)
        if response.status_code != 200:
            raise ReportException.GetFormsError("获取昨日表单id错误")

        history_form = response.json()
        yesterday_form_id = history_form["data"]["content"][0]["bdtbslid"]
        yesterday_form_date = history_form["data"]["content"][0]["tbrq"].split(' ')[0]

        # 获取今日表单内容
        url = requests_path["url"]["todayFormDetail"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})

        today_data = {
            "bdtbslid": self.today_form_id
        }
        response = self.mysession.post(url, json=today_data, headers=headers, verify=False, allow_redirects=False)

        if response.status_code != 200:
            raise ReportException.GetFormsError("获取今日表单内容错误")

        today_form_content = response.json()["data"]["content"]
        today_form_list: List[dict] = today_form_content["list"]
        self.name = today_form_content["xm"]
        self.college = today_form_content["zzjgmc"]

        # 获取昨日表单内容
        url = requests_path["url"]["historyFormDetail"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})
        yesterday_data = {
            "bdtbslid": yesterday_form_id,
            "tbrq": yesterday_form_date
        }
        response = self.mysession.post(url, json=yesterday_data, headers=headers, verify=False, allow_redirects=False)

        if response.status_code != 200:
            raise ReportException.GetFormsError("获取昨日表单内容错误")

        yesterday_form_list: List[dict] = response.json()["data"]["content"]["list"]

        # 比对今日昨日表单是否一致
        # 比对表单中的 bt (标题) 和 nr 项（我读不懂学校古怪的拼音缩写:(
        is_same = 1
        if len(today_form_list) != len(yesterday_form_list):
            is_same = 0
        else:
            for i, j in zip(today_form_list, yesterday_form_list):
                if (i.get('bt') != j.get('bt')) or (i.get('nr') != j.get('nr')):
                    is_same = 0
                    break
        if is_same == 0:
            raise ReportException.TableError("表单出现更改，请手动填写，并更改设置内容")

        print("表单校验无误")

    def submit_report(self):
        url = requests_path["url"]["submit"]
        headers: dict = requests_path["headers"]
        headers.update({"Content-Type": "application/json; charset=UTF-8"})

        with open("./daily_info_template.json", "r") as _f:
            submit_form = json.load(_f)["list"]

        submit_data = {
            "list": submit_form,
            "isEdit": 1,
            "tbzt": 0,
            "syxgcs": 3,
            "tbrq": time.strftime('%Y-%m-%d', time.localtime(time.time())),
            "mrtbjzsj": "22:10",
            "xm": self.name,
            "zzjgmc": self.college,
            "bdtbslid": self.today_form_id,
            "bdmc": "学生每日健康填报"
        }

        response = self.mysession.post(url, json=submit_data, headers=headers, verify=False, allow_redirects=False)

        if response.status_code != 200:
            raise ReportException.SubmitError("提交失败")
        print("填报完成")


def main():
    print("")
    print("==========================")
    print("#   HITwh 每日健康填报     #")
    print("==========================")

    a = Report()

    try:
        a.login()
    except ReportException.GetVerifyCodeError as e:
        print(e)
        return
    except ReportException.LoginError as e:
        print(e)
        return

    try:
        a.get_wechat_code()
    except ReportException.GetWeChatCodeError as e:
        print(e)
        return

    try:
        a.check_wechat_oauth()
    except ReportException.OAuth2Error as e:
        print(e)
        return

    try:
        a.check_report()
    except ReportException.GetFormsError as e:
        print(e)
        return
    except ReportException.ReportExistError as e:
        print(e)
        return
    except ReportException.TableError as e:
        print(e)
        return

    try:
        a.submit_report()
    except ReportException.SubmitError as e:
        print(e)


if __name__ == '__main__':
    try:
        main()
    except ReportException.GetVerifyCodeError as e:
        print(e)
    except ReportException.LoginError as e:
        print(e)
    except ReportException.GetWeChatCodeError as e:
        print(e)
    except ReportException.OAuth2Error as e:
        print(e)
    except ReportException.GetFormsError as e:
        print(e)
    except ReportException.ReportExistError as e:
        print(e)
    except ReportException.TableError as e:
        print(e)
    except ReportException.SubmitError as e:
        print(e)
