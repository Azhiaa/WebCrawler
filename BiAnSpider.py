"""
彼岸4K图片爬虫
https://pic.netbian.com
"""

import os
from urllib.parse import urljoin
from multiprocessing import Pool, cpu_count

import requests
from lxml import etree
from fake_useragent import UserAgent


BASE_URL = "https://pic.netbian.com"
SAVE_PATH = "./BiAn4K"
UA = UserAgent()


def connect(url: str) -> bytes or None:
    """
    连接、获取网页二进制数据
    """
    headers = {
    "user-agent": UA.random,
    "referer": "https://pic.netbian.com",
    }
    result: bytes or None = None

    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            result = response.content
        else:
            print("网页状态码不对,详情:", response.status_code)
    except Exception as err:
        print("发生错误,详情:", err)
    
    return result


def parse(content: bytes, code: str = "gbk", is_out: bool = True, is_home: bool = False) -> dict:
    """
    HTML网页解析
    """
    if not content:
        return
    
    try:
        content = content.decode(code)
    except Exception:
        content = content.decode("utf-8")

    html = etree.HTML(content)

    # 处理网站首页相关内容
    if is_home:
        home_title_info: dict = parser_home(html)
        return home_title_info

    # 解析外层页面
    if is_out:
        # 获取网页总页数和当前所在页数
        page_data: dict = parser_page(html)
        # 获取网页外层URL
        out_urls: list = parser_out_url(html)
        return {"page_dict": page_data, "out_urls_list": out_urls}
    # 解析内层页面
    else:
        pic_info: dict = parser_in_url(html)
        return pic_info


def parser_home(html: etree.HTML) -> dict:
    """
    HTML首页选择栏解析
    """
    title_names: list = html.xpath("//div[@class='classify clearfix']/a/text()")
    title_urls: list = html.xpath("//div[@class='classify clearfix']/a/@href")
    return {"title_names": title_names, "title_urls": title_urls}


def parser_page(html: etree.HTML) -> dict:
    """
    HTML网页页码解析
    """
    all_page_xpath: list = html.xpath("//div[@class='page']/a")
    current_page_xpath: list = html.xpath("//div[@class='page']/b")

    all_page: int = int(all_page_xpath[-2].text) if len(all_page_xpath) > 1 else 0
    current_page: int = int(current_page_xpath[0].text) if len(current_page_xpath) > 0 else 0

    return {"all_page": all_page, "current_page": current_page}


def parser_out_url(html: etree.HTML) -> list:
    """
    HTML网页外层URL解析
    """
    return [urljoin(BASE_URL, url) for url in html.xpath("//ul[@class='clearfix']/li/a/@href")]


def parser_in_url(html: etree.HTML) -> dict:
    """
    HTML网页内层URL解析
    """
    pic_url_list: list = html.xpath("//div[@class='photo-pic']/a[@id='img']/img/@src")
    pic_url: str or None = urljoin(BASE_URL, pic_url_list[0]) if len(pic_url_list) > 0 else None

    pic_name_list: list = html.xpath("//div[@class='photo-pic']/a[@id='img']/img/@title")
    pic_name: str or None = "_".join(pic_name_list[0].split()) if len(pic_name_list) > 0 else None

    if pic_url and pic_name:
        pic_name += pic_url.split("/")[-1]
    return {"name": pic_name, "url": pic_url}


def save_pic(content: bytes, path: str) -> None:
    """
    保存图片到指定路径
    """
    with open(path, mode="wb") as stream:
        stream.write(content)
    print("已下载：", path.split("/")[-1])


