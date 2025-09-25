from __future__ import annotations
import os
from openai import OpenAI

# 環境変数からAPIキーを取得
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# プレイヤーの初期ステータス
player = {
    "hp": 20,
    "items": [],
}


def adventure_step(story_so_far: str, user_choice: str, hp: int, items: list[str]) -> str:
    prompt = f"""
    あなたは壮大なファンタジー小説の語り部です。
    現在の物語は以下です:
    {story_so_far}

    プレイヤーは「{user_choice}」を選びました。
    プレイヤーの現在のHPは {hp} で、持ち物は {items} です。

    この続きの物語を150〜200文字で語ってください。
    さらに必ず「選択肢を2つ」と「イベント効果」を提示してください。
    イベント効果は HP増減 または アイテム獲得/喪失 の形にしてください。

    形式は:
    ---物語---
    （ストーリー本文）
    ---効果---
    HP: +x / -x または Item: 〇〇
    ---選択肢---
    1. ○○
    2. ○○
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],  # ← 修正
            }
        ],
        max_output_tokens=400,
    )
    return response.output_text  # まとめてテキスト取得OK


def apply_event_effects(story: str) -> None:
    if "---効果---" not in story:
        return

    loss_keywords = ["喪失", "失う", "失った", "lost", "失いました"]

    for raw_line in story.splitlines():
        line = raw_line.strip()
        if line.startswith("HP:"):
            effect_text = line.split("HP:", 1)[1].strip()
            if not effect_text:
                continue
            sign = 1
            if effect_text[0] in "+-":
                if effect_text[0] == "-":
                    sign = -1
                effect_text = effect_text[1:]
            try:
                value = int(effect_text.strip())
            except ValueError:
                continue
            player["hp"] += sign * value
        elif line.startswith("Item:"):
            item_text = line.split("Item:", 1)[1].strip()
            if not item_text:
                continue
            is_loss = False
            for keyword in loss_keywords:
                if keyword in item_text:
                    item_text = item_text.replace(keyword, "")
                    is_loss = True
            if item_text.startswith("-"):
                is_loss = True
                item_text = item_text[1:]
            if item_text.startswith("+"):
                item_text = item_text[1:]
            cleaned_item = item_text.strip(" ()")
            if not cleaned_item:
                continue
            if is_loss:
                if cleaned_item in player["items"]:
                    player["items"].remove(cleaned_item)
            elif cleaned_item not in player["items"]:
                player["items"].append(cleaned_item)


def main() -> None:
    story = "あなたは霧深い森の入口に立っている。旅は今始まったばかりだ。"
    print(story)
    print(f"HP: {player['hp']}, Items: {player['items']}")

    while True:
        choice = input("どうする？ > ")
        story = adventure_step(story, choice, player["hp"], player["items"])
        print(story)

        apply_event_effects(story)

        print(f"📊 ステータス → HP: {player['hp']}, Items: {player['items']}")
        if player["hp"] <= 0:
            print("💀 あなたは力尽きてしまった… ゲームオーバー！")
            break


if __name__ == "__main__":
    main()
