import csv
import json
import os
import urllib.error
import urllib.request

import streamlit as st


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="不動産エージェントAI",
    page_icon="🏠",
    layout="centered"
)

st.title("不動産エージェントAI")
st.write(
    "ご希望条件だけでなく、現在の暮らし方も踏まえて、"
    "あなたに合った物件をご提案します。"
)


# =========================================================
# OpenAI APIキー取得
# PCでは環境変数、Streamlit CloudではSecretsを使用
# =========================================================

def get_api_key():

    # Streamlit Cloud の Secrets を最優先
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    # ローカルPCではWindowsの環境変数を使用
    return os.getenv("OPENAI_API_KEY")


# =========================================================
# OpenAI APIへ直接接続
# openaiライブラリは使用しない
# =========================================================

def call_openai(prompt):

    api_key = get_api_key()

    if not api_key:
        return (
            "OpenAI APIキーが設定されていません。\n\n"
            "Streamlit CloudのSecretsに "
            "OPENAI_API_KEY を登録してください。"
        )

    url = "https://api.openai.com/v1/responses"

    data = {
        "model": "gpt-5.5",
        "input": prompt
    }

    body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        # Responses APIの回答本文を取得
        texts = []

        for output_item in result.get("output", []):

            if output_item.get("type") != "message":
                continue

            for content_item in output_item.get("content", []):

                if content_item.get("type") == "output_text":

                    text = content_item.get("text", "")

                    if text:
                        texts.append(text)

        if texts:
            return "\n".join(texts)

        return (
            "AIから回答は返ってきましたが、"
            "本文を取得できませんでした。"
        )

    except urllib.error.HTTPError as error:

        try:
            error_body = error.read().decode("utf-8")
        except Exception:
            error_body = str(error)

        return (
            "OpenAI APIへの接続でエラーが発生しました。\n\n"
            f"HTTPステータス：{error.code}\n\n"
            f"{error_body}"
        )

    except urllib.error.URLError as error:

        return (
            "OpenAI APIへ接続できませんでした。\n\n"
            f"エラー：{error.reason}"
        )

    except Exception as error:

        return (
            "AI処理中にエラーが発生しました。\n\n"
            f"エラー：{error}"
        )


# =========================================================
# 質問
# =========================================================

questions = [

    (
        "取引種別",
        "まず、購入と賃貸のどちらをご希望でしょうか？"
    ),

    (
        "希望エリア",
        "希望するエリアを教えてください。"
    ),

    (
        "予算",
        "ご予算はどれくらいでお考えですか？"
    ),

    (
        "物件種別",
        "マンション・戸建て・土地など、"
        "希望する物件種別はありますか？"
    ),

    (
        "間取り",
        "希望する間取りを教えてください。"
    ),

    (
        "駅徒歩",
        "駅からの距離について希望はありますか？"
    ),

    (
        "利用目的",
        "自己居住用ですか？それとも投資用ですか？"
    ),

    (
        "希望時期",
        "いつ頃までに入居・購入したいですか？"
    ),

    # -------------------------
    # 現在の生活背景
    # -------------------------

    (
        "現在の駅徒歩",
        "ちなみに、現在のお住まいは"
        "最寄り駅から徒歩何分くらいですか？"
    ),

    (
        "移動手段",
        "普段の移動は、電車・車・自転車など、"
        "どれが多いですか？"
    ),

    (
        "通勤通学",
        "ご家族も含めて、通勤や通学で"
        "よく使う駅や方面はありますか？"
    ),

    (
        "家族構成",
        "今回のお住まいには何名で住まれる予定ですか？"
        "お子様がいらっしゃれば、それも教えてください。"
    ),

    (
        "現在の住環境",
        "今のお住まいは、静かな住宅街・駅前・"
        "幹線道路沿いなど、どのような環境ですか？"
    ),

    (
        "現在の満足点",
        "今のお住まいで、気に入っているところはありますか？"
    ),

    (
        "現在の不満点",
        "逆に、今のお住まいで変えたいところや"
        "不満なところはありますか？"
    )
]


# =========================================================
# セッション初期化
# =========================================================

if "step" not in st.session_state:
    st.session_state.step = 0

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": questions[0][1]
        }
    ]

if "proposal_done" not in st.session_state:
    st.session_state.proposal_done = False


# =========================================================
# CSV読み込み
# =========================================================

