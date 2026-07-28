import csv
import streamlit as st
from openai import OpenAI


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="不動産エージェントAI",
    page_icon="🏠",
    layout="centered"
)

client = OpenAI()

st.title("不動産エージェントAI")
st.write(
    "ご希望条件だけでなく、現在の暮らし方も踏まえて、"
    "あなたに合った物件をご提案します。"
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
        "マンション・戸建て・土地など、希望する物件種別はありますか？"
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
        "自己居住用ですか？ それとも投資用ですか？"
    ),
    (
        "希望時期",
        "いつ頃までに入居・購入したいですか？"
    ),

    # ---- ここから現在の生活背景 ----

    (
        "現在の駅徒歩",
        "ちなみに、現在のお住まいは最寄り駅から徒歩何分くらいですか？"
    ),
    (
        "移動手段",
        "普段の移動は、電車・車・自転車など、どれが多いですか？"
    ),
    (
        "通勤通学",
        "ご家族も含めて、通勤や通学でよく使う駅や方面はありますか？"
    ),
    (
        "家族構成",
        "今回のお住まいには何名で住まれる予定ですか？ "
        "お子様がいらっしゃれば、それも教えてください。"
    ),
    (
        "現在の住環境",
        "今のお住まいは、静かな住宅街・駅前・幹線道路沿いなど、"
        "どのような環境ですか？"
    ),
    (
        "現在の満足点",
        "今のお住まいで、気に入っているところはありますか？"
    ),
    (
        "現在の不満点",
        "逆に、今のお住まいで変えたいところや不満なところはありますか？"
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
# CSVから物件データを読む
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
            "app.py と properties.csv が同じフォルダにあるか確認してください。"
        )

    if not properties:
        return "properties.csv に物件が登録されていません。"


    # -------------------------
    # 顧客ヒアリング内容
    # -------------------------

    customer_text = "\n".join(
        f"{key}: {value}"
        for key, value in st.session_state.answers.items()
    )


    # -------------------------
    # 登録物件を文字列化
    # -------------------------

    property_blocks = []

    for number, prop in enumerate(properties, start=1):

        details = "\n".join(
            f"{key}: {value}"
            for key, value in prop.items()
            if value
        )

        property_blocks.append(
            f"【登録物件 {number}】\n{details}"
        )

    property_text = "\n\n".join(property_blocks)


    # -------------------------
    # AIへの指示
    # -------------------------

    prompt = f"""
あなたはトップクラスの不動産エージェントです。

単なる物件検索サイトのように、
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
【重要な考え方】
========================

1.
顧客の表面的な希望条件だけではなく、
現在の生活背景を重視してください。

2.
現在の住まいより生活が不便になる可能性がある場合は、
必ずその点を説明してください。

例：
現在駅徒歩5分で暮らしている人が
「徒歩10分以内」と答えたからといって、
徒歩10分まで問題なく妥協できるとは限りません。


3.
現在の住まいで気に入っている点は、
新居でもできるだけ維持できるかを考えてください。

例：
現在静かな環境を気に入っている場合、
線路沿いや幹線道路沿いは慎重に評価してください。


4.
現在の住まいの不満を改善できる物件は高く評価してください。

例：
「狭いことが不満」であれば、
単に駅徒歩が近いだけの狭い物件を最上位にしないでください。


5.
家族構成を考えてください。

子供がいる場合は、
部屋数、通勤通学、駅距離などの重要性が変わる可能性があります。


6.
普段の移動手段を考えてください。

車中心の生活なら駅徒歩だけを過度に重視せず、
駐車場なども確認してください。


7.
予算は必ずしも絶対上限とは限りません。

ただし、
予算を超える物件を安易に勧めてはいけません。

予算超過物件を提案する場合は、

・いくら超えるのか
・それでも提案する価値がある理由

を明確にしてください。


8.
顧客が希望した条件の中には、

・絶対に譲れない条件
・できれば満たしたい条件
・多少伸縮できそうな条件

が混在しています。

ヒアリング内容から、その違いを推測してください。


9.
登録物件に存在しない物件を絶対に作らないでください。


10.
価格・住所・間取り・駅徒歩など、
登録されている物件情報を勝手に変更しないでください。


11.
登録されていない情報は推測せず、
「未確認」としてください。


12.
無理に3件提案する必要はありません。

本当に提案価値がある物件が1件しかなければ、
1件だけでも構いません。


========================
【まず顧客を分析】
========================

最初に以下を整理してください。

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
【その後、物件を提案】
========================

最大3件まで提案してください。

以下の形式で回答してください。


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


    try:
        response = client.responses.create(
            model="gpt-5.5",
            input=prompt
        )

        return response.output_text

    except Exception as error:

        return (
            "AIへの接続中にエラーが発生しました。\n\n"
            f"エラー内容：{error}"
        )


# =========================================================
# 会話履歴表示
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])


# =========================================================
# ヒアリング処理
# =========================================================

if (
    not st.session_state.proposal_done
    and st.session_state.step < len(questions)
):

    user_input = st.chat_input(
        "メッセージを入力してください"
    )

    if user_input:

        # ユーザー回答を表示履歴へ保存
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )


        # 今回答した質問の項目名
        current_key = questions[
            st.session_state.step
        ][0]

        st.session_state.answers[
            current_key
        ] = user_input


        # 次の質問へ
        st.session_state.step += 1


        # まだ質問が残っている場合
        if st.session_state.step < len(questions):

            next_question = questions[
                st.session_state.step
            ][1]

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": next_question
                }
            )


        # 全質問終了
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
                        "ご希望条件と現在の生活状況を整理しました。\n\n"
                        + summary
                }
            )


            # AIによる物件提案
            proposal = create_proposal()

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content":
                        "登録物件と現在の生活状況を比較しました。\n\n"
                        + proposal
                }
            )

            st.session_state.proposal_done = True


        st.rerun()


# =========================================================
# 完了後
# =========================================================

if st.session_state.proposal_done:

    st.divider()

    if st.button(
        "🔄 最初からやり直す",
        use_container_width=True
    ):

        st.session_state.clear()
        st.rerun()