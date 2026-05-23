import requests
import json
import re
import os
from bs4 import BeautifulSoup


def load_cookies():
    """
    从 assets/cookies.json 加载 cookies

    Returns:
        cookies 字符串，如果文件不存在或为空则返回 None
    """
    cookies_file = os.path.join(os.path.dirname(__file__), '..', 'assets', 'cookies.json')
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('cookies', '').strip()
    return None


def get_journal_comments(journal_id: int, page: int = 1, sorttype: str = "undefined", cookies: str = None):
    """
    获取期刊评论

    Args:
        journal_id: 期刊 ID
        page: 页码，默认为 1
        sorttype: 排序类型，默认为 "undefined"
        cookies: cookies 字符串，如果为 None 则从 assets/cookies.txt 读取

    Returns:
        评论数据 JSON
    """
    url = "https://letpub.com.cn/journalappAjax_comments_center.php"
    params = {
        "action": "getdetailscommentslistflow",
        "journalid": journal_id,
        "sorttype": sorttype,
        "page": page
    }
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest",
        "referer": f"https://letpub.com.cn/index.php?journalid={journal_id}&page=journalapp&view=detail"
    }

    # 如果未提供 cookies，尝试从文件加载
    if cookies is None:
        cookies = load_cookies()

    # 如果有 cookies，添加到 headers
    if cookies:
        headers["cookie"] = cookies

    response = requests.post(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def parse_comment(html_content: str):
    """
    解析单条评论的 HTML 内容

    Args:
        html_content: 评论的 HTML 字符串

    Returns:
        解析后的评论字典
    """
    soup = BeautifulSoup(html_content, "html.parser")
    comment = {}

    # 楼层号
    floor_tag = soup.select_one('span.layui-breadcrumb span[style*="font-size:18px"] strong')
    if floor_tag:
        comment['floor'] = floor_tag.get_text(strip=True)

    # 作者昵称
    author_tag = soup.select_one('a[href*="/profile/"]')
    if author_tag:
        comment['author'] = author_tag.get_text(strip=True)
        comment['author_id'] = author_tag['href'].split('/')[-1]

    # 期刊评分
    score_tag = soup.select_one('div[style*="color:#FF5722"]')
    if score_tag:
        comment['score'] = score_tag.get_text(strip=True)

    # 研究方向
    research_tags = soup.select('span.layui-badge.layui-bg-gray')
    if research_tags:
        comment['research_fields'] = [tag.get_text(strip=True) for tag in research_tags]

    # 投稿结果
    result_tag = soup.find('span', string=re.compile(r'投稿结果'))
    if result_tag:
        comment['submission_result'] = result_tag.next_sibling.get_text(strip=True) if result_tag.next_sibling else ''

    # 投稿周期
    cycle_tag = soup.find('span', string=re.compile(r'投稿周期'))
    if cycle_tag:
        comment['submission_cycle'] = cycle_tag.next_sibling.get_text(strip=True) if cycle_tag.next_sibling else ''

    # 发表时间
    publish_time_tag = soup.find('span', string=re.compile(r'发表时间'))
    if publish_time_tag:
        comment['publish_time'] = publish_time_tag.next_sibling.get_text(strip=True) if publish_time_tag.next_sibling else ''

    # 最后更新
    update_time_tag = soup.find('span', string=re.compile(r'最后更新'))
    if update_time_tag:
        comment['update_time'] = update_time_tag.next_sibling.get_text(strip=True) if update_time_tag.next_sibling else ''

    # 投稿经验
    experience_tag = soup.select_one('blockquote.layui-elem-quote')
    if experience_tag:
        # 提取"投稿经验："后面的内容，但排除"其他用户回复"部分
        experience_text = experience_tag.get_text(strip=True)
        if '投稿经验：' in experience_text:
            # 只取到"其他用户回复"之前的内容
            parts = experience_text.split('其他用户回复')
            experience = parts[0].replace('投稿经验：', '').strip()
            comment['experience'] = experience

    # 其他用户回复
    replies = []
    reply_wrapper = soup.select_one('div[id^="reply_section_wrapper_"]')
    if reply_wrapper:
        reply_blocks = reply_wrapper.select('blockquote.layui-elem-quote.layui-quote-nm')
        for reply_block in reply_blocks:
            reply = {}
            # 作者
            author_link = reply_block.select_one('a[href*="/profile/"]')
            if author_link:
                reply['author'] = author_link.get_text(strip=True)
                reply['author_id'] = author_link['href'].split('/')[-1]
            # 发表时间
            time_text = reply_block.get_text(strip=True)
            time_match = re.search(r'发表时间：(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', time_text)
            if time_match:
                reply['publish_time'] = time_match.group(1)
            # 回复内容（去除作者和时间）
            reply_text = reply_block.get_text(separator='\n', strip=True)
            lines = [line for line in reply_text.split('\n') if line.strip()]
            # 过滤掉作者、时间、点赞等信息，保留纯文本内容
            content_lines = []
            for line in lines:
                # 跳过包含关键词的行
                if any(keyword in line for keyword in ['发表时间：', '人赞', '主页', '好友', '【', '】', 'cursor:pointer', 'onclick']):
                    continue
                # 跳过纯数字（可能是点赞数）
                if line.strip().isdigit():
                    continue
                # 跳过作者名（与已提取的 author 相同）
                if line.strip() == reply.get('author', ''):
                    continue
                if line.strip():
                    content_lines.append(line.strip())
            if content_lines:
                reply['content'] = ' '.join(content_lines)
            # 点赞数
            good_tag = reply_block.select_one('span[id^="commentid_"][id$="_good"]')
            if good_tag:
                reply['good_count'] = int(good_tag.get_text(strip=True))
            replies.append(reply)
    if replies:
        comment['replies'] = replies

    # 点赞数
    good_count_tag = soup.select_one('span[id^="commentid_"][id$="_good"]')
    if good_count_tag:
        comment['good_count'] = int(good_count_tag.get_text(strip=True))

    # 踩数
    bad_count_tag = soup.select_one('span[id^="commentid_"][id$="_bad"]')
    if bad_count_tag:
        comment['bad_count'] = int(bad_count_tag.get_text(strip=True))

    return comment


def parse_comments_response(response_data: dict):
    """
    解析评论 API 响应

    Args:
        response_data: API 返回的 JSON 数据

    Returns:
        解析后的评论列表
    """
    if response_data.get('code') != 0:
        return []

    comments = []
    for item in response_data.get('data', []):
        html_content = item.get('content', '')
        if html_content:
            comment = parse_comment(html_content)
            comments.append(comment)

    return comments


if __name__ == "__main__":
    # 示例：获取期刊评论
    journal_id = 1642
    response_data = get_journal_comments(journal_id, page=1)
    print(f"总记录数: {response_data.get('count', 0)}")
    print(f"总页数: {response_data.get('pages', 0)}")
    print(f"当前页数据条数: {len(response_data.get('data', []))}")
    comments = parse_comments_response(response_data)
    print(json.dumps(comments, indent=2, ensure_ascii=False))