def load_properties():

    properties = []

    try:

        with open(
            "properties.csv",
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                properties.append(row)

    except FileNotFoundError:
        return None

    return properties


# =========================================================
# AIによる顧客分析＋物件提案
# =========================================================

def create_proposal():

    properties = load_properties()

    if properties is None:

        return (
            "properties.csv が見つかりません。\n\n"
            "app.py と properties.csv が"
            "同じ場所にあるか確認してください。"
        )

    if not properties:

        return (
            "properties.csv に物件が登録されていません。"
        )


    # -------------------------
    # 顧客条件
    # -------------------------

    customer_text = "\n".join(
        f"{key}: {value}"
        for key, value
        in st.session_state.answers.items()
    )


    # -------------------------
    # 物件データ
    # -------------------------

    property_blocks = []

    for number, prop in enumerate(
        properties,
        start=1
    ):

        details = "\n".join(
            f"{key}: {value}"
            for key, value in prop.items()
            if value
        )

        property_blocks.append(
            f"【登録物件 {number}】\n{details}"
        )

    property_text = "\n\n".join(
        property_blocks
    )


    # -------------------------
    # AIへの指示
    # -------------------------

    prompt = f"""
あなたはトップクラスの不動産エージェントです。

単なる検索サイトのように、
条件一致率だけで物件を順位付けしてはいけません。

顧客が現在どのような生活をしているのか、
何を維持したいのか、
何を改善したいのかまで考えてください。


========================
【顧客ヒアリング結果】
========================

{customer_text}


========================
【登録物件】
========================

{property_text}


========================
【重要ルール】
========================

1.
表面的な希望条件だけでなく、
現在の生活背景を重視してください。

2.
現在の住まいより生活が不便になる場合は、
必ず説明してください。

3.
現在の住まいで気に入っている点は、
新居でも可能な限り維持できるか考えてください。

4.
現在の住まいの不満を改善できる物件は
高く評価してください。

5.
家族構成を考慮してください。

6.
通勤・通学・移動手段を考慮してください。

7.
現在駅徒歩5分で生活している人が
「徒歩10分以内」と回答しても、
単純に徒歩10分まで妥協可能とは判断しないでください。

8.
予算は必ずしも絶対上限とは限りません。

ただし予算超過物件を提案する場合は、

・いくら超えるか
・それでも提案する価値がある理由

を明示してください。

9.
顧客の条件を、

・絶対に譲れない可能性が高い条件
・重要な条件
・伸縮できる可能性がある条件

に分けて考えてください。

10.
登録物件に存在しない物件を
絶対に作らないでください。

11.
価格・住所・間取り・駅徒歩などを
勝手に変更しないでください。

12.
登録されていない情報は
推測せず「未確認」としてください。

13.
無理に3件提案する必要はありません。

本当に提案価値がある物件が1件なら、
1件だけでも構いません。


========================
【最初に顧客分析】
========================

【この顧客の生活背景】

【現在維持したいと思われること】

【現在改善したいと思われること】

【推定される優先順位】
1.
2.
3.
4.

【妥協しにくいと思われる条件】

【ある程度伸縮できる可能性がある条件】


========================
【物件提案】
========================

最大3件まで提案してください。


【第一候補】

物件名：
価格：
所在地：
最寄駅：
駅徒歩：
間取り：

おすすめ理由：

現在の生活から改善する点：

現在の生活より悪くなる可能性：

希望条件との相違点：

この物件を内見する価値：


【第二候補】

物件名：
価格：
所在地：
最寄駅：
駅徒歩：
間取り：

おすすめ理由：

現在の生活から改善する点：

現在の生活より悪くなる可能性：

希望条件との相違点：

この物件を内見する価値：


【第三候補】

物件名：
価格：
所在地：
最寄駅：
駅徒歩：
間取り：

おすすめ理由：

現在の生活から改善する点：

現在の生活より悪くなる可能性：

希望条件との相違点：

この物件を内見する価値：


========================
【最後に】
========================

・どの順番で内見するべきか

・今回の登録物件では不足している条件

・この顧客に次に確認すべき質問を1つ

を説明してください。
"""

    return call_openai(prompt)


# =========================================================
# 会話履歴表示
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["content"]
        )


# =========================================================
# ヒアリング
# =========================================================

if (
    not st.session_state.proposal_done
    and st.session_state.step < len(questions)
):

    user_input = st.chat_input(
        "メッセージを入力してください"
    )

    if user_input:

        # ユーザー回答を履歴へ保存
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )


        # 現在の質問項目
        current_key = questions[
            st.session_state.step
        ][0]


        # 回答保存
        st.session_state.answers[
            current_key
        ] = user_input


        # 次の質問
        st.session_state.step += 1


        if (
            st.session_state.step
            < len(questions)
        ):

            next_question = questions[
                st.session_state.step
            ][1]

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": next_question
                }
            )


        else:

            summary = "\n".join(
                f"{key}: {value}"
                for key, value
                in st.session_state.answers.items()
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content":
                        "ありがとうございます。"
     