def user_choose_task() -> list:
    """
    用户选择执行任务
    """
    # 获取网站首页相关信息信息
    home_content: bytes = connect(BASE_URL)
    home_title_info: dict = parse(home_content, is_home=True)

    while True:
        # 展示风格选择项
        print("该网站目前提供的风格".center(20, "="))
        for number, title_name in enumerate(home_title_info["title_names"], 1):
            print("序号:".rjust(8), f"{number}".ljust(2), f" ->  {title_name}")
        
        # 获取用户风格选择项
        print("-" * 40)
        style_url = home_title_info["title_urls"][0]
        style_name = home_title_info["title_names"][0]
        cmd = input(f"请输入序号选择图片风格[默认为{style_name}:1]>")
        if cmd.isdigit() and 0 < int(cmd) < 13:
            style_url = home_title_info["title_urls"][int(cmd) - 1]
            style_name = home_title_info["title_names"][int(cmd) - 1]
        style_home_url = urljoin(BASE_URL, style_url)
        print(style_name, style_home_url)
        
        # 获取用户风格选择项的网页页数
        style_content: bytes = connect(style_home_url)
        # 都是 int 类型
        all_page, current_page = parse(style_content, is_out=True)["page_dict"].values()

        # 展示用户风格选择项的页数信息
        print("-" * 40)
        print(f"{style_name}风格系列总共有{all_page}页,起始页数为第{current_page}页")

        # 获取用户爬取任务的起始页
        print("-" * 40)
        start_page: int = current_page
        cmd = input(f"最小不低于{start_page},最大不超过{all_page}\n请输入任务起始页[默认为该系列第{current_page}页:{start_page}]>")
        if cmd.isdigit() and current_page <= int(cmd) <= all_page:
            start_page = int(cmd)
        
        # 获取用户爬取任务的结束页
        print("-" * 40)
        end_page: int = start_page + 4
        cmd = input(f"最小不低于{end_page},最大不超过{all_page}\n请输入任务结束页[默认为任务起始页+4:{end_page}]>")
        if cmd.isdigit() and start_page <= int(cmd) <= all_page:
            end_page = int(cmd)
        
        # 确认任务信息
        print("-" * 40)
        print(f"图片风格:{style_name}\n任务起始页:{start_page}\n任务结束页:{end_page}")
        print("-" * 40)
        cmd = input("请确认任务,'y'确认,'n'否认,'q'退出[默认为:y]>")
        if cmd in ["q", "Q"]:
            exit("程序已退出!")
        elif cmd == "" or cmd in ["y", "Y"]:
            task_urls = [urljoin(style_home_url, f"index_{page}.html") if page != 1 else style_home_url for page in range(start_page, end_page + 1)]
            print("=" * 40)
            print(f"任务已确认!\n爬取'{style_name}'风格图片,从'第{start_page}页'到'第{end_page}页',总共需爬取'{len(task_urls)}页'!")
            print("程序即将开始运行，请稍后...")
            return task_urls


def mut_parser(ite):
    """
    多进程多参数解析适配函数
    """
    return parse(**ite)


def mut_download(pic_info: dict):
    """
    多进程下载适配函数
    """
    pic_content = connect(pic_info.get("url"))
    save_pic(pic_content, os.path.join(SAVE_PATH, pic_info.get("name")))
    

def main():
    if not os.path.exists(SAVE_PATH):
        os.mkdir(SAVE_PATH)
    
    user_task_info: list = user_choose_task()

    # 使用多进程提高任务速度
    pool = Pool(cpu_count())

    # 获取所有任务的外层页面链接
    out_web_content = pool.map_async(connect, user_task_info)
    out_all_info = pool.map_async(parse, out_web_content.get())

    for out_info_dict in out_all_info.get():
        page_info_dict, out_url_list = out_info_dict.values()
        print(f"该系列总共{page_info_dict.get('all_page')}页,当前正在爬取第{page_info_dict.get('current_page')}页!")
        
        # 获取网页内层数据
        in_web_content = pool.map_async(connect, out_url_list)
        pic_info_list = pool.map_async(mut_parser, [{"content": sangle_content, "is_out": False} for sangle_content in in_web_content.get()])
        
        # 下载并保存图片
        pool.map_async(mut_download, pic_info_list.get())  

    # 关闭进程池并等待任务完成
    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
