from gevent import monkey

monkey.patch_all()
import urllib.parse
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import time
import requests
import xlwt
import gevent
from gevent.queue import Queue

url1 = 'https://www.toutiao.com/api/pc/list/feed?client_extra_params=%7B%22short_video_item%22:%22filter%22%7D&'

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
    'referer': 'https://www.toutiao.com/',
}

# 统计爬取条目
x = 1

# 表头数据预处理
workbook = xlwt.Workbook(encoding='ascii')
worksheet = workbook.add_sheet("data1")
worksheet.write(0, 0, "标题")
worksheet.write(0, 1, "出处")
worksheet.write(0, 2, "评论数")
workbook.save("今日头条.xls")


# 大部分时间消耗在这个函数中
def get_signature(url2):
    """
    通过url加密计算_signature参数
    :param url2: 待加密的url
    :return: _signature参数
    """
    options = Options()

    options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument('--disable-blink-features=AutomationControlled')

    browser = webdriver.Chrome(options=options)
    browser.set_page_load_timeout(10)

    try:
        browser.get('https://www.toutiao.com/')
    except TimeoutException as e:
        browser.execute_script('window.stop()')
        browser.close()
        browser.quit()
        print("页面加载超时")

    time.sleep(5)  # 等待页面元素充分加载

    cookies = browser.execute_script(f"return window.byted_acrawler.sign({{'url':'{url2}'}});")
    browser.close()
    browser.quit()
    return cookies


def re_reponse(s, url):
    """
    根据请求参数返回响应
    :param s: 构建的session对象
    :param url: 完整url链接
    :return: 响应数据
    """
    response = s.get(url=url, headers=header)
    datas = response.json()
    response.close()
    return datas


def data_analysis(datas):
    """
    数据处理
    :param datas: 要处理的json格式数据
    :return:
    """
    global x
    for i in datas['data']:
        title = i.get('title', '').replace('\n', '')[:20]
        # print(title)
        media_name = i.get('media_name', '')
        # print(media_name)
        comment_count = i.get('comment_count', '')
        # print(comment_count)

        # 写入execl文件
        worksheet.write(x, 0, title)
        worksheet.write(x, 1, media_name)
        worksheet.write(x, 2, comment_count)
        workbook.save("今日头条.xls")
        print(f'-------第{x}条写入------')

        x += 1


def first_request():
    """
    因为第一条请求与其它请求,参数不同,所以单独处理
    :return: 第二个请求的min_behot_time参数, session会话
    """
    # 第一个请求的参数
    param1 = {
        'channel_id': '3189398999',
        'min_behot_time': 0,
        'refresh_count': '1',
        'category': 'pc_profile_channel',
        'aid': '24',
        'app_name': 'toutiao_web',
    }

    # 拼接待加密的url
    url2 = url1 + urllib.parse.urlencode(param1)

    # 通过url加密计算_signature参数
    signature = get_signature(url2)

    # 拼接完整url路径
    url = url2 + '&_signature=' + signature
    # print(url)

    s = requests.session()  # 包含cookie

    # 第一个请求(15条数据)
    datas = re_reponse(s, url)

    # 第一条请求的数据处理(因为与其它请求参数不同所以单独处理)
    data_analysis(datas)

    # 拿到第二个请求的min_behot_time参数(这里的14是因为每个请求有15条数据，14代表最后一条数据)
    min_behot_time = datas['data'][14]['behot_time']

    return min_behot_time, s


def other_request():
    """
    其余请求处理
    :return:
    """
    while not work.empty():
        url = work.get_nowait()
        datas = re_reponse(s, url)
        data_analysis(datas)


def other_request_link(page, min_behot_time):
    """
    提取其余请求的链接到队列
    :param page: 请求个数
    :param min_behot_time: 第二个请求的min_behot_time参数
    :return: 装载请求链接的队列
    """
    # 创建queue队列
    work = Queue(page)

    for i in range(page):
        param2 = {
            'channel_id': '3189398999',
            'max_behot_time': min_behot_time,  # 这是第二个请求，从现在开始往后依次减去15
            'category': 'pc_profile_channel',
            'aid': ' 24',
            'app_name': ' toutiao_web',
        }

        # 拼接待加密的url
        url2 = url1 + urllib.parse.urlencode(param2)

        # 通过url加密计算_signature参数
        signature = get_signature(url2)

        # 拼接完整url路径
        url = url2 + '&_signature=' + signature
        # print(url)

        # 将请求链接放进队列里面
        work.put_nowait(url)

        # 其余请求的min_behot_time规律为依次递减15
        min_behot_time = min_behot_time - 15
    return work


if __name__ == '__main__':
    # 第二个请求的min_behot_time参数
    min_behot_time, s = first_request()
    # print(min_behot_time)

    page = 10  # 表示再获取两条请求，即2*15=30条数据，加上之前的15条一共45条数据(可以更改)

    # # 创建queue队列
    # work = Queue(page)

    # 提取其余请求的链接到队列
    work = other_request_link(page, min_behot_time)

    # 空任务列表
    tasks_list = []
    for i in range(5):  # 创建5个任务(可以更改)
        task = gevent.spawn(other_request)
        tasks_list.append(task)  # 将任务加入列表

    gevent.joinall(tasks_list)  # 启动执行所有的任务